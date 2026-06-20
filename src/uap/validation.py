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
        raise ValidationError(code="INVALID_ENVELOPE", message="uap must be a string", recoverable=True, safe_retry=False)
    if not isinstance(data.get("type"), str):
        raise ValidationError(code="INVALID_ENVELOPE", message="type must be a string", recoverable=True, safe_retry=False)
    if data.get("task_id") is not None and not isinstance(data.get("task_id"), str):
        raise ValidationError(code="INVALID_ENVELOPE", message="task_id must be a string", recoverable=True, safe_retry=False)

    # Actor validation
    actor = data.get("actor")
    if not isinstance(actor, Mapping):
        raise ValidationError(code="INVALID_ACTOR", message="actor must be an object/mapping", recoverable=True, safe_retry=False)
    if "agent_id" not in actor:
        raise ValidationError(code="INVALID_ACTOR", message="actor is missing agent_id", recoverable=True, safe_retry=False)
    if not isinstance(actor["agent_id"], str):
        raise ValidationError(code="INVALID_ACTOR", message="actor.agent_id must be a string", recoverable=True, safe_retry=False)
    for field_name in ["user_id", "org_id", "service_id", "delegation_token"]:
        val = actor.get(field_name)
        if val is not None and not isinstance(val, str):
            raise ValidationError(code="INVALID_ACTOR", message=f"actor.{field_name} must be a string", recoverable=True, safe_retry=False)
    scopes = actor.get("scopes")
    if scopes is not None:
        if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise ValidationError(code="INVALID_ACTOR", message="actor.scopes must be a list of strings", recoverable=True, safe_retry=False)

    # Intent validation
    intent = data.get("intent")
    if not isinstance(intent, Mapping):
        raise ValidationError(code="INVALID_INTENT", message="intent must be an object/mapping", recoverable=True, safe_retry=False)
    if "goal" not in intent:
        raise ValidationError(code="INVALID_INTENT", message="intent is missing goal", recoverable=True, safe_retry=False)
    if not isinstance(intent["goal"], str):
        raise ValidationError(code="INVALID_INTENT", message="intent.goal must be a string", recoverable=True, safe_retry=False)
    if intent.get("domain") is not None and not isinstance(intent["domain"], str):
        raise ValidationError(code="INVALID_INTENT", message="intent.domain must be a string", recoverable=True, safe_retry=False)
    if intent.get("parameters") is not None and not isinstance(intent["parameters"], Mapping):
        raise ValidationError(code="INVALID_INTENT", message="intent.parameters must be an object/mapping", recoverable=True, safe_retry=False)

    # Constraints validation
    constraints = data.get("constraints")
    if constraints is not None:
        if not isinstance(constraints, Mapping):
            raise ValidationError(code="INVALID_CONSTRAINTS", message="constraints must be an object/mapping", recoverable=True, safe_retry=False)
        if constraints.get("latency_ms") is not None and not isinstance(constraints["latency_ms"], int):
            raise ValidationError(code="INVALID_CONSTRAINTS", message="constraints.latency_ms must be an integer", recoverable=True, safe_retry=False)
        if constraints.get("max_cost_usd") is not None and not isinstance(constraints["max_cost_usd"], (int, float)):
            raise ValidationError(code="INVALID_CONSTRAINTS", message="constraints.max_cost_usd must be a number", recoverable=True, safe_retry=False)
        if constraints.get("max_context_tokens") is not None and not isinstance(constraints["max_context_tokens"], int):
            raise ValidationError(code="INVALID_CONSTRAINTS", message="constraints.max_context_tokens must be an integer", recoverable=True, safe_retry=False)
        if constraints.get("risk_level") is not None and not isinstance(constraints["risk_level"], str):
            raise ValidationError(code="INVALID_CONSTRAINTS", message="constraints.risk_level must be a string", recoverable=True, safe_retry=False)

    # Context Request validation
    context_req = data.get("context_request")
    if context_req is not None:
        if not isinstance(context_req, Mapping):
            raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request must be an object/mapping", recoverable=True, safe_retry=False)
        if context_req.get("detail") is not None and not isinstance(context_req["detail"], str):
            raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request.detail must be a string", recoverable=True, safe_retry=False)
        fields = context_req.get("fields")
        if fields is not None:
            if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
                raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request.fields must be a list of strings", recoverable=True, safe_retry=False)
        if context_req.get("evidence_required") is not None and not isinstance(context_req["evidence_required"], bool):
            raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request.evidence_required must be a boolean", recoverable=True, safe_retry=False)
        if context_req.get("max_items") is not None and not isinstance(context_req["max_items"], int):
            raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request.max_items must be an integer", recoverable=True, safe_retry=False)
        if context_req.get("max_tokens") is not None and not isinstance(context_req["max_tokens"], int):
            raise ValidationError(code="INVALID_CONTEXT_REQUEST", message="context_request.max_tokens must be an integer", recoverable=True, safe_retry=False)

    # Policy validation
    policy = data.get("policy")
    if policy is not None:
        if not isinstance(policy, Mapping):
            raise ValidationError(code="INVALID_POLICY", message="policy must be an object/mapping", recoverable=True, safe_retry=False)
        for list_field in ["requires_approval", "data_classes", "allowed_tools", "denied_tools"]:
            lst = policy.get(list_field)
            if lst is not None:
                if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
                    raise ValidationError(code="INVALID_POLICY", message=f"policy.{list_field} must be a list of strings", recoverable=True, safe_retry=False)
        if policy.get("max_risk") is not None and not isinstance(policy["max_risk"], str):
            raise ValidationError(code="INVALID_POLICY", message="policy.max_risk must be a string", recoverable=True, safe_retry=False)

    # Execution validation
    execution = data.get("execution")
    if execution is not None:
        if not isinstance(execution, Mapping):
            raise ValidationError(code="INVALID_EXECUTION", message="execution must be an object/mapping", recoverable=True, safe_retry=False)
        if execution.get("mode") is not None and not isinstance(execution["mode"], str):
            raise ValidationError(code="INVALID_EXECUTION", message="execution.mode must be a string", recoverable=True, safe_retry=False)
        if execution.get("parallelism") is not None and not isinstance(execution["parallelism"], int):
            raise ValidationError(code="INVALID_EXECUTION", message="execution.parallelism must be an integer", recoverable=True, safe_retry=False)
        if execution.get("allow_partial_results") is not None and not isinstance(execution["allow_partial_results"], bool):
            raise ValidationError(code="INVALID_EXECUTION", message="execution.allow_partial_results must be a boolean", recoverable=True, safe_retry=False)
        
        # Validate custom execution graph if supplied
        graph = execution.get("graph")
        if graph is not None:
            if not isinstance(graph, Mapping):
                raise ValidationError(code="INVALID_EXECUTION_GRAPH", message="execution.graph must be an object/mapping", recoverable=True, safe_retry=False)
            nodes = graph.get("nodes")
            if not isinstance(nodes, list):
                raise ValidationError(code="INVALID_EXECUTION_GRAPH", message="execution.graph.nodes must be a list", recoverable=True, safe_retry=False)
            for i, node in enumerate(nodes):
                if not isinstance(node, Mapping):
                    raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}] must be an object/mapping", recoverable=True, safe_retry=False)
                if "id" not in node or not isinstance(node["id"], str):
                    raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}].id must be a string", recoverable=True, safe_retry=False)
                if "capability" not in node or not isinstance(node["capability"], str):
                    raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}].capability must be a string", recoverable=True, safe_retry=False)
                if node.get("input") is not None and not isinstance(node["input"], Mapping):
                    raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}].input must be an object/mapping", recoverable=True, safe_retry=False)
                dep = node.get("depends_on")
                if dep is not None:
                    if not isinstance(dep, list) or not all(isinstance(d, str) for d in dep):
                        raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}].depends_on must be a list of strings", recoverable=True, safe_retry=False)
                if node.get("requires_approval") is not None and not isinstance(node["requires_approval"], bool):
                    raise ValidationError(code="INVALID_EXECUTION_GRAPH", message=f"execution.graph.nodes[{i}].requires_approval must be a boolean", recoverable=True, safe_retry=False)

    # Return validation
    ret = data.get("return") or data.get("return_spec")
    if ret is not None:
        if not isinstance(ret, Mapping):
            raise ValidationError(code="INVALID_RETURN", message="return specification must be an object/mapping", recoverable=True, safe_retry=False)
        if ret.get("stream") is not None and not isinstance(ret["stream"], bool):
            raise ValidationError(code="INVALID_RETURN", message="return.stream must be a boolean", recoverable=True, safe_retry=False)
        if ret.get("format") is not None and not isinstance(ret["format"], str):
            raise ValidationError(code="INVALID_RETURN", message="return.format must be a string", recoverable=True, safe_retry=False)
