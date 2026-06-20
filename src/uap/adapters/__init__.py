"""Adapters from existing protocols into UAP capabilities and events."""

from .a2a import a2a_agent_card_to_capability
from .agui import uap_event_to_agui
from .cloudevents import uap_event_to_cloudevent
from .mcp import mcp_tool_to_capability, mcp_tools_to_capabilities
from .openapi import openapi_to_capabilities

__all__ = [
    "a2a_agent_card_to_capability",
    "uap_event_to_agui",
    "uap_event_to_cloudevent",
    "mcp_tool_to_capability",
    "mcp_tools_to_capabilities",
    "openapi_to_capabilities",
]
