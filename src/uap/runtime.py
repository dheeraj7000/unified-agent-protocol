from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict, List, Optional, Set

from .capabilities import CapabilityRegistry
from .context import ContextManager
from .errors import ApprovalRequiredError, UAPError, ValidationError
from .events import EventBus
from .models import TaskEnvelope, TaskGraph, TaskNode, UAPEvent, new_id
from .planner import SimplePlanner
from .policy import PolicyEngine
from .provenance import ProvenanceStore
from .validation import validate_envelope_minimal


class UAPRuntime:
    """Reference UAP runtime.

    The runtime accepts UAP task envelopes, plans capability calls, checks policy,
    executes capabilities, compacts results, emits events, and records provenance.
    """

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        context_manager: Optional[ContextManager] = None,
        event_bus: Optional[EventBus] = None,
        provenance: Optional[ProvenanceStore] = None,
    ) -> None:
        self.registry = registry or CapabilityRegistry()
        self.policy_engine = policy_engine or PolicyEngine()
        self.context_manager = context_manager or ContextManager()
        self.event_bus = event_bus or EventBus()
        self.provenance = provenance or ProvenanceStore()
        self.planner = SimplePlanner(self.registry)
        self.tasks: Dict[str, Dict[str, Any]] = {}

    async def invoke(self, envelope_or_dict: TaskEnvelope | Dict[str, Any], graph: Optional[TaskGraph] = None) -> Dict[str, Any]:
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
                trace_id = str(envelope_or_dict.get("metadata", {}).get("trace_id") or new_id("trc"))
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
        envelope.metadata.setdefault("trace_id", new_id("trc"))
        self.tasks[envelope.task_id] = {"status": "accepted", "result": None}
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
        await self.emit(envelope, "plan.proposed", {"graph": [node.__dict__ for node in graph.nodes]})
        try:
            result = await self.execute_graph(envelope, graph)
            self.tasks[envelope.task_id] = {"status": "completed", "result": result}
            await self.emit(envelope, "task.completed", {"result": result})
            return {"task_id": envelope.task_id, "status": "completed", "result": result}
        except ApprovalRequiredError as exc:
            self.tasks[envelope.task_id] = {"status": "waiting_for_approval", "error": exc.to_dict()}
            await self.emit(envelope, "approval.requested", exc.to_dict())
            return {"task_id": envelope.task_id, "status": "waiting_for_approval", "error": exc.to_dict()}
        except UAPError as exc:
            self.tasks[envelope.task_id] = {"status": "failed", "error": exc.to_dict()}
            event_type = "error.recoverable" if exc.recoverable else "error.terminal"
            await self.emit(envelope, event_type, exc.to_dict())
            await self.emit(envelope, "task.failed", exc.to_dict())
            return {"task_id": envelope.task_id, "status": "failed", "error": exc.to_dict()}
        except Exception as exc:  # pragma: no cover - safety net
            error = UAPError(code="UNHANDLED_ERROR", message=str(exc), recoverable=False, safe_retry=False)
            self.tasks[envelope.task_id] = {"status": "failed", "error": error.to_dict()}
            await self.emit(envelope, "error.terminal", error.to_dict())
            await self.emit(envelope, "task.failed", error.to_dict())
            return {"task_id": envelope.task_id, "status": "failed", "error": error.to_dict()}

    async def execute_graph(self, envelope: TaskEnvelope, graph: TaskGraph) -> Dict[str, Any]:
        completed: Dict[str, Any] = {}
        pending: Dict[str, TaskNode] = {node.id: node for node in graph.nodes}
        if not pending:
            return {"message": "No matching capability found", "artifacts": []}

        while pending:
            ready = [node for node in pending.values() if all(dep in completed for dep in node.depends_on)]
            if not ready:
                raise UAPError(
                    code="PLAN_CYCLE_OR_MISSING_DEPENDENCY",
                    message="Task graph has a cycle or unresolved dependency",
                    recoverable=False,
                    safe_retry=False,
                )
            sem = asyncio.Semaphore(max(1, envelope.execution.parallelism))

            async def run_one(node: TaskNode):
                async with sem:
                    return node.id, await self.execute_node(envelope, node, completed)

            for node_id, output in await asyncio.gather(*(run_one(node) for node in ready)):
                completed[node_id] = output
                del pending[node_id]
        return {"nodes": completed, "provenance": [r.__dict__ for r in self.provenance.list_for_task(envelope.task_id)]}

    async def execute_node(self, envelope: TaskEnvelope, node: TaskNode, completed: Dict[str, Any]) -> Any:
        registered = self.registry.get(node.capability)
        card = registered.card
        self.policy_engine.check(envelope, card, self.registry)
        await self.emit(envelope, "tool.started", {"node_id": node.id, "capability_id": card.capability_id})
        input_value = dict(node.input)
        if completed:
            input_value["previous_results"] = completed
        raw = registered.handler(input_value, envelope)
        if inspect.isawaitable(raw):
            raw = await raw
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

    async def emit(self, envelope: TaskEnvelope, event_type: str, data: Dict[str, Any]) -> None:
        await self.event_bus.publish(
            UAPEvent(
                type=event_type,
                task_id=envelope.task_id,
                data=data,
                trace_id=str(envelope.metadata.get("trace_id")),
            )
        )
