"""Agentic Engine — LLM-powered alert triage service."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.triage import TriageResult, get_triager

VECTOR_KB_URL = os.getenv("VECTOR_KB_URL", "http://127.0.0.1:8005")
DETECTION_URL = os.getenv("DETECTION_URL", "http://127.0.0.1:8002")

app = FastAPI(title="agentic-engine", version="0.1.0")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class TriageRequest(BaseModel):
    alert: dict[str, Any] = Field(
        ..., description="Alert object (alert_id, score, label, …)"
    )
    event: dict[str, Any] = Field(
        ..., description="Source event (event_id, severity, message, fields, …)"
    )


class TriageResponse(BaseModel):
    severity_assessment: str
    recommended_action: str
    confidence: float
    reasoning: str
    ioc_indicators: list[str]
    engine: str = Field(
        description="Which engine produced the result (rule-based | llm)"
    )


class EnrichRequest(BaseModel):
    alert: dict[str, Any]
    event: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=50)


class EnrichResponse(BaseModel):
    alert_id: str
    similar_alerts: list[dict[str, Any]]
    threat_intel_matches: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    triager = get_triager()
    engine = type(triager).__name__
    return {"status": "ok", "service": "agentic-engine", "engine": engine}


@app.post("/triage", response_model=TriageResponse)
def triage_alert(req: TriageRequest):
    """Run triage analysis on an alert + event payload."""
    triager = get_triager()
    try:
        result: TriageResult = triager.triage(req.alert, req.event)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Triage failed: {exc}")

    engine_name = "llm" if type(triager).__name__ == "LLMTriager" else "rule-based"

    return TriageResponse(
        severity_assessment=result.severity_assessment,
        recommended_action=result.recommended_action,
        confidence=result.confidence,
        reasoning=result.reasoning,
        ioc_indicators=result.ioc_indicators,
        engine=engine_name,
    )


@app.post("/enrich", response_model=EnrichResponse)
async def enrich_alert(req: EnrichRequest):
    """Enrich an alert with context from the vector knowledge base."""
    alert_id = req.alert.get("alert_id", "unknown")
    label = req.alert.get("label", "")
    message = req.event.get("message", label)
    query_text = f"{label} {message}"

    similar_alerts: list[dict[str, Any]] = []
    threat_intel: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Search similar alerts
        try:
            resp = await client.post(
                f"{VECTOR_KB_URL}/search",
                json={"query": query_text, "collection": "alerts", "top_k": req.top_k},
            )
            if resp.status_code == 200:
                similar_alerts = resp.json().get("results", [])
        except httpx.RequestError:
            pass  # vector-kb may not be running

        # Search threat intel
        try:
            resp = await client.post(
                f"{VECTOR_KB_URL}/search",
                json={
                    "query": query_text,
                    "collection": "threat_intel",
                    "top_k": req.top_k,
                },
            )
            if resp.status_code == 200:
                threat_intel = resp.json().get("results", [])
        except httpx.RequestError:
            pass

    return EnrichResponse(
        alert_id=alert_id,
        similar_alerts=similar_alerts,
        threat_intel_matches=threat_intel,
    )
