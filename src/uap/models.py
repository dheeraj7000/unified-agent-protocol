from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

JsonDict = dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_dict(v) for k, v in asdict(value).items() if v is not None}
    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_dict(v) for v in value]
    return value


@dataclass
class Actor:
    agent_id: str
    user_id: str | None = None
    org_id: str | None = None
    service_id: str | None = None
    delegation_token: str | None = None
    scopes: list[str] = field(default_factory=list)


@dataclass
class Intent:
    goal: str
    domain: str | None = None
    parameters: JsonDict = field(default_factory=dict)


@dataclass
class Constraints:
    latency_ms: int | None = None
    max_cost_usd: float | None = None
    max_context_tokens: int = 4000
    risk_level: str = "medium"
    node_timeout_ms: int | None = None


SUPPORTED_UAP_VERSIONS = frozenset({"0.1", "1.0"})
UAP_RUNTIME_VERSION = "0.1"
UAP_FEATURES = [
    "dag_execution",
    "policy_enforcement",
    "sse_events",
    "provenance",
    "field_masking",
    "approval_lifecycle",
    "task_cancellation",
    "version_negotiation",
]


@dataclass
class ContextRequest:
    detail: str = "minimal"
    fields: list[str] = field(default_factory=list)
    evidence_required: bool = True
    max_items: int = 20
    max_tokens: int | None = None


@dataclass
class Policy:
    requires_approval: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    max_risk: str = "high"


@dataclass
class ReturnSpec:
    stream: bool = True
    format: str = "summary+artifacts"


@dataclass
class ExecutionSpec:
    mode: str = "server_optimized"
    parallelism: int = 5
    allow_partial_results: bool = True
    graph: JsonDict | None = None


@dataclass
class TaskEnvelope:
    actor: Actor
    intent: Intent
    task_id: str = field(default_factory=lambda: new_id("tsk"))
    uap: str = "1.0"
    type: str = "task.invoke"
    constraints: Constraints = field(default_factory=Constraints)
    context_request: ContextRequest = field(default_factory=ContextRequest)
    policy: Policy = field(default_factory=Policy)
    execution: ExecutionSpec = field(default_factory=ExecutionSpec)
    return_spec: ReturnSpec = field(default_factory=ReturnSpec)
    metadata: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TaskEnvelope:
        return cls(
            uap=data.get("uap", "1.0"),
            type=data.get("type", "task.invoke"),
            task_id=data.get("task_id") or new_id("tsk"),
            actor=Actor(**data.get("actor", {})),
            intent=Intent(**data.get("intent", {})),
            constraints=Constraints(**data.get("constraints", {})),
            context_request=ContextRequest(**data.get("context_request", {})),
            policy=Policy(**data.get("policy", {})),
            execution=ExecutionSpec(**data.get("execution", {})),
            return_spec=ReturnSpec(**data.get("return", data.get("return_spec", {}))),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> JsonDict:
        result = to_dict(self)
        result["return"] = result.pop("return_spec", {})
        return result


@dataclass
class CapabilityCard:
    capability_id: str
    purpose: str
    input_schema: JsonDict
    output_schema: JsonDict
    risk: str = "low"
    permissions: list[str] = field(default_factory=list)
    description: str = ""
    idempotent: bool = True
    latency_p50_ms: int | None = None
    latency_p95_ms: int | None = None
    cost_estimate: str = "low"
    context_cost: JsonDict = field(default_factory=dict)
    requires_approval: bool = False
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    transport: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return to_dict(self)


CapabilityHandler = Callable[[JsonDict, "TaskEnvelope"], Any]


@dataclass
class RegisteredCapability:
    card: CapabilityCard
    handler: CapabilityHandler


@dataclass
class TaskNode:
    id: str
    capability: str
    input: JsonDict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    requires_approval: bool = False


@dataclass
class TaskGraph:
    nodes: list[TaskNode]

    def node_ids(self) -> list[str]:
        return [node.id for node in self.nodes]


@dataclass
class UAPEvent:
    type: str
    task_id: str
    data: JsonDict = field(default_factory=dict)
    uap: str = "1.0"
    event_id: str = field(default_factory=lambda: new_id("evt"))
    time: str = field(default_factory=now_iso)
    trace_id: str | None = None

    def to_dict(self) -> JsonDict:
        return to_dict(self)


@dataclass
class ProvenanceRecord:
    task_id: str
    capability_id: str
    actor_id: str
    input_digest: str
    output_digest: str
    trace_id: str
    time: str = field(default_factory=now_iso)
    metadata: JsonDict = field(default_factory=dict)


# cache_bust = 1
