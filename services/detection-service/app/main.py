from fastapi import FastAPI
from confluent_kafka import Consumer
import json
import threading
import uuid
import psycopg
import time
import traceback

app = FastAPI(title="detection-service")

KAFKA_BOOTSTRAP = "127.0.0.1:9092"
TOPIC = "logs.raw"
PG_DSN = "postgresql://app:app@127.0.0.1:5432/cloudops"

consumer = Consumer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": f"detector-{int(time.time())}",  # new group each restart
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
)
consumer.subscribe([TOPIC])

def consume_forever():
    print("Detector thread starting...")
    print("Kafka:", KAFKA_BOOTSTRAP, "Topic:", TOPIC)
    print("Postgres:", PG_DSN)
    conn = psycopg.connect(PG_DSN, autocommit=True)
    print("Postgres connected OK")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Kafka error:", msg.error())
            continue

        try:
            raw = msg.value().decode("utf-8")
            event = json.loads(raw)
            print(f"Consumed offset={msg.offset()} event_id={event.get('event_id')} severity={event.get('severity')}")

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO events (event_id, ts, source, log_type, severity, message, fields)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        event["event_id"],
                        event["ts"],
                        event.get("source"),
                        event.get("log_type"),
                        event.get("severity"),
                        event.get("message"),
                        json.dumps(event.get("fields", {})),
                    ),
                )

            sev = (event.get("severity") or "").lower()
            score = 0.95 if sev in {"high", "critical"} else 0.60
            label = "suspicious_activity" if score >= 0.9 else "informational"

            alert_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO alerts (alert_id, event_id, score, label, status, model_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (alert_id, event["event_id"], score, label, "new", "rule-v1"),
                )

            print(f"Inserted alert alert_id={alert_id} score={score} label={label}")

        except Exception:
            print("ERROR while processing message:")
            traceback.print_exc()

@app.on_event("startup")
def start_thread():
    threading.Thread(target=consume_forever, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok", "service": "detection-service"}
