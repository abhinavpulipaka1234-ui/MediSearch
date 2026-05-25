import asyncio
import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Doctor portal joined. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed broadcasting: {e}")

manager = ConnectionManager()

# Standalone Async Kafka Listener that pushes to websocket manager
async def consume_notifications():
    from confluent_kafka import Consumer
    import os
    conf = {
        'bootstrap.servers': os.getenv("KAFKA_BROKER", 'localhost:9092'),
        'group.id': 'doctor-notification-ws',
        'auto.offset.reset': 'latest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(['doctor-notifications'])
    
    logger.info("Starting Async WebSocket Kafka Consumer...")
    while True:
        # Non-blocking poll
        msg = consumer.poll(0.1)
        if msg is not None and not msg.error():
            val = json.loads(msg.value().decode('utf-8'))
            logger.info(f"WS Broadcasting: {val}")
            await manager.broadcast(val)
            
        await asyncio.sleep(0.5)

# Async task started during FastAPI startup
import threading
def start_kafka_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(consume_notifications())

from threading import Thread
Thread(target=start_kafka_background, daemon=True).start()
