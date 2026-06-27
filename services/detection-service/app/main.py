import json
import os
import threading
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import psycopg
from confluent_kafka import Consumer
from fastapi import FastAPI, Query

from app.rules import evaluate

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BROKER", "127.0.0.1:9092")
TOPIC = "logs.raw"
PG_DSN = os.getenv("PG_DSN", "postgresql://app:app@127.0.0.1:5432/cloudops")


def consume_forever():
    print(f"Detector thread starting (broker={KAFKA_BOOTSTRAP})")

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "group.id": f"detector-{int(time.time())}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([TOPIC])

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
            print(
                f"Consumed offset={msg.offset()} event_id={event.get('event_id')} "
                f"severity={event.get('severity')}"
            )

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

            result = evaluate(event)
            alert_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO alerts (alert_id, event_id, score, label, status, model_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (alert_id, event["event_id"], result.score, result.label, "new", result.rule_name),
                )

            print(
                f"Alert alert_id={alert_id} score={result.score} "
                f"label={result.label} rule={result.rule_name}"
            )

        except Exception:
            print("ERROR while processing message:")
            traceback.print_exc()


@asynccontextmanager
async def lifespan(application: FastAPI):
    threading.Thread(target=consume_forever, daemon=True).start()
    yield


app = FastAPI(title="detection-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "detection-service"}


@app.get("/alerts")
def list_alerts(
    status: Optional[str] = Query(None),
    label: Optional[str] = Query(None),
    min_score: float = Query(0.0),
    limit: int = Query(50, le=500),
):
    conn = psycopg.connect(PG_DSN, autocommit=True)
    query = "SELECT alert_id, event_id, score, label, status, model_version, created_at FROM alerts WHERE score >= %s"
    params: list = [min_score]

    if status:
        query += " AND status = %s"
        params.append(status)
    if label:
        query += " AND label = %s"
        params.append(label)

    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

    conn.close()
    return {"count": len(rows), "alerts": [dict(zip(columns, row)) for row in rows]}


@app.get("/events")
def list_events(
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
):
    conn = psycopg.connect(PG_DSN, autocommit=True)
    query = "SELECT event_id, ts, source, log_type, severity, message, fields, created_at FROM events WHERE 1=1"
    params: list = []

    if severity:
        query += " AND severity = %s"
        params.append(severity)
    if source:
        query += " AND source = %s"
        params.append(source)

    query += " ORDER BY ts DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

    conn.close()
    return {"count": len(rows), "events": [dict(zip(columns, row)) for row in rows]}


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    conn = psycopg.connect(PG_DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.alert_id, a.event_id, a.score, a.label, a.status, a.model_version, a.created_at,
                   e.source, e.log_type, e.severity, e.message, e.fields
            FROM alerts a JOIN events e ON a.event_id = e.event_id
            WHERE a.alert_id = %s
            """,
            (alert_id,),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Alert not found")
        columns = [desc[0] for desc in cur.description]

    conn.close()
    return dict(zip(columns, row))


@app.patch("/alerts/{alert_id}")
def update_alert_status(alert_id: str, status: str = Query(...)):
    valid = {"new", "investigating", "resolved", "false_positive"}
    if status not in valid:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")

    conn = psycopg.connect(PG_DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE alerts SET status = %s WHERE alert_id = %s RETURNING alert_id",
            (status, alert_id),
        )
        row = cur.fetchone()
    conn.close()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"alert_id": alert_id, "status": status}


@app.get("/stats")
def stats():
    conn = psycopg.connect(PG_DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM events")
        event_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alerts")
        alert_count = cur.fetchone()[0]
        cur.execute(
            "SELECT label, COUNT(*) FROM alerts GROUP BY label ORDER BY COUNT(*) DESC"
        )
        by_label = [{"label": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT status, COUNT(*) FROM alerts GROUP BY status ORDER BY COUNT(*) DESC"
        )
        by_status = [{"status": r[0], "count": r[1]} for r in cur.fetchall()]
    conn.close()

    return {
        "total_events": event_count,
        "total_alerts": alert_count,
        "alerts_by_label": by_label,
        "alerts_by_status": by_status,
    }
