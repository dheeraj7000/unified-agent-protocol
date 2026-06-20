# Adapter Mapping Guide

## MCP to UAP

| MCP concept | UAP concept |
|---|---|
| Tool | Capability card |
| Resource | Context source |
| Prompt | Prompt template capability |
| Sampling | Model delegation capability |
| Tool result | Capability output with provenance |
| Server lifecycle | Capability registry lifecycle |

## A2A to UAP

| A2A concept | UAP concept |
|---|---|
| Agent card | Delegate capability |
| Task | UAP task |
| Artifact | UAP artifact |
| Streaming update | UAP event |
| Push notification | UAP event subscription |

## AG-UI to UAP

| AG-UI concept | UAP concept |
|---|---|
| Run | UAP task |
| Event stream | UAP events |
| User interrupt | Approval or input request |
| Frontend tool | UI-bound capability |
| Shared state | Task state or artifact |

## OpenAPI to UAP

| OpenAPI concept | UAP concept |
|---|---|
| Operation ID | Capability ID |
| Path + method | Transport binding |
| Request body schema | Input schema |
| Response schema | Output schema |
| Security scheme | Permission requirement |
| Tags | Capability tags/domain |

## CloudEvents to UAP Event Mapping

UAP streams standard task lifecycle events. When published to external brokers (Kafka, RabbitMQ, AWS EventBridge, etc.), standard `UAPEvent` data structures are serialized to standard CloudEvents 1.0 JSON format according to this mapping table:

| CloudEvents Field | Source UAP Event Field | Description / Format |
|---|---|---|
| `specversion` | (static) | `"1.0"` (CloudEvents spec version) |
| `id` | `event_id` | Unique UUID event identifier |
| `source` | (constructed) | `"/uap/tasks/{task_id}"` |
| `type` | `type` | Prefixed event type: `dev.uap.event.{type}` |
| `time` | `time` | ISO-8601 UTC timestamp format |
| `datacontenttype` | (static) | `"application/json"` |
| `data` | `data` | Event payload structure containing detail metrics or artifacts |
| `traceid` | `trace_id` | Distributed tracing transaction correlation identifier |
