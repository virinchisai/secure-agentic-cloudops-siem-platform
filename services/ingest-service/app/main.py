from fastapi import FastAPI
from pydantic import BaseModel
from confluent_kafka import Producer
import json
import uuid
from datetime import datetime

app = FastAPI()

KAFKA_BROKER = "localhost:9092"
TOPIC = "logs.raw"

producer = Producer({
    "bootstrap.servers": KAFKA_BROKER
})

class IngestEvent(BaseModel):
    source: str
    log_type: str
    severity: str
    message: str
    fields: dict

@app.get("/health")
def health():
    return {"status": "ok", "service": "ingest-service"}

@app.post("/ingest")
def ingest(event: IngestEvent):
    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": datetime.utcnow().isoformat(),
        **event.dict()
    }

    producer.produce(
        TOPIC,
        key=payload["event_id"],
        value=json.dumps(payload)
    )
    producer.flush()

    return {"status": "accepted", "event_id": payload["event_id"]}

