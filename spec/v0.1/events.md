# UAP Specification v0.1 - Events

A UAP task emits lifecycle events to track progress. Compliant runtimes MUST follow these constraints:

1. **Ordering Constraints**:
   - `task.accepted` MUST be emitted before any capability node is evaluated (prior to `tool.started`).
   - For a given node, `tool.completed` (or a node failure event) MUST follow `tool.started`.
   - The final event emitted for a task MUST be one of `task.completed`, `task.failed`, or `task.cancelled`.

2. **Required Fields**:
   - All events MUST include `event_id` (string), `task_id` (string), `time` (ISO 8601 date-time string), and `uap` (string).
   - Events SHOULD include `trace_id` when correlation metadata is available.
