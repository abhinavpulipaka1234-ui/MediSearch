import json
import logging
import os
import time
import subprocess
from confluent_kafka import Consumer, KafkaError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KafkaConsumerHDFS")

KAFKA_BROKER = 'localhost:9092' # Outside docker for local test, or 'kafka:9092' inside
GROUP_ID = 'medisearch-hdfs-dumper'
TOPIC = 'symptom-intake'
BATCH_SIZE = 100
LOG_FILE = '/tmp/symptom_logs_batch.json'

def init_consumer():
    conf = {
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe([TOPIC])
    return consumer

def flush_to_hdfs(batch, timestamp_signature):
    # Dump batch to local json
    with open(LOG_FILE, 'w') as f:
        for msg in batch:
            f.write(json.dumps(msg) + '\n')
    
    # Send to HDFS via subprocess mapped to namenode
    # In a real environment we'd use pyarrow.fs.HadoopFileSystem or WebHDFS
    hdfs_dest = f"/medisearch/logs/symptom_intake_{timestamp_signature}.json"
    logger.info(f"Uploading {len(batch)} logs to HDFS at {hdfs_dest}")
    
    try:
        # Assuming run locally with docker access
        cmd = f"docker exec namenode hdfs dfs -mkdir -p /medisearch/logs/ && docker cp {LOG_FILE} namenode:/tmp/log.json && docker exec namenode hdfs dfs -put -f /tmp/log.json {hdfs_dest}"
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
        logger.info("Upload successful.")
    except Exception as e:
        logger.error(f"Failed to upload to HDFS: {e}")

if __name__ == '__main__':
    c = init_consumer()
    logger.info(f"Consumer started matching group {GROUP_ID} on {TOPIC}")
    batch = []
    
    try:
        while True:
            msg = c.poll(timeout=1.0)
            if msg is None:
                if len(batch) > 0:
                    flush_to_hdfs(batch, int(time.time()))
                    batch.clear()
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Kafka Error: {msg.error()}")
                    continue
            
            val = json.loads(msg.value().decode('utf-8'))
            batch.append(val)
            
            if len(batch) >= BATCH_SIZE:
                flush_to_hdfs(batch, int(time.time()))
                batch.clear()
    except KeyboardInterrupt:
        pass
    finally:
        c.close()
