# Unified Agent Protocol (UAP) v1.0 Draft Specification
## The Control Plane for Agentic Applications

## Status

This is the reference draft specification for the Unified Agent Protocol (UAP). It is designed to serve as an open, AI-native control-plane standard for coordinating agentic workflows, policy enforcement, resource budgeting, and lifecycle management.

## Abstract

Unified Agent Protocol (UAP) is the control plane for agentic applications. Just as Kubernetes orchestrates containers and Envoy manages service mesh traffic, UAP coordinates AI agents — standardizing task lifecycle, capability selection, context budgeting, policy enforcement, identity delegation, provenance tracking, structured error recovery, and observable streaming events.

UAP does not replace transport protocols or domain-specific APIs (such as MCP, REST, OpenAPI, gRPC, and GraphQL). Instead, it acts as an orchestration and governance layer above them.

---

## 1. Task Envelope Schema

Every UAP interaction begins with a **Task Envelope** of type `task.invoke`.

### Core Envelope Structure

```json
{
  "uap": "1.0",
  "type": "task.invoke",
  "task_id": "tsk_12345",
  "actor": {
    "agent_id": "did:web:agent.example",
    "user_id": "usr_987",
    "org_id": "org_555",
    "service_id": "svc_billing",
    "delegation_token": "dpop-jwt-token-here",
    "scopes": ["invoice.read", "email.draft"]
  },
  "intent": {
    "goal": "Find overdue invoices and draft reminder emails",
    "domain": "finance.operations",
    "parameters": {
      "cutoff_date": "2026-06-01"
    }
  },
  "constraints": {
    "latency_ms": 5000,
    "max_cost_usd": 0.05,
    "max_context_tokens": 3000,
    "risk_level": "medium"
  },
  "context_request": {
    "detail": "minimal",
    "fields": ["invoice_id", "customer", "amount", "due", "status", "drafts"],
    "evidence_required": true,
    "max_items": 10,
    "max_tokens": 2000
  },
  "policy": {
    "requires_approval": ["email.send"],
    "data_classes": ["financial", "customer"],
    "allowed_tools": ["invoice.list_overdue", "email.draft"],
    "denied_tools": ["customer.delete"],
    "max_risk": "medium"
  },
  "execution": {
    "mode": "server_optimized",
    "parallelism": 4,
    "allow_partial_results": true,
    "graph": {
      "nodes": [
        {
          "id": "n1",
          "capability": "invoice.list_overdue",
          "input": {}
        },
        {
          "id": "n2",
          "capability": "email.draft",
          "depends_on": ["n1"],
          "input": {}
        }
      ]
    }
  },
  "return": {
    "stream": true,
    "format": "summary+artifacts"
  },
  "metadata": {}
}
```

### Field Definitions

#### `actor` (Required)
Defines the identities and scopes under which the task executes.
- `agent_id` (String, Required): The decentralized identifier or URI of the calling agent.
- `user_id` (String, Optional): The end-user identifier on whose behalf the agent is acting.
- `org_id` (String, Optional): The organization scope.
- `service_id` (String, Optional): An optional downstream service name.
- `delegation_token` (String, Optional): Token validating delegation authorization.
- `scopes` (List of Strings, Optional): List of specific capability scopes requested for this task.

#### `intent` (Required)
The target goal of the task.
- `goal` (String, Required): High-level description of what the agent should achieve.
- `domain` (String, Optional): The domain categorisation (e.g. `finance.operations`).
- `parameters` (Object, Optional): Flat JSON payload parameters passed to the capabilities.

#### `constraints` (Optional)
Resource and operational boundaries.
- `latency_ms` (Integer, Optional): Maximum latency allowed for execution.
- `max_cost_usd` (Float, Optional): Maximum financial budget for this invocation.
- `max_context_tokens` (Integer, Default: `4000`): Hard limit on tokens returned to the agent context.
- `risk_level` (String, Default: `"medium"`): Default maximum risk class allowed.

#### `context_request` (Optional)
Details on how outputs should be minimized/filtered.
- `detail` (String, Default: `"minimal"`): Visual or detail level (e.g., `"minimal"`, `"full"`).
- `fields` (List of Strings, Optional): Selection field masks to retain in output structures.
- `evidence_required` (Boolean, Default: `true`): True if citations and evidence are required.
- `max_items` (Integer, Default: `20`): Maximum list items to return.
- `max_tokens` (Integer, Optional): Token sub-budget for output values.

#### `policy` (Optional)
Security and compliance rules to evaluate before capability execution.
- `requires_approval` (List of Strings, Optional): Capabilities that must trigger an approval gate.
- `data_classes` (List of Strings, Optional): Allowed data classifications.
- `allowed_tools` (List of Strings, Optional): Allow-listed capability IDs.
- `denied_tools` (List of Strings, Optional): Block-listed capability IDs.
- `max_risk` (String, Default: `"high"`): Maximum permissible risk level (`"low"`, `"medium"`, `"high"`, `"critical"`).

