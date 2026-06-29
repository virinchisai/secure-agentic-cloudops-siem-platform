"""Tests for remediation workflows."""

from app.workflows import ExecutionStatus, WorkflowEngine


def test_list_workflows():
    engine = WorkflowEngine()
    workflows = engine.workflows
    assert len(workflows) == 4
    ids = {w.id for w in workflows}
    assert ids == {"block_ip", "isolate_host", "disable_user", "escalate"}


def test_execute_block_ip():
    engine = WorkflowEngine()
    execution = engine.execute("block_ip", alert_id="alert-001")
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.workflow_id == "block_ip"
    assert execution.alert_id == "alert-001"
    assert execution.steps_completed == 4
    assert execution.started_at is not None
    assert execution.completed_at is not None
    assert len(execution.details) == 4


def test_execute_unknown_workflow_raises():
    engine = WorkflowEngine()
    try:
        engine.execute("nonexistent", alert_id="alert-001")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "nonexistent" in str(exc)


def test_execution_status_tracking():
    engine = WorkflowEngine()
    execution = engine.execute("escalate", alert_id="alert-002")
    retrieved = engine.get_execution(execution.execution_id)
    assert retrieved is not None
    assert retrieved.execution_id == execution.execution_id
    assert retrieved.status == ExecutionStatus.COMPLETED
    assert retrieved.steps_completed == 3
