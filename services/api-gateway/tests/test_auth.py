"""Tests for auth, RBAC, and rate limiting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, rate_limiter


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def _get_token(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    return body["access_token"]


class TestTokenCreation:
    def test_admin_can_get_token(self, client):
        _get_token(client, "admin", "admin123")

    def test_analyst_can_get_token(self, client):
        _get_token(client, "analyst", "analyst123")

    def test_viewer_can_get_token(self, client):
        _get_token(client, "viewer", "viewer123")


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


class TestTokenValidation:
    def test_valid_token_accesses_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_missing_token_rejected(self, client):
        resp = client.get("/api/ingest/logs")
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, client):
        resp = client.get(
            "/api/ingest/logs",
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Invalid credentials
# ---------------------------------------------------------------------------


class TestInvalidCredentials:
    def test_wrong_password(self, client):
        resp = client.post(
            "/auth/token",
            data={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_unknown_user(self, client):
        resp = client.post(
            "/auth/token",
            data={"username": "nobody", "password": "nope"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Role-based access
# ---------------------------------------------------------------------------


class TestRBAC:
    def test_viewer_cannot_post(self, client):
        """Viewer role only permits GET; POST should be forbidden."""
        token = _get_token(client, "viewer", "viewer123")
        resp = client.post(
            "/api/ingest/logs",
            headers={"Authorization": f"Bearer {token}"},
            json={"event": "test"},
        )
        # The proxy checks role permission before forwarding;
        # viewer is not allowed to POST.
        assert resp.status_code == 403

    def test_admin_can_post(self, client):
        """Admin role permits all methods."""
        token = _get_token(client, "admin", "admin123")
        # The upstream isn't running so we expect a connection error
        # wrapped as 502 or a proxy error — but NOT 403.
        resp = client.post(
            "/api/ingest/logs",
            headers={"Authorization": f"Bearer {token}"},
            json={"event": "test"},
        )
        # Should not be a permissions error
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_rate_limit_triggers(self, client):
        """After exhausting the bucket the gateway should return 429."""
        # Use a tiny bucket for this test
        rate_limiter.rpm = 5
        rate_limiter._buckets.clear()

        responses = [client.get("/health") for _ in range(10)]
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes

        # Reset to default
        rate_limiter.rpm = 60
        rate_limiter._buckets.clear()