#### `execution` (Optional)
Specifies execution parameters or directly supplies a task graph.
- `mode` (String, Default: `"server_optimized"`): Can be `"client_orchestrated"`, `"server_optimized"`, or `"hybrid"`.
- `parallelism` (Integer, Default: `5`): Maximum concurrent threads or workers.
- `allow_partial_results` (Boolean, Default: `true`): If nodes fail, execute non-dependent nodes.
- `graph` (Object, Optional): A custom DAG. If present, the runtime bypasses the planner.
  - `nodes` (List of Objects, Required): The nodes in the custom task graph:
    - `id` (String, Required): Unique ID for the node.
    - `capability` (String, Required): The ID of the capability card to execute.
    - `input` (Object, Optional): Explicit inputs to the capability.
    - `depends_on` (List of Strings, Optional): Dependency node IDs.
    - `requires_approval` (Boolean, Optional): If true, force human approval before execution.

#### `return` (Optional)
Format of response delivery.
- `stream` (Boolean, Default: `true`): True if lifecycle events should be streamed.
- `format` (String, Default: `"summary+artifacts"`): Desired return shape.

---

## 2. Capability Cards

Capabilities represent the tools, services, or agents available to execute tasks.

```json
{
  "capability_id": "invoice.list_overdue",
  "purpose": "Find invoices that are past their payment due dates",
  "input_schema": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer" }
    }
  },
  "output_schema": {
    "type": "array",
    "items": { "type": "object" }
  },
  "risk": "low",
  "permissions": ["invoice.read"],
  "description": "Scans CRM database for overdue records.",
  "idempotent": true,
  "requires_approval": false,
  "tags": ["invoice", "finance", "read"],
  "transport": {
    "type": "rest",
    "path": "/invoices/overdue",
    "method": "GET"
  }
}
```

---

## 3. Task Lifecycle & Events

UAP tasks follow a strict lifecycle, emitting standardized event payloads.

### Lifecycle States

```text
created -> accepted -> planning -> running -> waiting_for_approval -> completed
                                 \-> failed
                                 \-> cancelled
                                 \-> expired
```

### Standard Event Types

- `task.accepted`: The envelope passed syntax validation and is accepted.
- `plan.proposed`: An execution graph was successfully generated.
- `tool.started`: Execution of a specific capability node has started.
- `tool.completed`: A capability node successfully completed execution.
- `artifact.created`: An immutable result file/artifact was generated.
- `approval.requested`: A policy gate blocked execution awaiting human input.
- `partial.result`: Intermediate data streamed back to client.
- `error.recoverable`: A recoverable error occurred during execution.
- `error.terminal`: The task failed irreversibly.
- `task.completed`: Execution finished and final outputs are compacted.
- `task.cancelled`: Execution was cancelled by client request.

---

## 4. Error Requirements

Errors must be structured to support machine readability and automated recovery.

### Schema

```json
{
  "code": "TOOL_NOT_ALLOWED",
  "message": "Capability 'email.send' is not permitted under allowed_tools",
  "recoverable": true,
  "safe_retry": false,
  "retry_after_ms": 3000,
  "alternative_capabilities": ["email.draft"],
  "details": {
    "policy_violation": "allowed_tools",
    "requested_tool": "email.send"
  }
}
```

### Core Error Fields

- `code` (String, Required): Machine-readable identifier:
  - `INVALID_ENVELOPE`: Syntax or type error in task envelope.
  - `INVALID_ACTOR`: Actor identity fields are invalid.
  - `INVALID_INTENT`: Intent or goal missing.
  - `INVALID_CONSTRAINTS`: Invalid constraint parameters.
  - `INVALID_POLICY`: Invalid policy field definitions.
  - `INVALID_EXECUTION_GRAPH`: Cycle detected or node schema mismatch in graph.
  - `TOOL_NOT_ALLOWED`: Capability blocked by policy `allowed_tools` or `denied_tools`.
  - `RISK_EXCEEDS_POLICY`: Risk level exceeds `max_risk`.
  - `APPROVAL_REQUIRED`: Triggered gate awaiting human response.
  - `EXECUTION_FAILED`: Core backend tool execution failure.
- `message` (String, Required): Human-readable error description.
- `recoverable` (Boolean, Required): True if the agent can retry or take healing actions.
- `safe_retry` (Boolean, Required): True if it is safe to rerun the capability immediately.
- `retry_after_ms` (Integer, Optional): Backoff suggestion in milliseconds.
- `alternative_capabilities` (List of Strings, Optional): Registry-matched permitted capability alternatives with similar tags or domains.

---

## 5. Transport Bindings

### HTTP
- `POST /uap/tasks`: Submit a task envelope.
- `GET /uap/tasks/{task_id}`: Get task status.
- `GET /uap/tasks/{task_id}/events`: Event stream (SSE).
- `POST /uap/tasks/{task_id}/cancel`: Request cancellation.
- `GET /uap/capabilities`: List registered capabilities.

### CloudEvents 1.0 JSON Event Binding
When UAP events are published to message brokers (Kafka, EventBridge, etc.), they map to CloudEvents 1.0 format:
- `specversion`: `1.0`
- `id`: Unique event UUID (`event_id`).
- `source`: `/uap/tasks/{task_id}`.
- `type`: `dev.uap.event.{type}` (e.g. `dev.uap.event.task.accepted`).
- `time`: ISO-8601 UTC timestamp (`time`).
- `datacontenttype`: `application/json`.
- `data`: Event-specific JSON payload (`data`).
- `traceid`: Trace correlation ID (`trace_id`).
