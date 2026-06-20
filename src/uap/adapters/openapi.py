from __future__ import annotations

from typing import Any

from ..models import CapabilityCard


def resolve_ref(schema: Any, spec: dict[str, Any], seen: set | None = None) -> Any:
    """Recursively resolve JSON references ($ref) in the OpenAPI spec."""
    if seen is None:
        seen = set()
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            if ref in seen:
                return {"type": "object", "description": f"Cyclic reference to {ref}"}
            seen.add(ref)
            parts = ref.strip("#/").split("/")
            curr = spec
            try:
                for part in parts:
                    curr = curr[part]
                return resolve_ref(curr, spec, seen)
            except KeyError:
                return {"type": "object", "description": f"Unresolved reference {ref}"}
        return {k: resolve_ref(v, spec, seen) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [resolve_ref(item, spec, seen) for item in schema]
    return schema


def openapi_to_capabilities(spec: dict[str, Any]) -> list[CapabilityCard]:
    """Convert OpenAPI operations into UAP capability cards.

    Parses parameters, JSON request bodies, and success responses to build schemas,
    and supports the `x-uap` vendor extension for overrides.
    """
    cards: list[CapabilityCard] = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue

            # Standard operation metadata
            operation_id = operation.get("operationId") or f"{method}_{path}".replace(
                "/", "_"
            ).strip("_")
            summary = operation.get("summary") or operation.get("description") or operation_id
            description = operation.get("description", "")
            tags = list(operation.get("tags", []))
            risk = "low" if method.lower() == "get" else "high"
            idempotent = method.lower() in {"get", "put", "delete"}
            requires_approval = False
            context_cost: dict[str, Any] = {}

            # Construct input schema from parameters and requestBody
            input_properties: dict[str, Any] = {}
            input_required: list[str] = []

            # 1. Parse parameters (query, path, header, etc.)
            parameters = operation.get("parameters", [])
            for p in parameters:
                p_resolved = resolve_ref(p, spec)
                name = p_resolved.get("name")
                if not name:
                    continue
                p_schema = p_resolved.get("schema", {"type": "string"})
                input_properties[name] = p_schema
                if p_resolved.get("required"):
                    input_required.append(name)

            # 2. Parse requestBody (merge fields if JSON object, else add as "body")
            request_body = operation.get("requestBody")
            if request_body:
                rb_resolved = resolve_ref(request_body, spec)
                content = rb_resolved.get("content", {})
                json_content = content.get("application/json", {})
                body_schema = json_content.get("schema")
                if body_schema:
                    body_schema_resolved = resolve_ref(body_schema, spec)
                    if body_schema_resolved.get("type") == "object":
                        props = body_schema_resolved.get("properties", {})
                        input_properties.update(props)
                        req = body_schema_resolved.get("required", [])
                        input_required.extend(req)
                    else:
                        input_properties["body"] = body_schema_resolved
                        if rb_resolved.get("required"):
                            input_required.append("body")

            input_schema = {
                "type": "object",
                "properties": input_properties,
            }
            if input_required:
                input_schema["required"] = sorted(list(set(input_required)))

            # Construct output schema from responses (first successful 2xx)
            output_schema: dict[str, Any] = {"type": "object"}
            responses = operation.get("responses", {})
            success_status = None
            for status in ["200", "201", "202", "2xx"]:
                if status in responses:
                    success_status = status
                    break
            if not success_status:
                for k in responses.keys():
                    if k.startswith("2"):
                        success_status = k
                        break
            if not success_status and "default" in responses:
                success_status = "default"

            if success_status:
                resp_resolved = resolve_ref(responses[success_status], spec)
                resp_content = resp_resolved.get("content", {})
                resp_json = resp_content.get("application/json", {})
                resp_schema = resp_json.get("schema")
                if resp_schema:
                    output_schema = resolve_ref(resp_schema, spec)

            # Support vendor extensions (x-uap)
            x_uap = operation.get("x-uap")
            if isinstance(x_uap, dict):
                if "capability_id" in x_uap:
                    operation_id = x_uap["capability_id"]
                risk_info = x_uap.get("risk", {})
                if isinstance(risk_info, dict):
                    risk = risk_info.get("level") or risk
                    requires_approval = risk_info.get("side_effect", requires_approval)
                elif isinstance(risk_info, str):
                    risk = risk_info

                if "requires_approval" in x_uap:
                    requires_approval = bool(x_uap["requires_approval"])
                if "context_cost" in x_uap:
                    context_cost = x_uap["context_cost"]
                if "tags" in x_uap:
                    tags = list(x_uap["tags"])

            cards.append(
                CapabilityCard(
                    capability_id=operation_id,
                    purpose=summary,
                    description=description,
                    input_schema=input_schema,
                    output_schema=output_schema,
                    risk=risk,
                    permissions=[f"openapi.{operation_id}"],
                    idempotent=idempotent,
                    requires_approval=requires_approval,
                    context_cost=context_cost,
                    tags=tags,
                    transport={"type": "openapi", "method": method.upper(), "path": path},
                )
            )
    return cards
