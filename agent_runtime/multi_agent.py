"""Safe multi-agent orchestration for MARSEL ROAPP.

The runtime coordinates independent specialist agents while keeping production
mutation disabled by construction. Specialist handlers execute concurrently;
aggregation and verification happen only after every handler completes.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable


class Risk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskState(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    VERIFIED = "VERIFIED"
    DONE = "DONE"


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    domain: str
    permissions: frozenset[str] = frozenset({"read", "plan", "test", "document"})


@dataclass
class AgentTask:
    task_id: str
    objective: str
    risk: Risk = Risk.MEDIUM
    state: TaskState = TaskState.PLANNED
    evidence_reference: str | None = None
    verification_result: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _dispatch_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)
    _dispatch_started: bool = field(default=False, init=False, repr=False, compare=False)

    def __setattr__(self, name: str, value: Any) -> None:
        # Risk is an authorization boundary. Once initialized, it must not be
        # mutable while dispatch validation and handler submission are in flight.
        if name == "risk" and name in self.__dict__:
            raise AttributeError("task risk is immutable after initialization")
        super().__setattr__(name, value)


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    task_id: str
    status: str
    findings: tuple[str, ...] = ()
    proposed_changes: tuple[str, ...] = ()
    evidence_reference: str | None = None


class MultiAgentCoordinator:
    """Run independent specialists, then gate aggregation and completion."""

    DEFAULT_AGENTS = (
        AgentSpec("architect", "architecture"),
        AgentSpec("security", "security"),
        AgentSpec("data_integrity", "data-integrity"),
        AgentSpec("integration", "integrations"),
        AgentSpec("tester", "testing"),
        AgentSpec("verifier", "verification"),
        AgentSpec("documenter", "documentation"),
        AgentSpec("github", "change-management", frozenset({"read", "plan", "publish_branch", "open_pr"})),
    )

    def __init__(self, agents: Iterable[AgentSpec] | None = None, *, max_workers: int | None = None) -> None:
        self.agents = {a.agent_id: a for a in (agents or self.DEFAULT_AGENTS)}
        self.max_workers = max_workers

    def dispatch(
        self,
        task: AgentTask,
        handlers: dict[str, Callable[[AgentTask], AgentResult]],
    ) -> list[AgentResult]:
        """Validate once, dispatch approved handlers, then validate their identities."""
        with task._dispatch_lock:
            if task.state != TaskState.PLANNED:
                raise ValueError("task must start in PLANNED state")
            task._dispatch_started = True
            risk = task.risk
            if type(risk) is not Risk:
                task.state = TaskState.BLOCKED
                return [AgentResult("coordinator", task.task_id, "BLOCKED", ("invalid risk value; expected a Risk enum member",))]
            if risk is Risk.CRITICAL:
                task.state = TaskState.BLOCKED
                return [AgentResult("coordinator", task.task_id, "BLOCKED", ("critical risk requires explicit external authorization",))]

            unknown = set(handlers) - set(self.agents)
            if unknown:
                task.state = TaskState.BLOCKED
                raise KeyError(f"unknown agent: {sorted(unknown)!r}")

            task.state = TaskState.RUNNING
            agent_ids = list(handlers)
            executor = ThreadPoolExecutor(max_workers=self.max_workers or max(1, len(agent_ids)))
            try:
                futures = [executor.submit(handlers[agent_id], task) for agent_id in agent_ids]
            except BaseException:
                executor.shutdown(wait=True)
                task.state = TaskState.BLOCKED
                raise

        try:
            # Reading results in submission order keeps the public result order deterministic.
            results = [future.result() for future in futures]
        except BaseException:
            task.state = TaskState.BLOCKED
            raise
        finally:
            executor.shutdown(wait=True)

        for agent_id, result in zip(agent_ids, results):
            if result.agent_id != agent_id or result.task_id != task.task_id:
                task.state = TaskState.BLOCKED
                raise ValueError("agent result identity does not match dispatched task")
        return results

    @staticmethod
    def verify_and_complete(task: AgentTask, results: Iterable[AgentResult]) -> AgentTask:
        results = list(results)
        if task.state != TaskState.RUNNING:
            task.state = TaskState.BLOCKED
            return task
        if not results or any(r.status != "PASS" for r in results):
            task.state = TaskState.BLOCKED
            return task
        evidence = next((r.evidence_reference for r in results if r.evidence_reference), None)
        if not evidence:
            task.state = TaskState.BLOCKED
            return task
        task.evidence_reference = evidence
        task.verification_result = "PASS"
        task.state = TaskState.VERIFIED
        task.state = TaskState.DONE
        return task

    @staticmethod
    def production_write_allowed() -> bool:
        """Hard safety invariant: orchestration never authorizes production WRITE."""
        return False
