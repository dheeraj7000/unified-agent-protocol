from __future__ import annotations

from typing import Any

from .errors import ApprovalRequiredError, PolicyDeniedError
from .models import CapabilityCard, TaskEnvelope, TaskNode

RISK_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class PolicyEngine:
    """Simple policy engine.

    Production systems should integrate policy-as-code, attribute-based access
    control, user consent, tenant isolation, and audited approval workflows.
    """

    def __init__(self, strict_scopes: bool = True) -> None:
        """Initialize PolicyEngine.

        Set strict_scopes=True in production to enforce permissions even when
        the actor presents an empty scope list.
        """
        self.strict_scopes = strict_scopes
        self._overrides: dict[str, set[str]] = {}

    def grant_approval(self, task_id: str, capability_id: str) -> None:
        self._overrides.setdefault(task_id, set()).add(capability_id)

    def revoke_approvals(self, task_id: str) -> None:
        self._overrides.pop(task_id, None)

    def check(
        self,
        envelope: TaskEnvelope,
        card: CapabilityCard,
        registry: Any | None = None,
        node: TaskNode | None = None,
    ) -> None:
        policy = envelope.policy
        if policy.allowed_tools and card.capability_id not in policy.allowed_tools:
            alternatives: list[str] = []
            if registry:
                # Suggest allowed tools that share similar tags or purposes
                for allowed_id in policy.allowed_tools:
                    try:
                        other_card = registry.get(allowed_id).card
                        if set(other_card.tags) & set(card.tags):
                            alternatives.append(allowed_id)
                    except Exception:
                        pass
            raise PolicyDeniedError(
                code="TOOL_NOT_ALLOWED",
                message=f"Capability {card.capability_id} is not in allowed_tools",
                recoverable=True,
                safe_retry=False,
                alternative_capabilities=alternatives,
                details={"capability_id": card.capability_id},
            )
        if card.capability_id in policy.denied_tools:
            raise PolicyDeniedError(
                code="TOOL_DENIED",
                message=f"Capability {card.capability_id} is explicitly denied",
                recoverable=False,
                safe_retry=False,
                details={"capability_id": card.capability_id},
            )
        if RISK_ORDER.get(card.risk, 99) > RISK_ORDER.get(policy.max_risk, 99):
            alternatives = []
            if registry:
                # Suggest other tools that have low risk and share similar tags
                for other_card in registry.list_cards():
                    if other_card.capability_id != card.capability_id:
                        if RISK_ORDER.get(other_card.risk, 99) <= RISK_ORDER.get(
                            policy.max_risk, 99
                        ):
                            if set(other_card.tags) & set(card.tags):
                                alternatives.append(other_card.capability_id)
            raise PolicyDeniedError(
                code="RISK_EXCEEDS_POLICY",
                message=f"Capability risk {card.risk} exceeds max_risk {policy.max_risk}",
                recoverable=True,
                safe_retry=False,
                alternative_capabilities=alternatives,
                details={"capability_id": card.capability_id, "risk": card.risk},
            )
        required = set(card.permissions)
        actor_scopes = set(envelope.actor.scopes)
        missing = sorted(required - actor_scopes)
        # In demo mode we allow empty scopes unless the envelope carries scopes.
        if (envelope.actor.scopes or self.strict_scopes) and missing:
            raise PolicyDeniedError(
                code="MISSING_PERMISSION",
                message="Actor lacks required capability permissions",
                recoverable=True,
                safe_retry=False,
                details={"missing_permissions": missing},
            )
        if (
            card.requires_approval
            or card.capability_id in policy.requires_approval
            or (node is not None and node.requires_approval)
        ):
            if card.capability_id in self._overrides.get(envelope.task_id, set()):
                return
            raise ApprovalRequiredError(
                code="APPROVAL_REQUIRED",
                message=f"Capability {card.capability_id} requires approval",
                recoverable=True,
                safe_retry=False,
                details={"capability_id": card.capability_id},
            )
