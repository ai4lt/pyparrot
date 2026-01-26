
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
import sys

admin_client = KafkaAdminClient(bootstrap_servers=["kafka:9092"])

existing_topics = admin_client.list_topics()

topic_partitions = [('mt',25),
                    ('tts',10),
                    ('mediator',10),
                    ('asr',25),
                    ('bot',10),
                    ('textseg',10),
                    ('kitmeetingbutler',10),
                    ('textstructurer',10),
                    ('postproduction',10),
                    ('summarizer',10),
                    ('log',10)]

for t,p in topic_partitions:
    if t in existing_topics:
        continue

    try:
        topic_list = [NewTopic(name=t, num_partitions=p, replication_factor=1)]
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
    except Exception as e:
        print(e)

