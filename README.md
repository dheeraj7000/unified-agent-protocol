# Unified Agent Protocol (UAP)

[![CI](https://github.com/dheeraj7000/unified-agent-protocol/actions/workflows/test.yml/badge.svg)](https://github.com/dheeraj7000/unified-agent-protocol/actions/workflows/test.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)
![Version 0.1.0-alpha](https://img.shields.io/badge/version-0.1.0--alpha-orange.svg)

*UAP is not a replacement for MCP, A2A, or AG-UI — it governs and coordinates them. It adds policy enforcement, context budgeting, provenance, and a typed task lifecycle to whatever agent infrastructure you already have.*

### How UAP Relates to Other Protocols

| Protocol / Framework | UAP Relationship |
| :--- | :--- |
| **MCP (Model Context Protocol)** | UAP wraps MCP tools with policy, context budgets, and provenance. |
| **A2A (Agent-to-Agent)** | UAP treats remote A2A agents as delegated capability nodes. |
| **AG-UI (Agent UI)** | UAP lifecycle events project into AG-UI event streams. |
| **LangGraph / CrewAI** | UAP can govern graph execution as a policy control plane. |
| **OpenAPI** | UAP converts OpenAPI operations into policy-aware capability cards. |
| **OpenTelemetry** | UAP provenance records integrate with OTel trace/span systems. |

### Architecture Flow

```text
POST envelope → validate → plan DAG → [policy check → execute] × N → compact → record provenance → emit events → return result
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Agent / Framework                        │
│              (LangGraph, CrewAI, MAF, ADK, custom)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────────┐
              │   Unified Agent Protocol    │
              │                             │
              │  Intent → Plan → Execute    │
              │  Policy → Budget → Prove    │
              └──┬──────┬──────┬──────┬─────┘
                 │      │      │      │
              ┌──▼──┐┌──▼──┐┌─▼──┐┌──▼───┐
              │ MCP ││ A2A ││REST││Kafka  │
              │Tools││Agent││gRPC││Events │
              └─────┘└─────┘└────┘└──────┘
```

**Kubernetes orchestrates containers. Envoy manages service mesh traffic. UAP coordinates AI agents.**

UAP is an open, AI-native control-plane protocol that sits above existing protocols — MCP, A2A, AG-UI, REST/OpenAPI, gRPC, GraphQL, Kafka, and WebSockets — and adds the missing coordination layer: **task lifecycle, capability selection, context budgeting, policy enforcement, identity delegation, provenance tracking, structured error recovery, and observable streaming events.**

Existing protocols continue to own transport and domain logic. UAP coordinates all of them under one production-grade contract.


---

## Why a Control Plane?

AI agents in production don't just call one API. They reason, discover tools, call multiple backends, delegate work to other agents, stream results to UIs, and mutate real-world state — all autonomously.

**Without a control plane, you get:**

| Problem | What Happens |
|---------|-------------|
| **Serial tool loops** | 10-step workflows take seconds instead of milliseconds. |
| **Context bloat** | LLMs drown in 50k+ tokens of tool definitions before a user even speaks. |
| **No governance** | Agents inherit broad permissions, traverse privilege graphs, and act unsafely. |
| **Invisible failures** | Errors cascade across multi-agent chains with no trace or recovery path. |
| **Audit black holes** | No one can explain what the agent did, why, or which data it touched. |

**With UAP as the control plane:**

| UAP Primitive | What It Does |
|--------------|-------------|
| **Intent** | Separates what the user wants from how it gets done. |
| **Task Graph** | Plans work as a DAG — parallel execution, dependency tracking, retries. |
| **Capability Cards** | Compact, typed, policy-aware descriptions replacing raw tool catalogs. |
| **Context Contract** | Token budgets, field masks, and item limits — models see only what matters. |
| **Policy Engine** | Risk labels, approval gates, scoped identity, least-privilege enforcement. |
| **Provenance** | Every output traced to its source capability, actor, and timestamp. |
| **Structured Errors** | Machine-readable recovery: retry hints, alternative tools, repair guidance. |
| **Event Stream** | Full task lifecycle observable via SSE, WebSocket, or CloudEvents. |

---

## Real-World Use Cases for AI Engineers & CTOs

If you are scaling agentic applications in production (using LangGraph, CrewAI, Autogen, or custom code), UAP addresses critical operational challenges:

### 1. The Secure Agent Gateway (Envoy for LLMs)
Avoid exposing raw API credentials or backend databases directly to autonomous agents. Route all tool calls through the UAP reference server as an API gateway:
* **Least-Privilege Verification:** Verify actor scopes (`actor.scopes`) against capability requirements before allowing tool execution.
* **Risk Envelopes:** Block calls if the tool's risk level exceeds the max allowed policy (e.g. `policy.max_risk = "medium"`).
* **Approval Gates:** Pause execution and trigger webhook/WebSocket interrupts for high-risk side effects (e.g., executing a credit card charge or deleting resources).

### 2. High-Performance DAG Execution (Bypassing LLM Loops)
Sequential tool calling is slow. Running 10 sequential tool calls takes 10+ seconds of round-trips to the LLM. 
* Under UAP, the planner or agent constructs a task DAG (`execution.graph`) defining dependencies.
* The UAP runtime executes independent branches concurrently in background thread pools, completing multi-step actions in milliseconds.

### 3. Context Window Preservaton & Cost Optimization
LLM context windows are expensive and suffer from quality degradation when bloated with raw JSON outputs.
* **Field Masking:** Filter fields on the wire so the LLM only receives what it requested (e.g., `fields = ["name", "status"]`).
* **Item Limits:** Set `max_items` to automatically truncate large tool responses, appending a standard `_truncated` marker.
* **Summarization:** When context limits are tight, UAP automatically summarizes tool outputs before returning them to the model context.

### 4. Enterprise Provenance & Audit Trails
For compliance, every tool execution generates a cryptographic record containing inputs, output digests, execution timestamps, actor context, and a trace ID.

---

## Programmatic Integration Example

Integrate UAP checks directly inside your Python backend:

```python
import asyncio
from uap import UAPRuntime, CapabilityCard

async def main():
    # 1. Initialize runtime
    runtime = UAPRuntime()

    # 2. Define capability cards and handlers
    def query_db(input_val, envelope):
        return [{"id": 1, "name": "Acme Corp", "secret_key": "xyz"}]

    runtime.registry.register(
        CapabilityCard(
            capability_id="db.query",
            purpose="Query customer database",
            input_schema={"type": "object"},
            output_schema={"type": "array"},
            risk="medium",
            permissions=["db.read"],
            tags=["crm", "read"]
        ),
        handler=query_db
    )

    # 3. Invoke UAP with validation, policy enforcement, and field masking
    envelope = {
        "uap": "1.0",
        "type": "task.invoke",
        "actor": {
            "agent_id": "did:web:finance-agent",
            "scopes": ["db.read"]
        },
        "intent": {
            "goal": "read database"
        },
        "context_request": {
            "fields": ["name"]  # Mask out secret_key
        },
        "policy": {
            "max_risk": "medium"
        },
        "execution": {
            "graph": {
                "nodes": [{"id": "n1", "capability": "db.query"}]
            }
        }
    }

    result = await runtime.invoke(envelope)
    
    # Verify field mask stripped 'secret_key' automatically
    print(result["result"]["nodes"]["n1"])
    # Output: [{'name': 'Acme Corp'}]

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Quick Start

Full specification: [spec/v0.1/index.md](file:///root/uap-reference/spec/v0.1/index.md)

### 1. Requirements & Setup
Python 3.10+. Zero external dependencies for the core library.

Install server dependencies:
```bash
pip install -e '.[server]'
```

### 2. Run the Gateway Server
Spin up the UAP reference server on `localhost:8000`:
```bash
PYTHONPATH=src python -m uap.server
```

### 3. Invoke a Task via HTTP (Curl)
Submit a task envelope to the running gateway to execute the demo workflow:
```bash
curl -X POST http://localhost:8000/uap/tasks \
  -H "Content-Type: application/json" \
  -d @examples/task_invoke.json
```

**Expected JSON Response (truncated):**
```json
{
  "task_id": "tsk_quickstart",
  "status": "completed",
  "result": {
    "nodes": {
      "n1": [
        {
          "invoice_id": "INV-1001",
          "customer": "Acme",
          "amount": 1200,
          "due_date": "2026-05-01"
        }
      ]
    },
    "provenance": [
      {
        "task_id": "tsk_quickstart",
        "capability_id": "invoice.list_overdue",
        "actor_id": "agent_quickstart",
        "input_digest": "44136fa355b3...",
        "output_digest": "c4a94c53f95b..."
      }
    ]
  }
}
```

The server will validate the envelope, execute the task graph in parallel, enforce the security policy, apply output field masking, and return the compacted results with provenance.

### 4. Run the Unit & Integration Tests
Ensure everything works correctly:
```bash
# Run unit tests
PYTHONPATH=src python -m unittest discover -s tests

# Run the 53-assertion end-to-end integration test suite
PYTHONPATH=src python examples/integration_test.py
```


---

## How It Works

### 1. Send a Task Envelope

A task envelope describes **what you want**, not how to do it:

```json
{
  "uap": "1.0",
  "type": "task.invoke",
  "task_id": "tsk_demo",
  "actor": {
    "agent_id": "did:web:agent.example",
    "user_id": "usr_123"
  },
  "intent": {
    "goal": "Find overdue invoices and draft reminder emails",
    "domain": "finance.operations"
  },
  "constraints": {
    "latency_ms": 5000,
    "max_cost_usd": 0.05,
    "max_context_tokens": 3000
  },
  "policy": {
    "requires_approval": ["email.send"],
    "allowed_tools": ["invoice.list_overdue", "email.draft"],
    "max_risk": "medium"
  }
}
```

### 2. The Runtime Coordinates Everything

```
Envelope received
    │
    ├─ Validate ──────── Deep schema + type checks on every field
    ├─ Plan ──────────── Build execution DAG from intent + capabilities
    ├─ Policy Check ──── Risk, permissions, approval gates per capability
    ├─ Execute Graph ─── Parallel nodes, dependency resolution, semaphores
    ├─ Compact Output ── Field masks, item limits, token budgets
    ├─ Record ────────── Provenance with input/output digests + trace IDs
    └─ Stream ────────── Events: accepted → planned → started → completed
```

### 3. Or Bring Your Own Execution Graph

Bypass the planner entirely by supplying a custom DAG in the envelope:

```json
{
  "execution": {
    "parallelism": 4,
    "graph": {
      "nodes": [
        { "id": "n1", "capability": "invoice.list_overdue" },
        { "id": "n2", "capability": "email.draft", "depends_on": ["n1"] }
      ]
    }
  }
}
```

---

## Adapter Ecosystem

UAP doesn't replace your existing infrastructure. It wraps it.

### OpenAPI Adapter
Converts any OpenAPI 3.x spec into UAP capability cards automatically:
- Parses parameters, request bodies, and response schemas.
- Supports `x-uap` vendor extensions for fine-grained risk/cost mapping.

### MCP Adapter
Maps Model Context Protocol tools directly to UAP capability cards, adding risk labels and enforcing policy before tool execution.

### A2A Adapter
Wraps remote A2A agent cards as delegated capability nodes. Cross-agent work becomes a node in the task graph with full policy and provenance coverage.

### AG-UI Adapter
Projects UAP lifecycle events into AG-UI format (`RUN_STARTED`, `USER_INPUT_REQUESTED`, `RUN_FINISHED`) for real-time frontend synchronization.

### CloudEvents Adapter
Formats UAP events as CloudEvents 1.0 JSON for publishing to Kafka, RabbitMQ, AWS EventBridge, or any standards-compliant broker.

---

## Policy & Security

The policy engine runs **before every capability invocation**, not once at the gateway:

```python
# Deny tools not in the allow-list
policy.allowed_tools = ["invoice.list_overdue", "email.draft"]

# Cap risk exposure
policy.max_risk = "medium"

# Require human approval for side effects
policy.requires_approval = ["email.send", "payment.process"]

# Scope permissions via actor identity
actor.scopes = ["invoice.read", "email.draft"]
```

When a capability is denied, the policy engine doesn't just fail — it searches the registry for **alternative capabilities** that are permitted and share similar tags, populating `alternative_capabilities` in the error response so agents can self-recover.

---

## Provenance & Observability

Every capability execution produces an immutable provenance record:

```json
{
  "task_id": "tsk_demo",
  "capability_id": "invoice.list_overdue",
  "actor_id": "did:web:agent.example",
  "input_digest": "44136fa355b3...",
  "output_digest": "c4a94c53f95b...",
  "trace_id": "trc_abc123",
  "time": "2026-06-19T19:36:23Z"
}
```

Every state change emits a structured event to the event bus:
`task.accepted` → `plan.proposed` → `tool.started` → `tool.completed` → `partial.result` → `task.completed`

---

## Server Mode Gateway API

Host the UAP runtime as an HTTP gateway:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | `GET` | Runtime health check |
| `/uap/capabilities` | `GET` | List registered capability cards |
| `/uap/tasks` | `POST` | Invoke a task (returns initial response or event stream) |
| `/uap/tasks/{id}` | `GET` | Inspect task execution status |
| `/uap/tasks/{id}/events` | `GET` | Stream task lifecycle events (SSE) |

---

## CLI

```bash
# Validate a task envelope
uap validate path/to/envelope.json

# Execute a task against the empty runtime
uap run-empty path/to/envelope.json
```

---

## Repository Layout

```
uap-reference/
  docs/               Protocol proposal and implementation guides
  schemas/            JSON Schema definitions for all message types
  src/uap/            Python reference runtime
    adapters/         MCP, A2A, AG-UI, OpenAPI, CloudEvents adapters
    runtime.py        Core execution engine
    policy.py         Policy enforcement engine
    context.py        Context compaction and budgeting
    provenance.py     Provenance record store
    events.py         Event bus
    planner.py        Capability-aware task planner
    validation.py     Deep envelope validation
    models.py         Protocol data models
  examples/           Runnable demos and sample payloads
  tests/              Unit and integration tests
```

---

## Design Principles

1. **Protocol, not framework.** UAP defines the wire format. Any runtime can implement it.
2. **Coordinate, don't replace.** MCP, A2A, REST, gRPC, Kafka — they all keep working. UAP adds the missing layer above.
3. **LLM-budget native.** Context windows are the fundamental constraint. Compaction, field masks, and token budgets are first-class protocol primitives.
4. **Policy before execution.** Every capability invocation passes through risk, permission, and approval checks.
5. **Everything is traceable.** Every action has a provenance record, trace ID, and audit trail.
6. **Errors are data.** Structured, machine-readable errors with retry safety, alternatives, and repair hints.

---

## License

Apache-2.0. See `LICENSE`.
