from __future__ import annotations

from typing import Any

from ..models import CapabilityCard


def a2a_agent_card_to_capability(agent_card: dict[str, Any]) -> CapabilityCard:
    """Represent a remote A2A-capable agent as a delegate capability."""

    agent_id = agent_card.get("id") or agent_card.get("name") or "remote_agent"
    description = agent_card.get("description") or f"Delegate work to {agent_id}"
    return CapabilityCard(
        capability_id=f"agent.delegate.{agent_id}",
        purpose=description,
        description=description,
        input_schema={"type": "object", "properties": {"task": {"type": "string"}}},
        output_schema={"type": "object"},
        risk=agent_card.get("risk", "medium"),
        permissions=[f"agent.delegate.{agent_id}"],
        idempotent=False,
        tags=["a2a", "delegate"],
        transport={"type": "a2a", "endpoint": agent_card.get("endpoint")},
    )
