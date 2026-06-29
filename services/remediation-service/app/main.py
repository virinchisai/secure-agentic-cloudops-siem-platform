"""Remediation Workflow Engine — FastAPI service (port 8006)."""

import os
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.workflows import WorkflowEngine

DETECTION_URL = os.getenv("DETECTION_URL", "http://detection-service:8002")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

engine = WorkflowEngine()

app = FastAPI(title="remediation-service", version="0.1.0")


# ---- request / response models ----

class ExecuteRequest(BaseModel):
    workflow_id: str
    alert_id: str


# ---- routes ----

@app.get("/health")
def health():
    return {"status": "ok", "service": "remediation-service"}


@app.get("/workflows")
def list_workflows():
    workflows = engine.workflows
    return {
        "count": len(workflows),
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "trigger_labels": w.trigger_labels,
                "steps": len(w.steps),
            }
            for w in workflows
        ],
    }


@app.post("/workflows/execute")
def execute_workflow(req: ExecuteRequest):
    try:
        execution = engine.execute(req.workflow_id, req.alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return asdict(execution)


@app.get("/workflows/{execution_id}/status")
def workflow_status(execution_id: str):
    execution = engine.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return asdict(execution)
