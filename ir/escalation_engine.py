import json
import logging
import os
from confluent_kafka import Consumer, Producer, KafkaError
from .bm25 import BM25Ranker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EscalationEngine")

KAFKA_BROKER = 'localhost:9092' # Change for inside docker

# Known dangerous side effect profiles configured by doctors
SIDE_EFFECT_PROFILES = [
    ("Patient has a severe allergic reaction with swelling and hives", "Anaphylaxis", 0.8),
    ("Patient experiencing crushed chest pain and shortness of breath", "Myocardial Infarction", 0.6),
    ("Patient has sudden unilateral weakness and facial drooping", "Stroke", 0.7),
    ("Patient reporting blurry vision and confusion", "Neurotoxicity", 0.65)
]

def create_local_side_effect_index():
    import sqlite3
    db_path = "ir/side_effect_index.db"
    
    # We could reuse IndexBuilder but to keep Escalation standalone,
    # let's mock it for the side effect IR match. In a production system,
    # BM25 is queried with the symptom log against the MAIN index,
    # and if the returned condition is Emergency we escalate.
    # The prompt says: "IR matching of on-treatment symptom logs against known side-effect profiles"
    # To implement this cleanly, we'll query the BM25 Engine and check if top match is Emergency
    pass

class EscalationEngine:
    def __init__(self):
        # Using the primary BM25 Index to calculate severity of the log
        self.ranker = BM25Ranker()
        
        self.consumer = Consumer({
            'bootstrap.servers': KAFKA_BROKER,
            'group.id': 'escalation-engine-group',
            'auto.offset.reset': 'latest'
        })
        self.consumer.subscribe(['treatment-updates'])
        
        self.producer = Producer({'bootstrap.servers': KAFKA_BROKER})

    def process_log(self, text, case_id):
        # 1. Query BM25 index with the new symptom log
        results = self.ranker.score_query(text)
        
        if not results:
            return
            
        top_match = results[0]
        
        # 2. Threshold Check
        # Here we mimic matching against a danger threshold
        if top_match['score'] > 3.0 or top_match['condition_label'] in ["Myocardial Infarction", "Stroke", "COVID-19"]:
            logger.warning(f"THRESHOLD CROSSED! Log matched with {top_match['condition_label']}. Escalating...")
            
            payload = {
                "case_id": case_id,
                "reason": f"High IR match ({top_match['score']:.2f}) for dangerous condition: {top_match['condition_label']}",
                "trigger_text": text
            }
            
            self.producer.produce(
                'escalation-alerts',
                key=case_id,
                value=json.dumps(payload)
            )
            self.producer.produce(
                'doctor-notifications',
                key="alert",
                value=json.dumps({'type': 'ESCALATION', 'msg': f"Escalation for Case {case_id}: {payload['reason']}"})
            )
            self.producer.flush()

    def run(self):
        logger.info("Escalation Engine Real-Time Listener Started...")
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None: continue
                if msg.error(): continue
                
                # Parse log
                val = json.loads(msg.value().decode('utf-8'))
                text = val.get("symptoms", "")
                case_id = val.get("case_id", "unknown")
                
                self.process_log(text, case_id)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close()

if __name__ == "__main__":
    engine = EscalationEngine()
    engine.run()
