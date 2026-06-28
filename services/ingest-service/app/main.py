import json
import os
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ingest-service")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "logs.raw"

producer = Producer({"bootstrap.servers": KAFKA_BROKER})


class IngestEvent(BaseModel):
    source: str = Field(..., min_length=1)
    log_type: str = Field(..., min_length=1)
    severity: str = Field(..., pattern="^(low|medium|high|critical|info)$")
    message: str = Field(..., min_length=1)
    fields: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingest-service"}


@app.post("/ingest", status_code=202)
def ingest(event: IngestEvent):
    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        **event.model_dump(),
    }

    try:
        producer.produce(
            TOPIC,
            key=payload["event_id"],
            value=json.dumps(payload),
        )
        producer.flush(timeout=5)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Kafka unavailable: {exc}")

    return {"status": "accepted", "event_id": payload["event_id"]}


@app.post("/ingest/batch", status_code=202)
def ingest_batch(events: list[IngestEvent]):
    results = []
    for event in events:
        payload = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            **event.model_dump(),
        }
        producer.produce(
            TOPIC,
            key=payload["event_id"],
            value=json.dumps(payload),
        )
        results.append({"event_id": payload["event_id"]})

    producer.flush(timeout=10)
    return {"status": "accepted", "count": len(results), "events": results}
