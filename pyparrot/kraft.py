"""Prepare an existing deployment for a fresh KRaft cluster without starting it.

Usage: python -m pyparrot.kraft config/<deployment>
"""
import argparse
import base64
from pathlib import Path
import shutil
import uuid

from dotenv import dotenv_values
import yaml

from .template_manager import TemplateManager


def prepare_kraft(directory):
    """Back up and update Kafka settings; preserve unrelated deployment values."""
    directory = Path(directory)
    compose_path = directory / 'docker-compose.yaml'
    env_path = directory / '.env'
    config = yaml.safe_load(compose_path.read_text())
    env_text = env_path.read_text()
    env = dotenv_values(env_path, interpolate=False)
    manager = TemplateManager()
    middleware = manager.load_template('middleware')
    services = config['services']
    if 'kafka' not in services:
        raise ValueError('Deployment has no kafka service')
    services.pop('zookeeper', None)
    for name in ['kafka', 'kafka_post_task']:
        services[name] = middleware['services'][name]
    config.setdefault('volumes', {})['kafka_data'] = {}
    if not env.get('KAFKA_CLUSTER_ID'):
        cluster_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')
        env_text = env_text.rstrip('\n') + '\nKAFKA_CLUSTER_ID=' + cluster_id + '\n'
    for path in [compose_path, env_path]:
        backup = path.with_name(path.name + '.pre-kraft')
        if not backup.exists():
            shutil.copy2(path, backup)
            # Environment backups may contain credentials.
            if path == env_path:
                backup.chmod(0o600)
    compose_path.write_text(yaml.safe_dump(config, sort_keys=False))
    env_path.write_text(env_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    prepare_kraft(args.directory)
    print('Prepared KRaft configuration; originals saved as *.pre-kraft. No containers changed.')


if __name__ == '__main__':
    main()
