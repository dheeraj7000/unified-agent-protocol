# UAP Specification v0.1 - Provenance

A UAP runtime MUST record a cryptographic audit trail (provenance) of capability invocations.
Each `ProvenanceRecord` MUST contain:
- `task_id` (string): The task identifier.
- `capability_id` (string): The capability identifier.
- `actor_id` (string): The calling actor's identifier.
- `input_digest` (string): The SHA-256 hash of the JSON-serialized input parameters.
- `output_digest` (string): The SHA-256 hash of the JSON-serialized output values.
- `trace_id` (string): Trace correlation ID.
- `time` (string, ISO 8601 format): Timestamp when recorded.
- `metadata` (object): Optional additional audit data.
