from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("app.main.producer") as mock_producer:
        mock_producer.produce = MagicMock()
        mock_producer.flush = MagicMock()
        from app.main import app

        yield TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "ingest-service"


def test_ingest_valid_event(client):
    event = {
        "source": "firewall",
        "log_type": "network",
        "severity": "high",
        "message": "Suspicious connection",
        "fields": {"src_ip": "10.0.0.1"},
    }
    r = client.post("/ingest", json=event)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "accepted"
    assert "event_id" in data


def test_ingest_missing_fields(client):
    r = client.post("/ingest", json={"source": "test"})
    assert r.status_code == 422


def test_ingest_invalid_severity(client):
    event = {
        "source": "firewall",
        "log_type": "network",
        "severity": "INVALID",
        "message": "test",
        "fields": {},
    }
    r = client.post("/ingest", json=event)
    assert r.status_code == 422


def test_ingest_batch(client):
    events = [
        {
            "source": "firewall",
            "log_type": "network",
            "severity": "low",
            "message": "Normal traffic",
            "fields": {},
        },
        {
            "source": "vpn",
            "log_type": "authentication",
            "severity": "high",
            "message": "Failed login",
            "fields": {},
        },
    ]
    r = client.post("/ingest/batch", json=events)
    assert r.status_code == 202
    data = r.json()
    assert data["count"] == 2
    assert len(data["events"]) == 2


def test_ingest_empty_source_rejected(client):
    event = {
        "source": "",
        "log_type": "network",
        "severity": "low",
        "message": "test",
        "fields": {},
    }
    r = client.post("/ingest", json=event)
    assert r.status_code == 422
