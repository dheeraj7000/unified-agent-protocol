from __future__ import annotations

from typing import Any, Dict

from ..models import UAPEvent


def uap_event_to_agui(event: UAPEvent) -> Dict[str, Any]:
    """Map UAP lifecycle events to a generic AG-UI-style event envelope."""

    mapping = {
        "task.accepted": "RUN_STARTED",
        "partial.result": "TEXT_MESSAGE_CONTENT",
        "approval.requested": "USER_INPUT_REQUESTED",
        "task.completed": "RUN_FINISHED",
        "task.failed": "RUN_ERROR",
    }
    return {
        "type": mapping.get(event.type, "CUSTOM"),
        "runId": event.task_id,
        "timestamp": event.time,
        "payload": event.to_dict(),
    }
