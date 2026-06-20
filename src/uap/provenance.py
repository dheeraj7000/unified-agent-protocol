from __future__ import annotations

import hashlib
import json
from typing import Any, List

from .models import ProvenanceRecord, TaskEnvelope, new_id


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ProvenanceStore:
    """Append-only in-memory provenance store."""

    def __init__(self) -> None:
        self._records: List[ProvenanceRecord] = []

    def record(self, envelope: TaskEnvelope, capability_id: str, input_value: Any, output_value: Any) -> ProvenanceRecord:
        rec = ProvenanceRecord(
            task_id=envelope.task_id,
            capability_id=capability_id,
            actor_id=envelope.actor.agent_id,
            input_digest=digest(input_value),
            output_digest=digest(output_value),
            trace_id=str(envelope.metadata.get("trace_id") or new_id("trc")),
        )
        self._records.append(rec)
        return rec

    def list_for_task(self, task_id: str) -> List[ProvenanceRecord]:
        return [r for r in self._records if r.task_id == task_id]
