from __future__ import annotations

from typing import Any

from ..models import UAPEvent


def uap_event_to_cloudevent(event: UAPEvent) -> dict[str, Any]:
    """Map a UAP lifecycle event to a standard CloudEvents 1.0 JSON envelope."""

    return {
        "specversion": "1.0",
        "id": event.event_id,
        "source": f"/uap/tasks/{event.task_id}",
        "type": f"dev.uap.event.{event.type}",
        "time": event.time,
        "datacontenttype": "application/json",
        "data": event.data,
        "traceid": event.trace_id,
    }
