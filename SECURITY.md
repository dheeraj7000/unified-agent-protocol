# Security Policy

## Reporting a Vulnerability

We take the security of UAP seriously. If you find a security issue, please report it via GitHub Security Advisories. Alternatively, you can email the maintainers directly.

Please do not report security vulnerabilities via public GitHub issues.

## Response SLA

- **Acknowledgment**: We aim to acknowledge receipt of reports within 72 hours.
- **Triage**: A detailed assessment and status update will be provided within 7 days.

## In-Scope Threats

We are interested in vulnerability reports concerning:
- **Prompt Injection**: Overriding task directives to execute arbitrary code or bypass controls.
- **Capability Escalation**: Executing capabilities that the actor's scopes do not permit.
- **Data Leakage**: Information disclosure through incorrect or missing field masking/filtering.
- **Replay of Approval Tokens**: Using stale or intercepted approval overrides to execute unauthorized tasks.

## Out-of-Scope Threats

The following are out of scope for this reference implementation:
- Distributed Denial of Service (DDoS) attacks.
- Attacks requiring physical access to the server/host machine.
