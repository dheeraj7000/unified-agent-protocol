# UAP Specification v0.1 - Index

## Overview
The Unified Agent Protocol (UAP) is a control-plane protocol for orchestrating, governing, and observing agentic workflows and tool executions.

## Conformance Language
The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

## Conformance Tiers
1. **CORE Conformance**: A compliant runtime MUST implement Envelope validation, Policy enforcement, and Event emission.
2. **FULL Conformance**: A compliant runtime MUST implement the CORE tier plus approval lifecycle, SSE streams, task cancellation, and version negotiation.

## Sitemap
- [Envelope Schema](envelope.md)
- [Capability Card Schema](capability-card.md)
- [Task Graph Schema](task-graph.md)
- [Policy Schema](policy.md)
- [Context Contract Schema](context-contract.md)
- [Provenance Schema](provenance.md)
- [Error Codes Specification](errors.md)
- [Lifecycle Events Specification](events.md)
- [Approval Lifecycle Specification](approval-lifecycle.md)
- [HTTP Transport Specification](transport-http.md)
- [SSE Transport Specification](transport-sse.md)
- [Security Threat Model](security.md)
- [Compatibility & Version Negotiation Specification](compatibility.md)
