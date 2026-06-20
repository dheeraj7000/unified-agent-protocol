# UAP Specification v0.1 - Approval Lifecycle

When a capability execution hits a policy check that requires approval:

1. The runtime MUST halt execution, emit `approval.requested` with details of the required approval, and set the task status to `waiting_for_approval`.
2. Resume MUST be triggered by a separate, authenticated client call indicating consent.
3. The runtime MUST emit `approval.granted` before resuming capability execution.
4. If approved, the task resumes from the blocked node and proceeds to completion (or next gate).
5. If denied, the task state transitions to `failed` and emits `task.failed`.
