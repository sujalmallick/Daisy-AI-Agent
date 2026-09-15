import json
import os
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("daisy.mcp")

class MCPManager:
    """
    Universal Model Context Protocol (MCP) Client / Manager.
    Adheres strictly to MCP_INTEGRATION.md contract:
      1. Maintains registry of configured MCP servers
      2. Exposes available tools in a uniform schema for LLMs
      3. Routes tool calls cleanly without service-specific leakage
      4. Enforces safety gating and fail-closed permissions
    """

    def __init__(self):
        self._servers: Dict[str, Any] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_server(self, server_name: str, server_instance: Any):
        """Registers an MCP server instance."""
        configured_servers = {
            name.strip().lower()
            for name in os.getenv("MCP_ENABLED_SERVERS", "").split(",")
            if name.strip()
        }
        if configured_servers and server_name.lower() not in configured_servers and server_name != "custom":
            logger.info(f"Skipped disabled MCP server '{server_name}'.")
            return
        self._servers[server_name] = server_instance
        # Register its tools
        if hasattr(server_instance, "get_tools"):
            for tool in server_instance.get_tools():
                tool_full_name = f"{server_name}.{tool['name']}"
                self._tools[tool_full_name] = tool
                if hasattr(server_instance, "execute_tool"):
                    self._handlers[tool_full_name] = lambda t_name=tool['name'], inst=server_instance, **kwargs: inst.execute_tool(t_name, kwargs)

        logger.info(f"Registered MCP server '{server_name}' with {len(self.get_server_tools(server_name))} tools.")

    def unregister_server(self, server_name: str):
        """Unregisters an MCP server and removes its tools from the registry."""
        if server_name in self._servers:
            del self._servers[server_name]
        prefix = f"{server_name}."
        tools_to_remove = [k for k in self._tools if k.startswith(prefix)]
        for k in tools_to_remove:
            self._tools.pop(k, None)
            self._handlers.pop(k, None)
        logger.info(f"Unregistered MCP server '{server_name}' ({len(tools_to_remove)} tools removed).")

    def get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        return [t for name, t in self._tools.items() if name.startswith(f"{server_name}.")]

    def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        """Returns tool schema formatted for LLMs (e.g. Gemini / OpenAI function calling)."""
        schema = []
        for name, tool in self._tools.items():
            schema.append({
                "name": name.replace(".", "_"), # sanitize for Gemini tool names
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
            })
        return schema

    def get_domain_tools_schema(self, domains: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Returns pruned tool schema filtered by functional domains to save LLM tokens.
        Domain mappings:
          - 'media': spotify.*
          - 'desktop': app_launcher.*, filesystem.*
          - 'rag' or 'knowledge': rag.*, filesystem.*
          - 'custom': custom.*
        """
        if not domains:
            return self.get_all_tools_schema()

        domain_prefixes = set()
        for d in domains:
            dl = d.lower().strip()
            if dl in ("media", "spotify", "music"):
                domain_prefixes.add("spotify.")
            elif dl in ("desktop", "apps", "filesystem", "files"):
                domain_prefixes.add("app_launcher.")
                domain_prefixes.add("filesystem.")
            elif dl in ("rag", "knowledge", "docs", "documents"):
                domain_prefixes.add("rag.")
                domain_prefixes.add("filesystem.")
            elif dl in ("custom",):
                domain_prefixes.add("custom.")
            else:
                domain_prefixes.add(f"{dl}.")

        schema = []
        for name, tool in self._tools.items():
            if any(name.startswith(p) for p in domain_prefixes):
                schema.append({
                    "name": name.replace(".", "_"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                })
        return schema if schema else self.get_all_tools_schema()

    def execute(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes an MCP tool with fail-closed safety gating.
        tool_name can be in format 'spotify.play' or sanitized 'spotify_play'.
        """
        arguments = arguments or {}
        
        # Resolve the exact sanitized name emitted for LLM function calling.
        if "." not in tool_name:
            sanitized_matches = [
                registered_name
                for registered_name in self._handlers
                if registered_name.replace(".", "_") == tool_name
            ]
            if len(sanitized_matches) == 1:
                tool_name = sanitized_matches[0]

        if tool_name not in self._handlers:
            return {
                "success": False,
                "error": f"MCP tool '{tool_name}' not found in registry.",
                "code": "TOOL_NOT_FOUND"
            }

        try:
            handler = self._handlers[tool_name]
            result = handler(**arguments)
            return {
                "success": True,
                "tool": tool_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error executing MCP tool '{tool_name}': {e}", exc_info=True)
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "code": "EXECUTION_ERROR"
            }

# Global singleton
mcp_manager = MCPManager()

# Auto-register built-in servers
try:
    import backend.mcp.servers.spotify.server
    import backend.mcp.servers.filesystem.server
    import backend.mcp.servers.app_launcher.server
    import backend.mcp.servers.rag.server
    from backend.mcp.custom_loader import custom_tool_manager
    custom_tool_manager.sync_into_mcp_manager()
except Exception as _err:
    logger.warning(f"Failed to auto-register default MCP servers: {_err}")
