# UAP Specification v0.1 - Envelope

A compliant UAP runtime MUST validate every incoming task envelope according to the following normative rules:

1. The runtime MUST reject any envelope missing any of the core fields: `uap`, `type`, `task_id`, `actor`, or `intent`.
2. The runtime MUST reject the envelope if the `actor` field is present but does not contain an `agent_id`.
3. The `task_id` MUST be a unique identifier within the scope of the server instance.
4. The runtime MUST validate all nested properties against the JSON schemas in the `schemas/` directory.
5. Unknown fields at the top-level or inside sub-objects MUST be ignored but preserved in metadata for downstream processing.
