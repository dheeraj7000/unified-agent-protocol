from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Iterable, List, Optional

from .errors import CapabilityNotFoundError
from .models import CapabilityCard, RegisteredCapability


class CapabilityRegistry:
    """In-memory capability registry.

    Production implementations should back this with a durable registry, schema registry,
    trust store, and automated validation pipeline.
    """

    def __init__(self) -> None:
        self._items: Dict[str, RegisteredCapability] = {}

    def register(self, card: CapabilityCard, handler: Callable[..., Any]) -> None:
        if card.capability_id in self._items:
            raise ValueError(f"capability already registered: {card.capability_id}")
        self._items[card.capability_id] = RegisteredCapability(card=card, handler=handler)

    def get(self, capability_id: str) -> RegisteredCapability:
        try:
            return self._items[capability_id]
        except KeyError as exc:
            raise CapabilityNotFoundError(
                code="CAPABILITY_NOT_FOUND",
                message=f"No capability registered with id {capability_id}",
                recoverable=True,
                safe_retry=False,
                details={"capability_id": capability_id},
            ) from exc

    def list_cards(self) -> List[CapabilityCard]:
        return [item.card for item in self._items.values()]

    def search(self, query: str, allowed: Optional[Iterable[str]] = None) -> List[CapabilityCard]:
        allowed_set = set(allowed or [])
        terms = {t.lower() for t in query.split() if t.strip()}
        cards: List[CapabilityCard] = []
        for item in self._items.values():
            card = item.card
            if allowed_set and card.capability_id not in allowed_set:
                continue
            haystack = " ".join(
                [card.capability_id, card.purpose, card.description, " ".join(card.tags)] + card.examples
            ).lower()
            if not terms or any(term in haystack for term in terms):
                cards.append(card)
        return cards

    def from_function(
        self,
        capability_id: str,
        purpose: str,
        risk: str = "low",
        permissions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        """Decorator to register a Python function as a capability."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            signature = inspect.signature(func)
            properties = {
                name: {"type": "string"} for name in signature.parameters.keys() if name != "envelope"
            }
            card = CapabilityCard(
                capability_id=capability_id,
                purpose=purpose,
                input_schema={"type": "object", "properties": properties},
                output_schema={"type": "object"},
                risk=risk,
                permissions=permissions or [],
                tags=tags or [],
            )
            self.register(card, func)
            return func

        return decorator
