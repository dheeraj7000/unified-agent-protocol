from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from uuid import uuid4

JsonDict = Dict[str, Any]


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
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    service_id: Optional[str] = None
    delegation_token: Optional[str] = None
    scopes: List[str] = field(default_factory=list)


@dataclass
class Intent:
    goal: str
    domain: Optional[str] = None
    parameters: JsonDict = field(default_factory=dict)


@dataclass
class Constraints:
    latency_ms: Optional[int] = None
    max_cost_usd: Optional[float] = None
    max_context_tokens: int = 4000
    risk_level: str = "medium"


@dataclass
class ContextRequest:
    detail: str = "minimal"
    fields: List[str] = field(default_factory=list)
    evidence_required: bool = True
    max_items: int = 20
    max_tokens: Optional[int] = None


@dataclass
class Policy:
    requires_approval: List[str] = field(default_factory=list)
    data_classes: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
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
    graph: Optional[JsonDict] = None


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
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskEnvelope":
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
    permissions: List[str] = field(default_factory=list)
    description: str = ""
    idempotent: bool = True
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    cost_estimate: str = "low"
    context_cost: JsonDict = field(default_factory=dict)
    requires_approval: bool = False
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
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
    depends_on: List[str] = field(default_factory=list)
    requires_approval: bool = False


@dataclass
class TaskGraph:
    nodes: List[TaskNode]

    def node_ids(self) -> List[str]:
        return [node.id for node in self.nodes]


@dataclass
class UAPEvent:
    type: str
    task_id: str
    data: JsonDict = field(default_factory=dict)
    uap: str = "1.0"
    event_id: str = field(default_factory=lambda: new_id("evt"))
    time: str = field(default_factory=now_iso)
    trace_id: Optional[str] = None

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
