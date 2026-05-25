import json
import logging
from confluent_kafka import Producer

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KafkaProducer")

KAFKA_BROKER = 'localhost:9092' # Outside docker for local test, or 'kafka:9092' in docker

TOPICS = [
    'symptom-intake',
    'treatment-updates',
    'escalation-alerts',
    'doctor-notifications'
]

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

class MediSearchProducer:
    def __init__(self, broker=KAFKA_BROKER):
        conf = {
            'bootstrap.servers': broker,
            'client.id': 'medisearch-producer'
        }
        self.producer = Producer(conf)

    def produce(self, topic, key, value):
        if topic not in TOPICS:
            logger.warning(f"Warning: Producing to an unknown topic: {topic}")
        
        try:
            self.producer.produce(
                topic=topic,
                key=str(key),
                value=json.dumps(value),
                callback=delivery_report
            )
            self.producer.poll(0)
        except BufferError:
            logger.error(f"Local producer queue is full ({len(self.producer)} messages awaiting delivery)")
        except Exception as e:
            logger.error(f"Exception while producing: {e}")

    def flush(self):
        self.producer.flush()

if __name__ == '__main__':
    # Simple test run
    producer = MediSearchProducer()
    producer.produce('symptom-intake', 'case-123', {'symptom': 'headache', 'severity': 'Low'})
    producer.produce('doctor-notifications', 'doc-456', {'type': 'ESCALATION', 'msg': 'Patient 123 in distress'})
    producer.flush()
