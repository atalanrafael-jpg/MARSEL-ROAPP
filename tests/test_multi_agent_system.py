import threading

import pytest

from agent_runtime.multi_agent import (
    AgentResult,
    AgentTask,
    MultiAgentCoordinator,
    Risk,
    TaskState,
)
from agent_runtime.github_bridge import ChangeSet, GatedGitHubBridge


def test_default_agents_cover_required_specialties():
    coordinator = MultiAgentCoordinator()
    assert {"architect", "security", "data_integrity", "integration", "tester", "verifier", "documenter", "github"} <= set(coordinator.agents)


def test_dispatch_runs_specialists_and_completion_requires_evidence():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-1", "audit integration boundary")
    handlers = {
        name: (lambda task, name=name: AgentResult(name, task.task_id, "PASS", evidence_reference="evidence/T-1.json"))
        for name in coordinator.agents
    }
    results = coordinator.dispatch(task, handlers)
    coordinator.verify_and_complete(task, results)
    assert task.state == TaskState.DONE
    assert task.verification_result == "PASS"
    assert task.evidence_reference == "evidence/T-1.json"


def test_dispatch_executes_independent_handlers_concurrently():
    coordinator = MultiAgentCoordinator(max_workers=2)
    task = AgentTask("T-PAR", "parallel audit")
    barrier = threading.Barrier(2)

    def handler(agent_id):
        def run(current):
            barrier.wait(timeout=1)
            return AgentResult(agent_id, current.task_id, "PASS", evidence_reference="evidence/T-PAR.json")

        return run

    results = coordinator.dispatch(task, {"architect": handler("architect"), "security": handler("security")})
    assert [result.agent_id for result in results] == ["architect", "security"]


def test_failed_agent_blocks_completion():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-2", "test")
    task.state = TaskState.RUNNING
    coordinator.verify_and_complete(task, [AgentResult("tester", task.task_id, "FAIL")])
    assert task.state == TaskState.BLOCKED


def test_completion_requires_running_state():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-STATE", "test")
    result = AgentResult("tester", task.task_id, "PASS", evidence_reference="evidence/T-STATE.json")
    coordinator.verify_and_complete(task, [result])
    assert task.state == TaskState.BLOCKED


def test_result_identity_mismatch_blocks_task():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-ID", "test")
    with pytest.raises(ValueError):
        coordinator.dispatch(task, {"tester": lambda current: AgentResult("security", current.task_id, "PASS")})
    assert task.state == TaskState.BLOCKED


def test_critical_task_is_blocked():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-3", "production mutation", risk=Risk.CRITICAL)
    result = coordinator.dispatch(task, {})
    assert task.state == TaskState.BLOCKED
    assert result[0].status == "BLOCKED"


def test_production_write_is_never_authorized():
    assert MultiAgentCoordinator.production_write_allowed() is False


def test_github_bridge_requires_explicit_publish_gate():
    publisher = object()
    bridge = GatedGitHubBridge(publisher, allow_publish=False)
    changes = ChangeSet("T-4", "feat/example", "fix: example", ("x.py",), "evidence/T-4.json")
    with pytest.raises(PermissionError):
        bridge.publish(changes)


@pytest.mark.parametrize("invalid_risk", ["critical", "URGENT", "", None, 123])
def test_dispatch_fails_closed_on_invalid_risk_before_handler(invalid_risk):
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-INVALID-RISK", "must not dispatch", risk=invalid_risk)
    invoked = []

    result = coordinator.dispatch(
        task,
        {"tester": lambda current: invoked.append(current.task_id) or AgentResult("tester", current.task_id, "PASS")},
    )

    assert task.state == TaskState.BLOCKED
    assert result[0].status == "BLOCKED"
    assert "invalid risk value" in result[0].findings[0]
    assert invoked == []


def test_dispatch_rejects_class_spoofed_risk_before_handler():
    class SpoofedRisk:
        @property
        def __class__(self):
            return Risk

    spoofed = SpoofedRisk()
    assert isinstance(spoofed, Risk)
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-SPOOFED-RISK", "must not dispatch", risk=spoofed)
    invoked = []

    result = coordinator.dispatch(
        task,
        {"tester": lambda current: invoked.append(current.task_id) or AgentResult("tester", current.task_id, "PASS")},
    )

    assert task.state == TaskState.BLOCKED
    assert result[0].status == "BLOCKED"
    assert "invalid risk value" in result[0].findings[0]
    assert invoked == []


def test_risk_cannot_change_after_dispatch_starts():
    coordinator = MultiAgentCoordinator()
    task = AgentTask("T-RISK-RACE", "risk must remain stable")
    handler_started = threading.Event()
    release_handler = threading.Event()
    dispatch_errors = []

    def handler(current):
        handler_started.set()
        assert release_handler.wait(timeout=2)
        return AgentResult("tester", current.task_id, "PASS", evidence_reference="evidence/T-RISK-RACE.json")

    def run_dispatch():
        try:
            coordinator.dispatch(task, {"tester": handler})
        except BaseException as exc:
            dispatch_errors.append(exc)

    worker = threading.Thread(target=run_dispatch)
    worker.start()
    assert handler_started.wait(timeout=2)
    with pytest.raises(AttributeError, match="risk is immutable after initialization"):
        task.risk = Risk.CRITICAL
    release_handler.set()
    worker.join(timeout=3)

    assert not worker.is_alive()
    assert dispatch_errors == []
    assert task.risk is Risk.MEDIUM
    assert task.state == TaskState.RUNNING
def test_task_risk_cannot_be_mutated_after_initialization():
    task = AgentTask("T-IMMUTABLE-RISK", "risk must remain stable", risk=Risk.HIGH)

    with pytest.raises(AttributeError, match="risk is immutable"):
        task.risk = Risk.CRITICAL

    assert task.risk is Risk.HIGH
