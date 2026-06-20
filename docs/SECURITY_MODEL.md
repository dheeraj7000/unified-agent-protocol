# UAP Security Model

## Threats

UAP systems must defend against:

- prompt injection through tool results;
- tool poisoning through malicious tool descriptions;
- confused-deputy attacks;
- overbroad bearer tokens;
- cross-tenant data leakage;
- unapproved side effects;
- unsafe autonomous loops;
- provenance tampering;
- replay attacks.

## Required controls

### Least privilege capabilities

Agents should receive scoped capability tokens, not broad API credentials.

### Delegation chain

Every task should preserve the chain:

```text
user -> agent -> UAP runtime -> capability -> backend system
```

### Side-effect gates

Capabilities that send email, charge money, modify records, delete data, or contact external parties should require explicit policy approval or human approval.

### Context minimization

Return only the minimum data needed for the task. Avoid returning entire documents or database rows when excerpts, field masks, or summaries are enough.

### Tool metadata validation

Do not trust tool descriptions from untrusted servers. Validate schemas, risk labels, and permission declarations before adding capabilities to the registry.

### Provenance integrity

Persist provenance separately from model-visible context. Use append-only logs or signed records in high-security environments.

### Structured safe retries

Only retry operations marked idempotent or `safe_retry=true`.

---

## Risk levels

- `low`: read-only, public or non-sensitive data.
- `medium`: read sensitive data or create drafts.
- `high`: modify records, notify humans, or expose PII.
- `critical`: payments, deletion, legal/medical/financial commitments, security changes.

---

## Security Enhancements & Self-Healing Policy

### Automated Policy Recovery (Self-Healing)
When the policy engine blocks a capability call due to `allowed_tools` restrictions (`TOOL_NOT_ALLOWED`) or risk limits (`RISK_EXCEEDS_POLICY`), it queries the capability registry for alternative permitted tools matching the blocked capability's tags or domains. It returns these alternatives in the error object under the `alternative_capabilities` array, allowing agents to fallback or adjust strategies dynamically.

### Least-Privilege Verification
The calling actor specifies scopes under `actor.scopes`. The runtime and downstream backends verify that these scopes cover the permissions required by target capabilities before starting execution.

### OWASP Agentic Top 10 Alignment

UAP's control plane primitives map directly to mitigation strategies for the emerging OWASP Agentic Top 10 vulnerabilities:

- **AA-01 (Agent-to-Agent/Double-Agency Threat)**: Prevented via actor identity token mapping and scope constraints propagated down the execution chain.
- **AA-02 (Overbroad Scoping & Privilege Escalation)**: Checked at the runtime level. Capability cards dictate exact scopes, and policy limits are validated before executing each node.
- **AA-03 (Indirect Prompt Injection)**: Context budgeting, field masks, and item limits strip malicious prompt payloads from raw outputs before returning them to the LLM context.
- **AA-04 (Approval Bypass / Unintended Actions)**: Enforced via first-class `requires_approval` policy parameters, interrupting execution until human or system confirmation is received.
- **AA-05 (System Poisoning & Registry Hijacking)**: Handled by schema structure validation in the capability registry, ensuring no malformed or unverified capability specifications are registered.
