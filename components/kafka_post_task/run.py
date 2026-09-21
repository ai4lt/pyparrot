"""Create required pipeline topics before application services start."""

import logging
import os
import time

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError

TOPIC_PARTITIONS = {
    'mt': 25, 'tts': 10, 'mediator': 10, 'asr': 25, 'bot': 10,
    'textseg': 10, 'kitmeetingbutler': 10, 'textstructurer': 10,
    'postproduction': 10, 'summarizer': 10, 'log': 10, 'slide': 10,
}
logger = logging.getLogger(__name__)


def initialize_topics(bootstrap_servers='kafka:9092', attempts=12, retry_delay=5):
    """Retry transient broker failures; never report success with missing topics."""
    if attempts < 1:
        raise ValueError('attempts must be positive')
    for attempt in range(attempts):
        admin = None
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=10000,
                api_version_auto_timeout_ms=10000,
            )
            existing = set(admin.list_topics())
            for topic, partitions in TOPIC_PARTITIONS.items():
                if topic in existing:
                    continue
                try:
                    admin.create_topics([NewTopic(topic, partitions, 1)], timeout_ms=10000)
                except TopicAlreadyExistsError:
                    pass  # Another initializer may have won the race.
            missing = set(TOPIC_PARTITIONS) - set(admin.list_topics())
            if missing:
                raise KafkaError(f'Topics not yet visible: {sorted(missing)}')
            logger.info('All %s pipeline topics are ready', len(TOPIC_PARTITIONS))
            return
        except KafkaError:
            if attempt == attempts - 1:
                raise
            logger.warning('Kafka initialization attempt %s failed; retrying', attempt + 1,
                           exc_info=True)
        finally:
            if admin is not None:
                admin.close()
        time.sleep(retry_delay)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    initialize_topics(
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        attempts=int(os.getenv('KAFKA_INIT_ATTEMPTS', '12')),
        retry_delay=float(os.getenv('KAFKA_INIT_RETRY_DELAY', '5')),
    )
