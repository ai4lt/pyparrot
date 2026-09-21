"""Supply local mediator wheels without changing standalone component installs."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import yaml
from .versions import kafka_version


BUNDLE = 'pyparrot_local_dependencies'


def _build_mediator_wheel(source: Path, workspace: Path, version='2.0.2') -> Path:
    """Build in Docker, keeping packaging tools and generated files out of the checkout."""
    context = workspace / 'mediator'
    shutil.copytree(source, context, symlinks=True,
                    ignore=shutil.ignore_patterns('.git', '__pycache__', 'build', 'dist', '*.egg-info'))
    dockerfile = workspace / 'mediator.Dockerfile'
    dockerfile.write_text(
        'FROM python:3.11-slim\n'
        'COPY . /src\n'
        'ARG KAFKA_PYTHON_VERSION=2.0.2\n'
        'RUN python -m pip wheel --no-deps --wheel-dir /wheels /src\n'
    )
    image = 'pyparrot-mediator-wheel:' + uuid.uuid4().hex
    container = None
    wheels = workspace / 'wheels'
    wheels.mkdir()
    try:
        subprocess.run(['docker', 'build', '-f', str(dockerfile), '-t', image, '--build-arg', 'KAFKA_PYTHON_VERSION=' + kafka_version(version), str(context)],
                       check=True)
        container = subprocess.check_output(['docker', 'create', image], text=True).strip()
        subprocess.run(['docker', 'cp', container + ':/wheels/.', str(wheels)], check=True)
    finally:
        if container:
            subprocess.run(['docker', 'rm', container], capture_output=True)
        subprocess.run(['docker', 'image', 'rm', image], capture_output=True)
    candidates = list(wheels.glob('qbmediator-*.whl'))
    if len(candidates) != 1:
        raise RuntimeError('Expected exactly one qbmediator wheel from the local source')
    return candidates[0]


MEDIATOR_REQUIREMENTS = {
    'git+https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/qbmediator',
    'git+https://gitlab.kit.edu/kit/isl-ai4lt/lt-middleware/qbmediator.git',
}


def _requirement_matches(lines):
    return [i for i, line in enumerate(lines) if line.strip() in MEDIATOR_REQUIREMENTS]


def _build_context(build, config_dir):
    value = build if isinstance(build, str) else (build or {}).get('context')
    if not value or '://' in value or value.startswith('git@'):
        return None
    path = Path(value)
    return (path if path.is_absolute() else Path(config_dir) / path).resolve()


def _find_mediator(context, configured_source=None):
    # The pipeline's mediator service is authoritative when present. Otherwise
    # support both components/dialog/* and backends/* repository layouts.
    candidates = [configured_source] if configured_source else [
        candidate for parent in context.parents
        for candidate in (parent / 'qbmediator', parent / 'components' / 'qbmediator')
    ]
    for candidate in candidates:
        if (candidate / 'setup.py').is_file() or (candidate / 'pyproject.toml').is_file():
            return candidate.resolve()
    raise RuntimeError(f'Local qbmediator source missing for {context}; initialize the submodule')


def _stage_component_context(context: Path, staged: Path, wheel: Path) -> Path:
    lines = (context / 'requirements.txt').read_text().splitlines()
    matches = _requirement_matches(lines)
    if len(matches) != 1:
        raise RuntimeError(f'Expected one GitLab qbmediator requirement in {context}')
    shutil.copytree(context, staged, symlinks=True,
                    ignore=shutil.ignore_patterns('.git', '__pycache__'))
    bundle = staged / BUNDLE
    bundle.mkdir()  # Refuse to overwrite an existing bundle in the source context.
    shutil.copy2(wheel, bundle / wheel.name)
    lines[matches[0]] = '/tmp/pyparrot-dependencies/' + wheel.name
    (bundle / 'requirements.txt').write_text('\n'.join(lines) + '\n')
    # Keep repository ignore rules, but ensure the injected dependency bundle is sent.
    ignore = staged / '.dockerignore'
    with ignore.open('a') as stream:
        stream.write(f'\n!{BUNDLE}/\n!{BUNDLE}/**\n')
    return staged


@contextmanager
def local_dependency_override(compose_command, config_dir, services=()):
    """Stage selected mediator consumers, building one wheel per local source."""
    result = subprocess.run(compose_command + ['config'], cwd=str(config_dir),
                            check=True, capture_output=True, text=True)
    configured = yaml.safe_load(result.stdout).get('services') or {}
    unknown = set(services) - configured.keys()
    if unknown:
        raise RuntimeError(f'Unknown build services: {", ".join(sorted(unknown))}')
    configured_source = _build_context(configured.get('qbmediator', {}).get('build'), config_dir)
    targets = {}
    for name in services or configured:
        build = configured[name].get('build')
        context = _build_context(build, config_dir)
        if context is None or not (context / 'requirements.txt').is_file():
            continue
        matches = _requirement_matches((context / 'requirements.txt').read_text().splitlines())
        if not matches:
            continue
        if len(matches) != 1:
            raise RuntimeError(f'Expected one GitLab qbmediator requirement in {context}')
        dockerfile = context / (build.get('dockerfile', 'Dockerfile') if isinstance(build, dict) else 'Dockerfile')
        if 'ARG DEPENDENCY_BUNDLE=' not in dockerfile.read_text():
            raise RuntimeError(f'{name}: Dockerfile does not support DEPENDENCY_BUNDLE; update the component checkout')
        args = build.get('args', {}) if isinstance(build, dict) else {}
        version = kafka_version(args.get('KAFKA_PYTHON_VERSION') or '2.0.2')
        targets[name] = (context, _find_mediator(context, configured_source), version)
    if not targets:
        yield None
        return
    with tempfile.TemporaryDirectory(prefix='pyparrot-local-build-') as temporary:
        workspace = Path(temporary)
        wheels = {}
        contexts = {}
        overrides = {}
        for name, (context, mediator, version) in targets.items():
            wheel_key = (mediator, version)
            if wheel_key not in wheels:
                wheel_workspace = workspace / f'wheel-{len(wheels)}'
                wheel_workspace.mkdir()
                wheels[wheel_key] = _build_mediator_wheel(mediator, wheel_workspace, version)
            key = (context, mediator, version)
            if key not in contexts:
                contexts[key] = _stage_component_context(
                    context, workspace / f'component-{len(contexts)}', wheels[wheel_key])
            overrides[name] = {'build': {
                'context': str(contexts[key]), 'args': {'DEPENDENCY_BUNDLE': BUNDLE, 'KAFKA_PYTHON_VERSION': version},
            }}
        override = workspace / 'compose.override.yaml'
        override.write_text(yaml.safe_dump({'services': overrides}))
        yield override
