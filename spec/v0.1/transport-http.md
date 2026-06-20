# UAP Specification v0.1 - HTTP Transport

UAP HTTP bindings define the following standard endpoints:

1. **POST `/uap/tasks`**:
   - Submits a task envelope.
   - Response: Returns a status dictionary (e.g. `{"task_id": "...", "status": "completed|failed|waiting_for_approval", ...}`).
   - Normative: This endpoint MUST return HTTP 200 even if the task status is `failed`. The HTTP status code reflects transport-level delivery, not the task execution outcome.

2. **GET `/uap/tasks/{task_id}`**:
   - Retrieves the current task state.
   - Response: Returns `{"status": "accepted|running|waiting_for_approval|completed|failed|cancelled", ...}`. Returns HTTP 404 if the task ID is unknown.

3. **POST `/uap/tasks/{task_id}/approve`**:
   - Submits an approval grant for a waiting task.
   - Body: `{"approver_id": "..."}`.
   - Response: Returns HTTP 200 with the task state, or HTTP 404/400 on error.

4. **DELETE `/uap/tasks/{task_id}`**:
   - Requests cancellation of the task.
   - Response: Returns HTTP 200 on success, or HTTP 404 if the task is not found.

5. **GET `/uap/capabilities`**:
   - Lists registered capability cards.
   - Response: Returns `{"capabilities": [...]}`.

6. **GET `/uap/version`**:
   - Returns version information: `{"protocol": "uap", "version": "0.1", "supported_versions": ["0.1", "1.0"], "features": [...]}`.
