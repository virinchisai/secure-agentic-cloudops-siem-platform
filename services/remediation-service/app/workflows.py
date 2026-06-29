"""Remediation workflow definitions and execution engine."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    action: str
    target: str
    params: dict = field(default_factory=dict)


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    trigger_labels: list[str] = field(default_factory=list)


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow_id: str
    alert_id: str
    status: ExecutionStatus
    steps_completed: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    details: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Built-in workflow definitions
# ---------------------------------------------------------------------------

BUILTIN_WORKFLOWS: list[Workflow] = [
    Workflow(
        id="block_ip",
        name="Block Source IP",
        description="Block the source IP associated with the alert via firewall rules (simulated).",
        steps=[
            WorkflowStep(action="extract_ip", target="alert", params={}),
            WorkflowStep(action="block_ip", target="firewall", params={"duration_hours": 24}),
            WorkflowStep(action="update_alert_status", target="alert", params={"status": "resolved"}),
            WorkflowStep(action="log_action", target="audit", params={}),
        ],
        trigger_labels=["brute_force_attempt", "suspicious_network_activity"],
    ),
    Workflow(
        id="isolate_host",
        name="Isolate Compromised Host",
        description="Network-isolate a compromised host and notify the SOC team (simulated).",
        steps=[
            WorkflowStep(action="identify_host", target="alert", params={}),
            WorkflowStep(action="isolate_host", target="network", params={}),
            WorkflowStep(action="update_alert_status", target="alert", params={"status": "investigating"}),
            WorkflowStep(action="notify", target="soc_team", params={"channel": "slack"}),
        ],
        trigger_labels=["data_exfiltration_risk", "privilege_escalation"],
    ),
    Workflow(
        id="disable_user",
        name="Disable Compromised User Account",
        description="Disable a user account that has been compromised (simulated).",
        steps=[
            WorkflowStep(action="identify_user", target="alert", params={}),
            WorkflowStep(action="disable_account", target="iam", params={}),
            WorkflowStep(action="revoke_sessions", target="iam", params={}),
            WorkflowStep(action="update_alert_status", target="alert", params={"status": "resolved"}),
            WorkflowStep(action="log_action", target="audit", params={}),
        ],
        trigger_labels=["brute_force_attempt", "privilege_escalation"],
    ),
    Workflow(
        id="escalate",
        name="Escalate to SOC Team",
        description="Escalate a high-severity alert to the SOC team for manual review (simulated).",
        steps=[
            WorkflowStep(action="update_alert_status", target="alert", params={"status": "investigating"}),
            WorkflowStep(action="notify", target="soc_team", params={"channel": "pagerduty"}),
            WorkflowStep(action="log_action", target="audit", params={}),
        ],
        trigger_labels=["high_severity_event"],
    ),
]


def _get_workflow_map() -> dict[str, Workflow]:
    return {w.id: w for w in BUILTIN_WORKFLOWS}


# ---------------------------------------------------------------------------
# Simulated step executors
# ---------------------------------------------------------------------------

def _simulate_step(step: WorkflowStep, alert_id: str) -> str:
    """Simulate executing a single workflow step. Returns a log message."""
    match step.action:
        case "extract_ip":
            msg = f"[SIM] Extracted source IP from alert {alert_id}"
        case "block_ip":
            duration = step.params.get("duration_hours", 24)
            msg = f"[SIM] Blocked IP via {step.target} for {duration}h"
        case "update_alert_status":
            new_status = step.params.get("status", "investigating")
            msg = f"[SIM] Updated alert {alert_id} status to '{new_status}'"
        case "log_action":
            msg = f"[SIM] Logged remediation action to {step.target}"
        case "identify_host":
            msg = f"[SIM] Identified compromised host from alert {alert_id}"
        case "isolate_host":
            msg = f"[SIM] Isolated host on {step.target}"
        case "notify":
            channel = step.params.get("channel", "email")
            msg = f"[SIM] Notified {step.target} via {channel}"
        case "identify_user":
            msg = f"[SIM] Identified compromised user from alert {alert_id}"
        case "disable_account":
            msg = f"[SIM] Disabled user account via {step.target}"
        case "revoke_sessions":
            msg = f"[SIM] Revoked active sessions via {step.target}"
        case _:
            msg = f"[SIM] Executed {step.action} on {step.target}"
    logger.info(msg)
    return msg


# ---------------------------------------------------------------------------
# Workflow engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """Executes remediation workflows and tracks their status."""

    def __init__(self) -> None:
        self._workflows = _get_workflow_map()
        self._executions: dict[str, WorkflowExecution] = {}

    @property
    def workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def execute(self, workflow_id: str, alert_id: str) -> WorkflowExecution:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            alert_id=alert_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            for step in workflow.steps:
                detail = _simulate_step(step, alert_id)
                execution.details.append(detail)
                execution.steps_completed += 1

            execution.status = ExecutionStatus.COMPLETED
        except Exception as exc:
            logger.exception("Workflow %s failed at step %d", workflow_id, execution.steps_completed)
            execution.status = ExecutionStatus.FAILED
            execution.details.append(f"[ERROR] {exc}")

        execution.completed_at = datetime.now(timezone.utc).isoformat()
        self._executions[execution.execution_id] = execution
        return execution

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def list_executions(self) -> list[WorkflowExecution]:
        return list(self._executions.values())
