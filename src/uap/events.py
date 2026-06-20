from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncIterator, DefaultDict, Dict, List

from .models import UAPEvent


class EventBus:
    """In-memory async event bus."""

    def __init__(self) -> None:
        self._history: DefaultDict[str, List[UAPEvent]] = defaultdict(list)
        self._queues: DefaultDict[str, List[asyncio.Queue[UAPEvent]]] = defaultdict(list)

    async def publish(self, event: UAPEvent) -> None:
        self._history[event.task_id].append(event)
        for queue in list(self._queues[event.task_id]):
            await queue.put(event)

    def history(self, task_id: str) -> List[UAPEvent]:
        return list(self._history.get(task_id, []))

    async def subscribe(self, task_id: str) -> AsyncIterator[UAPEvent]:
        queue: asyncio.Queue[UAPEvent] = asyncio.Queue()
        self._queues[task_id].append(queue)
        try:
            for event in self.history(task_id):
                yield event
                if event.type in {"task.completed", "task.failed", "task.cancelled"}:
                    return
            while True:
                event = await queue.get()
                yield event
                if event.type in {"task.completed", "task.failed", "task.cancelled"}:
                    break
        finally:
            self._queues[task_id].remove(queue)
