# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-alpha] - 2026-06-20

Initial alpha release of the Unified Agent Protocol (UAP) Reference Implementation.

### Added
- **Core Runtime**: Compliant task envelope parsing, execution mapping, and lifecycle state transitions.
- **DAG Execution**: Upfront cycle detection and dependency resolution, enabling secure concurrent node processing.
- **Policy Engine**: Enforcement rules evaluating allowed tools, denied tools, risk level, actor scopes, and approval gates.
- **Context Compaction**: Automated field masking, max list item truncation with count indicators, and token budgeting.
- **Provenance Store**: Cryptographic audit records generated for each capability invocation via SHA-256 digests.
- **Event Bus & SSE Stream**: Real-time event streaming including SSE event IDs, Last-Event-ID reconnect, and standard lifecycle mapping.
- **Five Standard Adapters**:
  - **MCP (Model Context Protocol)**: Bridges MCP servers with UAP policies.
  - **OpenAPI**: Parses REST OpenAPI endpoints into governance capability cards.
  - **A2A (Agent-to-Agent)**: Treats remote agents as capability nodes.
  - **AG-UI**: Projects task lifecycle events into AG-UI event schemas.
  - **CloudEvents**: Standardizes UAP event logging into CloudEvents 1.0 format.
