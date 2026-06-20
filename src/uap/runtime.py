from __future__ import annotations

import asyncio
import inspect
from typing import Any

from .capabilities import CapabilityRegistry
from .context import ContextManager
from .errors import ApprovalRequiredError, UAPError, ValidationError
from .events import EventBus
from .models import SUPPORTED_UAP_VERSIONS, TaskEnvelope, TaskGraph, TaskNode, UAPEvent, new_id
from .planner import SimplePlanner
from .policy import PolicyEngine
from .provenance import ProvenanceStore
from .validation import validate_envelope_minimal


def _detect_cycle(nodes: list[TaskNode]) -> bool:
    node_ids = {n.id for n in nodes}
    # 0 = unvisited, 1 = in-stack (gray), 2 = done (black)
    state: dict[str, int] = {n.id: 0 for n in nodes}
    adj = {n.id: [d for d in n.depends_on if d in node_ids] for n in nodes}

    def visit(v: str) -> bool:
        state[v] = 1
        for u in adj[v]:
            if state[u] == 1:  # back edge = cycle
                return True
            if state[u] == 0 and visit(u):
                return True
        state[v] = 2
        return False

    return any(visit(n.id) for n in nodes if state[n.id] == 0)


def _check_missing_deps(nodes: list[TaskNode]) -> str | None:
    node_ids = {n.id for n in nodes}
    for n in nodes:
        for dep in n.depends_on:
            if dep not in node_ids:
                return dep
    return None


