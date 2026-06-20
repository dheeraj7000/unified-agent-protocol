from __future__ import annotations

from typing import Any, Mapping

from .errors import ValidationError


REQUIRED_ENVELOPE_FIELDS = {"uap", "type", "task_id", "actor", "intent"}


def validate_envelope_minimal(data: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_ENVELOPE_FIELDS - set(data.keys()))
    if missing:
        raise ValidationError(
            code="INVALID_ENVELOPE",
            message="UAP envelope is missing required fields",
            recoverable=True,
            safe_retry=False,
            details={"missing": missing},
        )

    # Validate basic envelope strings
    if not isinstance(data.get("uap"), str):
        raise ValidationError("INVALID_ENVELOPE", "uap must be a string", True, False)
    if not isinstance(data.get("type"), str):
        raise ValidationError("INVALID_ENVELOPE", "type must be a string", True, False)
    if data.get("task_id") is not None and not isinstance(data.get("task_id"), str):
        raise ValidationError("INVALID_ENVELOPE", "task_id must be a string", True, False)

    # Actor validation
    actor = data.get("actor")
    if not isinstance(actor, Mapping):
        raise ValidationError("INVALID_ACTOR", "actor must be an object/mapping", True, False)
    if "agent_id" not in actor:
        raise ValidationError("INVALID_ACTOR", "actor is missing agent_id", True, False)
    if not isinstance(actor["agent_id"], str):
        raise ValidationError("INVALID_ACTOR", "actor.agent_id must be a string", True, False)
    for field_name in ["user_id", "org_id", "service_id", "delegation_token"]:
        val = actor.get(field_name)
        if val is not None and not isinstance(val, str):
            raise ValidationError("INVALID_ACTOR", f"actor.{field_name} must be a string", True, False)
    scopes = actor.get("scopes")
    if scopes is not None:
        if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise ValidationError("INVALID_ACTOR", "actor.scopes must be a list of strings", True, False)

    # Intent validation
    intent = data.get("intent")
    if not isinstance(intent, Mapping):
        raise ValidationError("INVALID_INTENT", "intent must be an object/mapping", True, False)
    if "goal" not in intent:
        raise ValidationError("INVALID_INTENT", "intent is missing goal", True, False)
    if not isinstance(intent["goal"], str):
        raise ValidationError("INVALID_INTENT", "intent.goal must be a string", True, False)
    if intent.get("domain") is not None and not isinstance(intent["domain"], str):
        raise ValidationError("INVALID_INTENT", "intent.domain must be a string", True, False)
    if intent.get("parameters") is not None and not isinstance(intent["parameters"], Mapping):
        raise ValidationError("INVALID_INTENT", "intent.parameters must be an object/mapping", True, False)

    # Constraints validation
    constraints = data.get("constraints")
    if constraints is not None:
        if not isinstance(constraints, Mapping):
            raise ValidationError("INVALID_CONSTRAINTS", "constraints must be an object/mapping", True, False)
        if constraints.get("latency_ms") is not None and not isinstance(constraints["latency_ms"], int):
            raise ValidationError("INVALID_CONSTRAINTS", "constraints.latency_ms must be an integer", True, False)
        if constraints.get("max_cost_usd") is not None and not isinstance(constraints["max_cost_usd"], (int, float)):
            raise ValidationError("INVALID_CONSTRAINTS", "constraints.max_cost_usd must be a number", True, False)
        if constraints.get("max_context_tokens") is not None and not isinstance(constraints["max_context_tokens"], int):
            raise ValidationError("INVALID_CONSTRAINTS", "constraints.max_context_tokens must be an integer", True, False)
        if constraints.get("risk_level") is not None and not isinstance(constraints["risk_level"], str):
            raise ValidationError("INVALID_CONSTRAINTS", "constraints.risk_level must be a string", True, False)

    # Context Request validation
    context_req = data.get("context_request")
    if context_req is not None:
        if not isinstance(context_req, Mapping):
            raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request must be an object/mapping", True, False)
        if context_req.get("detail") is not None and not isinstance(context_req["detail"], str):
            raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request.detail must be a string", True, False)
        fields = context_req.get("fields")
        if fields is not None:
            if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
                raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request.fields must be a list of strings", True, False)
        if context_req.get("evidence_required") is not None and not isinstance(context_req["evidence_required"], bool):
            raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request.evidence_required must be a boolean", True, False)
        if context_req.get("max_items") is not None and not isinstance(context_req["max_items"], int):
            raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request.max_items must be an integer", True, False)
        if context_req.get("max_tokens") is not None and not isinstance(context_req["max_tokens"], int):
            raise ValidationError("INVALID_CONTEXT_REQUEST", "context_request.max_tokens must be an integer", True, False)

    # Policy validation
    policy = data.get("policy")
    if policy is not None:
        if not isinstance(policy, Mapping):
            raise ValidationError("INVALID_POLICY", "policy must be an object/mapping", True, False)
        for list_field in ["requires_approval", "data_classes", "allowed_tools", "denied_tools"]:
            lst = policy.get(list_field)
            if lst is not None:
                if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
                    raise ValidationError("INVALID_POLICY", f"policy.{list_field} must be a list of strings", True, False)
        if policy.get("max_risk") is not None and not isinstance(policy["max_risk"], str):
            raise ValidationError("INVALID_POLICY", "policy.max_risk must be a string", True, False)

    # Execution validation
    execution = data.get("execution")
    if execution is not None:
        if not isinstance(execution, Mapping):
            raise ValidationError("INVALID_EXECUTION", "execution must be an object/mapping", True, False)
        if execution.get("mode") is not None and not isinstance(execution["mode"], str):
            raise ValidationError("INVALID_EXECUTION", "execution.mode must be a string", True, False)
        if execution.get("parallelism") is not None and not isinstance(execution["parallelism"], int):
            raise ValidationError("INVALID_EXECUTION", "execution.parallelism must be an integer", True, False)
        if execution.get("allow_partial_results") is not None and not isinstance(execution["allow_partial_results"], bool):
            raise ValidationError("INVALID_EXECUTION", "execution.allow_partial_results must be a boolean", True, False)
        
        # Validate custom execution graph if supplied
        graph = execution.get("graph")
        if graph is not None:
            if not isinstance(graph, Mapping):
                raise ValidationError("INVALID_EXECUTION_GRAPH", "execution.graph must be an object/mapping", True, False)
            nodes = graph.get("nodes")
            if not isinstance(nodes, list):
                raise ValidationError("INVALID_EXECUTION_GRAPH", "execution.graph.nodes must be a list", True, False)
            for i, node in enumerate(nodes):
                if not isinstance(node, Mapping):
                    raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}] must be an object/mapping", True, False)
                if "id" not in node or not isinstance(node["id"], str):
                    raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}].id must be a string", True, False)
                if "capability" not in node or not isinstance(node["capability"], str):
                    raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}].capability must be a string", True, False)
                if node.get("input") is not None and not isinstance(node["input"], Mapping):
                    raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}].input must be an object/mapping", True, False)
                dep = node.get("depends_on")
                if dep is not None:
                    if not isinstance(dep, list) or not all(isinstance(d, str) for d in dep):
                        raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}].depends_on must be a list of strings", True, False)
                if node.get("requires_approval") is not None and not isinstance(node["requires_approval"], bool):
                    raise ValidationError("INVALID_EXECUTION_GRAPH", f"execution.graph.nodes[{i}].requires_approval must be a boolean", True, False)

    # Return validation
    ret = data.get("return") or data.get("return_spec")
    if ret is not None:
        if not isinstance(ret, Mapping):
            raise ValidationError("INVALID_RETURN", "return specification must be an object/mapping", True, False)
        if ret.get("stream") is not None and not isinstance(ret["stream"], bool):
            raise ValidationError("INVALID_RETURN", "return.stream must be a boolean", True, False)
        if ret.get("format") is not None and not isinstance(ret["format"], str):
            raise ValidationError("INVALID_RETURN", "return.format must be a string", True, False)

