from __future__ import annotations

from typing import Any

from ..models import CapabilityCard


def mcp_tool_to_capability(tool: dict[str, Any], server_name: str = "mcp") -> CapabilityCard:
    """Map an MCP-style tool descriptor to a UAP capability card."""

    name = tool.get("name") or tool.get("id")
    description = tool.get("description", "")
    return CapabilityCard(
        capability_id=f"{server_name}.{name}",
        purpose=description[:160] or name,
        description=description,
        input_schema=tool.get("inputSchema", tool.get("input_schema", {"type": "object"})),
        output_schema=tool.get("outputSchema", tool.get("output_schema", {"type": "object"})),
        risk=tool.get("risk", "medium"),
        permissions=tool.get("permissions", [f"mcp.{server_name}.{name}"]),
        idempotent=tool.get("idempotent", False),
        tags=tool.get("tags", ["mcp"]),
        transport={"type": "mcp", "server": server_name, "tool": name},
    )


def mcp_tools_to_capabilities(
    tools: list[dict[str, Any]], server_name: str = "mcp"
) -> list[CapabilityCard]:
    return [mcp_tool_to_capability(tool, server_name=server_name) for tool in tools]
