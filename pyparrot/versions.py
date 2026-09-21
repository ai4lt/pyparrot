"""Deployment version defaults and isolated images for Kafka consumers."""
import hashlib
import re
from pathlib import Path
from dotenv import dotenv_values


def kafka_version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:(?:a|b|rc)[0-9]+)?", value):
        raise ValueError("KAFKA_PYTHON_VERSION must be an exact release version")
    return value


def deployment_versions(existing, pipeline_name):
    defaults = dotenv_values(Path(__file__).parent / "templates/versions.env", interpolate=False)
    values = {key: existing.get(key) or value for key, value in defaults.items()}
    kafka_version(values["KAFKA_PYTHON_VERSION"])
    name = re.sub(r"[^a-z0-9-]+", "-", pipeline_name.lower()).strip("-")[:48] or "pipeline"
    digest = hashlib.sha256(pipeline_name.encode()).hexdigest()[:10]
    values["PIPELINE_IMAGE_PREFIX"] = f"pyparrot/{name}-{digest}"
    return values


def configure_kafka_builds(composed):
    # Every locally built service gets a deployment-specific image. This also
    # covers mediator consumers supplied by backend templates and service aliases.
    for name, service in composed.get("services", {}).items():
        build = service.get("build")
        if not build:
            continue
        if isinstance(build, str):
            build = service["build"] = {"context": build}
        build.setdefault("args", {})["KAFKA_PYTHON_VERSION"] = "${KAFKA_PYTHON_VERSION:-2.0.2}"
        service["image"] = "${PIPELINE_IMAGE_PREFIX:?Run configure to set the pipeline image prefix}/" + name + ":kafka-${KAFKA_PYTHON_VERSION:-2.0.2}"
    return composed


def prepare_versions(directory):
    """Opt an existing deployment into versioned builds, preserving its settings."""
    import shutil
    import yaml
    directory = Path(directory)
    env_path = directory / '.env'
    compose_path = directory / 'docker-compose.yaml'
    existing = dotenv_values(env_path, interpolate=False)
    values = deployment_versions(existing, existing.get('PIPELINE_NAME') or directory.name)
    config = yaml.safe_load(compose_path.read_text())
    configure_kafka_builds(config)
    if 'kafka' in config.get('services', {}):
        config['services']['kafka']['image'] = '${KAFKA_IMAGE:?Set KAFKA_IMAGE in the deployment .env}'
    text = env_path.read_text().rstrip('\n') + '\n'
    for key, value in values.items():
        if re.search(r'^' + key + r'=', text, re.M):
            text = re.sub(r'^' + key + r'=.*$', key + '=' + value, text, flags=re.M)
        else:
            text += key + '=' + value + '\n'
    for path in (env_path, compose_path):
        backup = path.with_name(path.name + '.pre-versions')
        if not backup.exists():
            shutil.copy2(path, backup)
            if path == env_path:
                backup.chmod(0o600)
    env_path.write_text(text)
    compose_path.write_text(yaml.safe_dump(config, sort_keys=False))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Prepare versioned builds without restarting containers.')
    parser.add_argument('directory', type=Path)
    prepare_versions(parser.parse_args().directory)
