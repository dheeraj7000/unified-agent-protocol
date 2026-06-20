# UAP Specification v0.1 - SSE Transport

For real-time observability, UAP provides an SSE binding:

1. **GET `/uap/tasks/{task_id}/events`**:
   - Establishes a server-sent events connection for the task.
   - Headers: Clients MAY send the standard `Last-Event-ID` header.
   - Reconnection: If `Last-Event-ID` is set, the server MUST skip events up to and including the specified ID from history, and yield only subsequent events.
   - Format: The server MUST prefix every event with an `id: {event_id}\n` line.

Example Event:
```text
id: evt_1234
event: task.accepted
data: {"goal": "hello"}
```
