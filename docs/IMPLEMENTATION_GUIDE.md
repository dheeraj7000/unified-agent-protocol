# UAP Implementation Guide

## Recommended Architecture

```text
Client / Agent / UI
        |
        v
UAP Gateway or Runtime
        |
        +-- Envelope Validator (validation.py)
        +-- Capability Registry (runtime.py)
        +-- Policy Engine (policy.py)
        +-- Context Manager (context.py)
        +-- Task Planner & Executor (planner.py, runtime.py)
        +-- Event Bus (events.py)
        +-- Provenance Store (provenance.py)
        |
        +-- Adapters (adapters/):
            +-- MCP Adapter
            +-- A2A Adapter
            +-- AG-UI Adapter
            +-- OpenAPI Adapter
            +-- CloudEvents Adapter
```

---

## Core Components Implementation

### Step 1: Define & Register Capabilities

Start with capability cards. Do not expose raw endpoints directly to agents.
A capability card (defined in [models.py](file:///root/uap-reference/src/uap/models.py)) should describe:
- `capability_id`: Unique identifier (e.g. `invoice.list_overdue`).
- `purpose` & `description`: Purpose of the capability.
- `input_schema` & `output_schema`: JSON schemas for parameters and output validation.
- `risk`: Level of risk (`"low"`, `"medium"`, `"high"`, `"critical"`).
- `permissions`: Scopes required to execute this tool.
- `requires_approval`: Boolean gate for human authorization.
- `tags`: List of categories for search and alternative suggestion.

### Step 2: Wrap Existing Systems (Adapters)

Use standard adapters under `uap.adapters` to map legacy tools to UAP:
- **OpenAPI**: Maps standard OpenAPI 3.x specifications to capability cards, resolving internal schema references (`$ref`), query/path parameters, and custom `x-uap` extensions.
- **MCP**: Maps Model Context Protocol tools directly to capability cards.
- **CloudEvents**: Converts streamed lifecycle events into standard CloudEvents 1.0 JSON format for external message brokers.

### Step 3: Add Envelope Validation

Before any task execution, parse and validate the JSON payload using [validation.py](file:///root/uap-reference/src/uap/validation.py). The validation logic must verify:
- Presence of all required top-level envelope fields.
- Correct datatypes for `actor`, `intent`, `constraints`, `context_request`, `policy`, `execution`, and `return`.
- Syntactic correctness and node structure of optional execution graphs (if client-supplied).

### Step 4: Policy Checking & Self-Healing

Before a capability executes, check:
- Actor token verification and scopes.
- Capability risk level against policy `max_risk`.
- Allowed/denied capability list.

If a check fails:
- Raise `PolicyDeniedError` (returns `TOOL_NOT_ALLOWED` or `RISK_EXCEEDS_POLICY`).
- Search the capability registry for alternative permitted capabilities sharing similar tags or domains.
- Populate `alternative_capabilities` to allow automated agent self-healing.

### Step 5: Execute Plans as DAGs

UAP supports executing task graphs as Directed Acyclic Graphs (DAGs) in two ways:
1. **Server-Optimized**: The runtime planner builds a DAG using registered capabilities to satisfy the user's intent.
2. **Client-Directed / Custom**: If the client supplies `execution.graph` in the envelope, the runtime bypasses the planner, respects the specified dependency structure, runs independent nodes in parallel up to `execution.parallelism`, and enforces policy, context, and provenance checkpoints.

### Step 6: Add Context Budgeting

Each node output must pass through the `ContextManager` before return:
- Apply field masks (`context_request.fields`).
- Limit item count (`context_request.max_items`) and inject standard truncation metadata (`_truncated`, `remaining_items`).
- Compact token budget (`constraints.max_context_tokens`) by generating summaries when budgets are tight.

### Step 7: Emit Events & Log Provenance

- **Events**: Stream lifecycle changes (`task.accepted` → `plan.proposed` → `tool.started` → `tool.completed` → `task.completed`).
- **Provenance**: Record input/output SHA-256 digests, actor identifier, timestamp, and a trace ID for compliance auditing.

---

## Verification & Integration Testing

Use the reference integration test suite to verify implementation updates:
```bash
PYTHONPATH=src python examples/integration_test.py
```
This suite verifies:
1. Deep envelope validation
2. Policy enforcement and alternative matching
3. Parallel DAG execution and latency checks
4. Context contract field masking and item truncation
5. Event streaming and CloudEvents / AG-UI conversion
6. OpenAPI/MCP adapter importing
7. Structured error recovery
