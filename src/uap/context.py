from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping

from .models import ContextRequest


class ContextManager:
    """Applies field masks, item limits, and approximate token budgets."""

    def compact(self, result: Any, request: ContextRequest, max_context_tokens: int) -> Any:
        value = self._field_mask(result, request.fields)
        value = self._limit_items(value, request.max_items)
        budget = request.max_tokens or max_context_tokens
        return self._limit_tokens(value, budget)

    def _field_mask(self, value: Any, fields: List[str]) -> Any:
        if not fields:
            return value
        if isinstance(value, list):
            return [self._field_mask(item, fields) for item in value]
        if isinstance(value, Mapping):
            return {key: val for key, val in value.items() if key in fields or key.startswith("_")}
        return value

    def _limit_items(self, value: Any, max_items: int) -> Any:
        if isinstance(value, list):
            trimmed = value[:max_items]
            if len(value) > max_items:
                return trimmed + [{"_truncated": True, "remaining_items": len(value) - max_items}]
            return trimmed
        if isinstance(value, Mapping):
            return {key: self._limit_items(val, max_items) for key, val in value.items()}
        return value

    def _limit_tokens(self, value: Any, max_tokens: int) -> Any:
        # Approximation: one token ~= four characters. This is intentionally
        # conservative and dependency-free for the reference implementation.
        max_chars = max_tokens * 4
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if len(text) <= max_chars:
            return value
        return {
            "summary": text[: max_chars - 80],
            "_truncated": True,
            "original_chars": len(text),
            "budget_tokens": max_tokens,
        }
