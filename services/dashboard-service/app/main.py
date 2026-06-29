import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DETECTION_URL = os.getenv("DETECTION_URL", "http://detection-service:8002")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="dashboard-service")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard-service"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/api/dashboard-data")
async def dashboard_data():
    """Aggregate data from the detection service for the dashboard."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            stats_resp = await client.get(f"{DETECTION_URL}/stats")
            stats_resp.raise_for_status()
            stats = stats_resp.json()

            alerts_resp = await client.get(
                f"{DETECTION_URL}/alerts", params={"limit": 50}
            )
            alerts_resp.raise_for_status()
            alerts = alerts_resp.json()

            events_resp = await client.get(
                f"{DETECTION_URL}/events", params={"limit": 10}
            )
            events_resp.raise_for_status()
            events = events_resp.json()

        # Build severity distribution from recent alerts
        severity_counts: dict[str, int] = {}
        for alert in alerts.get("alerts", []):
            label = alert.get("label", "unknown")
            # Map labels to approximate severity buckets
            severity_counts[label] = severity_counts.get(label, 0) + 1

        return {
            "total_events": stats.get("total_events", 0),
            "total_alerts": stats.get("total_alerts", 0),
            "alerts_by_label": stats.get("alerts_by_label", []),
            "alerts_by_status": stats.get("alerts_by_status", []),
            "severity_distribution": severity_counts,
            "recent_alerts": alerts.get("alerts", [])[:20],
            "recent_events": events.get("events", [])[:10],
            "detection_rules_active": len(
                {
                    a.get("model_version")
                    for a in alerts.get("alerts", [])
                    if a.get("model_version")
                }
            ),
        }

    except httpx.HTTPError:
        # Return empty data so the dashboard still renders
        return {
            "total_events": 0,
            "total_alerts": 0,
            "alerts_by_label": [],
            "alerts_by_status": [],
            "severity_distribution": {},
            "recent_alerts": [],
            "recent_events": [],
            "detection_rules_active": 0,
            "error": "Unable to reach detection service",
        }
