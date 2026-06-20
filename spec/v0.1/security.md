# UAP Specification v0.1 - Security

UAP defines the following threat model and mitigations:

| Threat | Description | UAP Mitigation |
| :--- | :--- | :--- |
| **Prompt Injection** | Untrusted content overrides task directives | Policy engine evaluates and restricts allowed tools; context boundaries restrict leakage |
| **Capability Escalation** | Actor executes unauthorized capability | Permissions checking against the actor's scopes |
| **Confused Deputy** | Agent is tricked into performing actions | Strict validation of scopes; approval gates for sensitive actions |
| **Data Leakage** | Output details contain sensitive info | Field masking strips unrequested fields before returning them to client |
| **Replay Attack** | Stale approval token reused | Unique task IDs and single-use approval override state |
| **Event Spoofing** | Invalid event stream inputs | SSE endpoint authentication and read-only event bus history |
| **Provenance Tampering** | Tampering with invocation audit logs | Crypto digests (SHA-256) matching exact inputs and outputs |
