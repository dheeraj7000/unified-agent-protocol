from __future__ import annotations

from .capabilities import CapabilityRegistry
from .models import TaskEnvelope, TaskGraph, TaskNode


class SimplePlanner:
    """Naive planner that picks capabilities by search terms.

    This is intentionally conservative. Production planners should use typed plans,
    rules, learned rankers, or explicit application workflows.
    """

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def plan(self, envelope: TaskEnvelope) -> TaskGraph:
        allowed = envelope.policy.allowed_tools or None
        candidates = self.registry.search(envelope.intent.goal, allowed=allowed)
        if not candidates and allowed:
            candidates = [self.registry.get(cid).card for cid in allowed]
        nodes: list[TaskNode] = []
        for index, card in enumerate(candidates):
            nodes.append(
                TaskNode(
                    id=f"n{index + 1}",
                    capability=card.capability_id,
                    input=dict(envelope.intent.parameters),
                    depends_on=[] if index == 0 else [nodes[-1].id],
                    requires_approval=card.requires_approval,
                )
            )
        return TaskGraph(nodes=nodes)
