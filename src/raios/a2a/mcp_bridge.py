"""A2A does not replace MCP. External agents cannot call MCP directly."""

from __future__ import annotations

from typing import Any

from .failclosed import MCP_BYPASS_FORBIDDEN, FailClosed

EXISTING_MCP_GATEWAY = "scripts/ai-os/raios_mcp/gateway.py"
EXISTING_MCP_SERVER = "scripts/ai-os/raios_mcp/server.py"

REQUIRED_TOOL_PATH = (
    "A2A",
    "RAIOS policy/control",
    "internal capability",
    "MCP",
    "tool",
)


def forbid_direct(agent_id: str | None = None) -> None:
    raise FailClosed(MCP_BYPASS_FORBIDDEN, agent_id or "")


def route_tools(*, via_control_plane: bool, tools_required: list[str]) -> dict[str, Any]:
    if not via_control_plane:
        forbid_direct()
    if not tools_required:
        return {"MCP_USED": False, "PATH": REQUIRED_TOOL_PATH, "STATUS": "NOT_REQUIRED"}
    # Foundation does not invoke live MCP. Live tool use remains UCP-owned.
    return {
        "MCP_USED": False,
        "PATH": REQUIRED_TOOL_PATH,
        "STATUS": "DEFERRED_TO_UNIFIED_CONTROL_PLANE",
        "EXISTING_MCP_GATEWAY": EXISTING_MCP_GATEWAY,
    }