class UAPRuntime:
    """Reference UAP runtime.

    The runtime accepts UAP task envelopes, plans capability calls, checks policy,
    executes capabilities, compacts results, emits events, and records provenance.
    """

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        context_manager: ContextManager | None = None,
        event_bus: EventBus | None = None,
        provenance: ProvenanceStore | None = None,
    ) -> None:
        self.registry = registry or CapabilityRegistry()
        self.policy_engine = policy_engine or PolicyEngine()
        self.context_manager = context_manager or ContextManager()
        self.event_bus = event_bus or EventBus()
        self.provenance = provenance or ProvenanceStore()
        self.planner = SimplePlanner(self.registry)
        self.tasks: dict[str, dict[str, Any]] = {}
        self._pending: dict[str, dict[str, Any]] = {}
        self._cancel: dict[str, asyncio.Event] = {}

    async def invoke(
        self, envelope_or_dict: TaskEnvelope | dict[str, Any], graph: TaskGraph | None = None
    ) -> dict[str, Any]:
        if isinstance(envelope_or_dict, dict):
            try:
                validate_envelope_minimal(envelope_or_dict)
            except ValidationError as exc:
                task_id = envelope_or_dict.get("task_id") or new_id("tsk")
                error_response = {
                    "task_id": task_id,
                    "status": "failed",
                    "error": exc.to_dict(),
                }
                trace_id = str(
                    envelope_or_dict.get("metadata", {}).get("trace_id") or new_id("trc")
                )
                await self.event_bus.publish(
                    UAPEvent(
                        type="error.terminal",
                        task_id=task_id,
                        data=exc.to_dict(),
                        trace_id=trace_id,
                    )
                )
                await self.event_bus.publish(
                    UAPEvent(
                        type="task.failed",
                        task_id=task_id,
                        data=exc.to_dict(),
                        trace_id=trace_id,
                    )
                )
                return error_response

        envelope = (
            envelope_or_dict
            if isinstance(envelope_or_dict, TaskEnvelope)
            else TaskEnvelope.from_dict(envelope_or_dict)
        )

        if envelope.uap not in SUPPORTED_UAP_VERSIONS:
            exc = ValidationError(
                code="UNSUPPORTED_VERSION",
                message=f"UAP version {envelope.uap!r} is not supported. Supported: {sorted(SUPPORTED_UAP_VERSIONS)}",
                recoverable=False,
                safe_retry=False,
            )
            trace_id = str(envelope.metadata.get("trace_id") or new_id("trc"))
            envelope.metadata["trace_id"] = trace_id
            self.tasks[envelope.task_id] = {"status": "failed", "error": exc.to_dict()}
            await self.event_bus.publish(
                UAPEvent(
                    type="error.terminal",
                    task_id=envelope.task_id,
                    data=exc.to_dict(),
                    trace_id=trace_id,
                )
            )
            await self.event_bus.publish(
                UAPEvent(
                    type="task.failed",
                    task_id=envelope.task_id,
                    data=exc.to_dict(),
                    trace_id=trace_id,
                )
            )
            return {"task_id": envelope.task_id, "status": "failed", "error": exc.to_dict()}

        envelope.metadata.setdefault("trace_id", new_id("trc"))
        self.tasks[envelope.task_id] = {"status": "accepted", "result": None}
        self._cancel[envelope.task_id] = asyncio.Event()
        await self.emit(envelope, "task.accepted", {"intent": envelope.intent.goal})

        # Support custom execution graph from envelope if provided
        if graph is None and envelope.execution.graph is not None:
            nodes = []
            for node_dict in envelope.execution.graph.get("nodes", []):
                nodes.append(
                    TaskNode(
                        id=node_dict["id"],
                        capability=node_dict["capability"],
                        input=dict(node_dict.get("input", {})),
                        depends_on=list(node_dict.get("depends_on", [])),
                        requires_approval=bool(node_dict.get("requires_approval", False)),
                    )
                )
            graph = TaskGraph(nodes=nodes)

        graph = graph or self.planner.plan(envelope)
        await self.emit(
            envelope, "plan.proposed", {"graph": [node.__dict__ for node in graph.nodes]}
        )
        try:
            result = await self.execute_graph(envelope, graph)
            self.tasks[envelope.task_id] = {"status": "completed", "result": result}
            await self.emit(envelope, "task.completed", {"result": result})
            return {"task_id": envelope.task_id, "status": "completed", "result": result}
        except ApprovalRequiredError as exc:
            self.tasks[envelope.task_id] = {
                "status": "waiting_for_approval",
                "error": exc.to_dict(),
            }
            self._pending[envelope.task_id] = {
                "envelope": envelope,
                "graph": exc.graph,
                "completed": exc.completed,
                "capability_id": exc.details.get("capability_id"),
            }
            await self.emit(envelope, "approval.requested", exc.to_dict())
            return {
                "task_id": envelope.task_id,
                "status": "waiting_for_approval",
                "error": exc.to_dict(),
            }
        except UAPError as exc:
            if exc.code == "TASK_CANCELLED":
                self.tasks[envelope.task_id] = {"status": "cancelled", "error": exc.to_dict()}
                await self.emit(envelope, "task.cancelled", exc.to_dict())
                return {"task_id": envelope.task_id, "status": "cancelled", "error": exc.to_dict()}
            else:
                self.tasks[envelope.task_id] = {"status": "failed", "error": exc.to_dict()}
                event_type = "error.recoverable" if exc.recoverable else "error.terminal"
                await self.emit(envelope, event_type, exc.to_dict())
                await self.emit(envelope, "task.failed", exc.to_dict())
                return {"task_id": envelope.task_id, "status": "failed", "error": exc.to_dict()}
        except Exception as exc:  # pragma: no cover - safety net
            error = UAPError(
                code="UNHANDLED_ERROR", message=str(exc), recoverable=False, safe_retry=False
            )
            self.tasks[envelope.task_id] = {"status": "failed", "error": error.to_dict()}
            await self.emit(envelope, "error.terminal", error.to_dict())
            await self.emit(envelope, "task.failed", error.to_dict())
            return {"task_id": envelope.task_id, "status": "failed", "error": error.to_dict()}

    async def execute_graph(
        self,
        envelope: TaskEnvelope,
        graph: TaskGraph,
        completed_so_far: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Validate upfront
        if _detect_cycle(graph.nodes):
            raise UAPError(
                code="PLAN_GRAPH_CYCLE",
                message="Task graph contains a cycle",
                recoverable=False,
                safe_retry=False,
            )
        missing_dep = _check_missing_deps(graph.nodes)
        if missing_dep is not None:
            raise UAPError(
                code="PLAN_MISSING_DEPENDENCY",
                message=f"Task graph has missing dependency: {missing_dep}",
                recoverable=False,
                safe_retry=False,
            )

        completed: dict[str, Any] = dict(completed_so_far or {})
        pending: dict[str, TaskNode] = {
            node.id: node for node in graph.nodes if node.id not in completed
        }
        if not pending and not completed:
            return {"message": "No matching capability found", "artifacts": []}

        while pending:
            if self._cancel.get(envelope.task_id, asyncio.Event()).is_set():
                raise UAPError(
                    code="TASK_CANCELLED",
                    message="Task cancelled by client",
                    recoverable=False,
                    safe_retry=False,
                )

            ready = [
                node
                for node in pending.values()
                if all(dep in completed for dep in node.depends_on)
            ]
            if not ready:
                raise UAPError(
                    code="PLAN_MISSING_DEPENDENCY",
                    message="Unresolvable dependency — check for missing nodes.",
                    recoverable=False,
                    safe_retry=False,
                )
            sem = asyncio.Semaphore(max(1, envelope.execution.parallelism))

            async def run_one(node: TaskNode):
                async with sem:
                    try:
                        return node.id, await self.execute_node(envelope, node, completed)
                    except ApprovalRequiredError as exc:
                        exc.graph = graph
                        exc.completed = dict(completed)
                        raise exc

            for node_id, output in await asyncio.gather(*(run_one(node) for node in ready)):
                completed[node_id] = output
                del pending[node_id]
        return {
            "nodes": completed,
            "provenance": [r.__dict__ for r in self.provenance.list_for_task(envelope.task_id)],
        }

    async def execute_node(
        self, envelope: TaskEnvelope, node: TaskNode, completed: dict[str, Any]
    ) -> Any:
        registered = self.registry.get(node.capability)
        card = registered.card
        self.policy_engine.check(envelope, card, self.registry, node=node)
        await self.emit(
            envelope, "tool.started", {"node_id": node.id, "capability_id": card.capability_id}
        )
        input_value = dict(node.input)
        if completed:
            input_value["previous_results"] = dict(completed)

        # T2.4 Timeout settings
        timeout_s = (
            envelope.constraints.node_timeout_ms or envelope.constraints.latency_ms or 30_000
        ) / 1000.0

        if not inspect.iscoroutinefunction(registered.handler):
            loop = asyncio.get_event_loop()
            coro = loop.run_in_executor(None, registered.handler, input_value, envelope)
        else:
            coro = registered.handler(input_value, envelope)

        try:
            raw = await asyncio.wait_for(coro, timeout=timeout_s)
        except asyncio.TimeoutError:
            raise UAPError(
                code="CAPABILITY_TIMEOUT",
                message=f"Capability {card.capability_id} timed out after {timeout_s}s",
                recoverable=True,
                safe_retry=True,
                retry_after_ms=int(timeout_s * 2000),
            )

        compact = self.context_manager.compact(
            raw,
            envelope.context_request,
            envelope.constraints.max_context_tokens,
        )
        rec = self.provenance.record(envelope, card.capability_id, input_value, compact)
        await self.emit(
            envelope,
            "tool.completed",
            {"node_id": node.id, "capability_id": card.capability_id, "provenance": rec.__dict__},
        )
        await self.emit(envelope, "partial.result", {"node_id": node.id, "result": compact})
        return compact

    async def emit(self, envelope: TaskEnvelope, event_type: str, data: dict[str, Any]) -> None:
        await self.event_bus.publish(
            UAPEvent(
                type=event_type,
                task_id=envelope.task_id,
                data=data,
                trace_id=str(envelope.metadata.get("trace_id")),
            )
        )

    async def resume_after_approval(self, task_id: str, approver_id: str) -> dict[str, Any]:
        if task_id not in self._pending:
            raise UAPError(
                code="TASK_NOT_FOUND",
                message=f"No pending approval for task {task_id}",
                recoverable=False,
                safe_retry=False,
            )
        p = self._pending.pop(task_id)
        envelope, graph, completed = p["envelope"], p["graph"], p["completed"]
        cap_id = p["capability_id"]

        self.policy_engine.grant_approval(task_id, cap_id)
        await self.emit(
            envelope,
            "approval.granted",
            {
                "approver_id": approver_id,
                "capability_id": cap_id,
            },
        )
        try:
            result = await self.execute_graph(envelope, graph, completed_so_far=completed)
            self.tasks[task_id] = {"status": "completed", "result": result}
            await self.emit(envelope, "task.completed", {"result": result})
            return {"task_id": task_id, "status": "completed", "result": result}
        except ApprovalRequiredError as exc:
            self.tasks[task_id] = {"status": "waiting_for_approval", "error": exc.to_dict()}
            self._pending[task_id] = {
                "envelope": envelope,
                "graph": exc.graph,
                "completed": exc.completed,
                "capability_id": exc.details.get("capability_id"),
            }
            await self.emit(envelope, "approval.requested", exc.to_dict())
            return {"task_id": task_id, "status": "waiting_for_approval", "error": exc.to_dict()}
        except UAPError as exc:
            if exc.code == "TASK_CANCELLED":
                self.tasks[task_id] = {"status": "cancelled", "error": exc.to_dict()}
                await self.emit(envelope, "task.cancelled", exc.to_dict())
                return {"task_id": task_id, "status": "cancelled", "error": exc.to_dict()}
            else:
                self.tasks[task_id] = {"status": "failed", "error": exc.to_dict()}
                event_type = "error.recoverable" if exc.recoverable else "error.terminal"
                await self.emit(envelope, event_type, exc.to_dict())
                await self.emit(envelope, "task.failed", exc.to_dict())
                return {"task_id": task_id, "status": "failed", "error": exc.to_dict()}
        except Exception as exc:
            error = UAPError(
                code="UNHANDLED_ERROR", message=str(exc), recoverable=False, safe_retry=False
            )
            self.tasks[task_id] = {"status": "failed", "error": error.to_dict()}
            await self.emit(envelope, "error.terminal", error.to_dict())
            await self.emit(envelope, "task.failed", error.to_dict())
            return {"task_id": task_id, "status": "failed", "error": error.to_dict()}
        finally:
            self.policy_engine.revoke_approvals(task_id)

    def cancel(self, task_id: str) -> bool:
        if task_id not in self._cancel:
            return False
        self._cancel[task_id].set()
        if task_id in self._pending:
            p = self._pending.pop(task_id)
            envelope = p["envelope"]
            self.tasks[task_id] = {
                "status": "cancelled",
                "error": {
                    "code": "TASK_CANCELLED",
                    "message": "Task cancelled by client",
                    "recoverable": False,
                    "safe_retry": False,
                },
            }
            asyncio.create_task(
                self.emit(
                    envelope,
                    "task.cancelled",
                    {
                        "code": "TASK_CANCELLED",
                        "message": "Task cancelled by client",
                        "recoverable": False,
                        "safe_retry": False,
                    },
                )
            )
        return True
