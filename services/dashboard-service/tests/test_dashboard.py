from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "dashboard-service"


@pytest.mark.anyio
async def test_dashboard_page_returns_html():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Secure Agentic CloudOps SIEM" in resp.text


def _make_response(json_payload):
    """Build a mock httpx.Response with sync .json() and a no-op raise_for_status."""
    resp = MagicMock()
    resp.json = MagicMock(return_value=json_payload)
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


@pytest.mark.anyio
async def test_api_dashboard_data_returns_json():
    mock_stats = {
        "total_events": 100,
        "total_alerts": 25,
        "alerts_by_label": [],
        "alerts_by_status": [],
    }
    mock_alerts = {"count": 0, "alerts": []}
    mock_events = {"count": 0, "events": []}

    stats_resp = _make_response(mock_stats)
    alerts_resp = _make_response(mock_alerts)
    events_resp = _make_response(mock_events)

    with patch("app.main.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=[stats_resp, alerts_resp, events_resp])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/dashboard-data")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_events"] == 100
    assert body["total_alerts"] == 25
    assert "recent_alerts" in body


@pytest.mark.anyio
async def test_api_dashboard_data_handles_detection_failure():
    """When detection service is unreachable, endpoint returns fallback data."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/dashboard-data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_events"] == 0
    assert "error" in body
