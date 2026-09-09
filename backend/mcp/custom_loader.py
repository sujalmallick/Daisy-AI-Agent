import os
import json
import time
import shlex
import logging
import requests
import subprocess
from typing import Dict, Any, List, Optional

logger = logging.getLogger("daisy.mcp.custom")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "custom_mcps.json")

class CustomToolManager:
    """
    Manages user-defined custom MCP tools and REST webhooks.
    Supports dynamic registration into MCPManager, persistence in JSON,
    live testing, and execution via command subprocess or HTTP request.
    """

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self._tools: Dict[str, Dict[str, Any]] = {}
        self.load_tools()

    def load_tools(self) -> List[Dict[str, Any]]:
        """Loads custom tools from JSON file and populates internal registry."""
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            self._tools = {}
            return []

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                tool_list = json.load(f)
                self._tools = {t["name"]: t for t in tool_list if isinstance(t, dict) and "name" in t}
                return tool_list
        except Exception as e:
            logger.error(f"Error loading custom MCP config: {e}")
            return []

    def save_tools(self) -> bool:
        """Saves internal registry to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(list(self._tools.values()), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving custom MCP config: {e}")
            return False

    def get_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def add_or_update_tool(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """Adds or updates a custom tool and synchronizes with MCP Manager."""
        name = tool_def.get("name", "").strip().lower().replace(" ", "_")
        if not name:
            raise ValueError("Tool name is required.")

        tool_type = tool_def.get("type", "command").lower()
        if tool_type not in ("command", "http"):
            raise ValueError("Tool type must be 'command' or 'http'.")

        clean_def = {
            "name": name,
            "description": tool_def.get("description", f"Custom {tool_type} tool: {name}").strip(),
            "type": tool_type,
            "parameters": tool_def.get("parameters", {}),
            "trigger_phrases": tool_def.get("trigger_phrases", []),
            "enabled": bool(tool_def.get("enabled", True)),
        }

        if tool_type == "command":
            cmd = tool_def.get("command", "").strip()
            if not cmd:
                raise ValueError("Command string is required for command tools.")
            clean_def["command"] = cmd
            clean_def["timeout"] = int(tool_def.get("timeout", 15))
        elif tool_type == "http":
            url = tool_def.get("url", "").strip()
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("Valid HTTP or HTTPS URL is required for HTTP tools.")
            clean_def["url"] = url
            clean_def["method"] = tool_def.get("method", "GET").upper()
            clean_def["headers"] = tool_def.get("headers", {})
            clean_def["timeout"] = int(tool_def.get("timeout", 10))

        self._tools[name] = clean_def
        self.save_tools()
        self.sync_into_mcp_manager()
        return clean_def

    def delete_tool(self, name: str) -> bool:
        """Removes a custom tool by name."""
        name = name.strip().lower().replace(" ", "_")
        if name in self._tools:
            del self._tools[name]
            self.save_tools()
            self.sync_into_mcp_manager()
            return True
        return False

    def execute_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes a custom tool (command or HTTP request)."""
        args = args or {}
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Custom tool '{tool_name}' not found."}

        if not tool.get("enabled", True):
            return {"error": f"Custom tool '{tool_name}' is currently disabled."}

        tool_type = tool.get("type", "command")
        start_time = time.time()

        try:
            if tool_type == "command":
                cmd_template = tool.get("command", "")
                # Safe argument substitution
                formatted_cmd = cmd_template
                for k, v in args.items():
                    placeholder = f"{{{k}}}"
                    if placeholder in formatted_cmd:
                        formatted_cmd = formatted_cmd.replace(placeholder, str(v))

                timeout = tool.get("timeout", 15)
                res = subprocess.run(
                    formatted_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                duration_ms = round((time.time() - start_time) * 1000, 1)

                output = res.stdout.strip() if res.stdout else res.stderr.strip()
                if res.returncode != 0 and not output:
                    output = f"Process exited with code {res.returncode}"

                return {
                    "status": "success" if res.returncode == 0 else "failed",
                    "output": output,
                    "returncode": res.returncode,
                    "latency_ms": duration_ms
                }

            elif tool_type == "http":
                url = tool.get("url", "")
                method = tool.get("method", "GET").upper()
                headers = tool.get("headers", {})
                timeout = tool.get("timeout", 10)

                # Replace placeholders in URL
                formatted_url = url
                for k, v in args.items():
                    placeholder = f"{{{k}}}"
                    if placeholder in formatted_url:
                        formatted_url = formatted_url.replace(placeholder, str(v))

                if method == "GET":
                    resp = requests.get(formatted_url, params=args, headers=headers, timeout=timeout)
                elif method == "POST":
                    resp = requests.post(formatted_url, json=args, headers=headers, timeout=timeout)
                elif method == "PUT":
                    resp = requests.put(formatted_url, json=args, headers=headers, timeout=timeout)
                elif method == "DELETE":
                    resp = requests.delete(formatted_url, json=args, headers=headers, timeout=timeout)
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}

                duration_ms = round((time.time() - start_time) * 1000, 1)

                try:
                    payload = resp.json()
                except Exception:
                    payload = resp.text

                return {
                    "status": "success" if resp.ok else "http_error",
                    "status_code": resp.status_code,
                    "output": payload,
                    "latency_ms": duration_ms
                }

        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {tool.get('timeout', 15)} seconds."}
        except requests.RequestException as re:
            return {"error": f"HTTP request failed: {str(re)}"}
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}

    def test_tool(self, tool_name: str, test_args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convenience method for testing a tool and receiving diagnostics."""
        result = self.execute_tool(tool_name, test_args)
        return {
            "tool": tool_name,
            "args": test_args or {},
            "result": result
        }

    def match_trigger(self, prompt: str) -> Optional[tuple]:
        """
        Checks if prompt matches any registered trigger phrase of an enabled custom tool.
        Returns (tool_name, matched_phrase) or None.
        """
        clean = prompt.lower().strip()
        for name, tool in self._tools.items():
            if not tool.get("enabled", True):
                continue
            triggers = tool.get("trigger_phrases", [])
            for trigger in triggers:
                t_clean = trigger.lower().strip()
                if t_clean and (t_clean == clean or t_clean in clean):
                    return (name, trigger)
        return None

    def sync_into_mcp_manager(self):
        """Synchronizes custom tools into the global MCP Manager."""
        try:
            from backend.mcp.manager import mcp_manager
            # Unregister any existing custom tools first
            mcp_manager.unregister_server("custom")

            # Create an MCP Server adapter for custom tools
            adapter = CustomMCPServerAdapter(self)
            mcp_manager.register_server("custom", adapter)
            logger.info(f"Synchronized {len(self._tools)} custom tools into MCP Manager.")
        except Exception as e:
            logger.warning(f"Could not sync custom tools into MCP Manager: {e}")

class CustomMCPServerAdapter:
    """Adapts CustomToolManager to the MCP Server contract."""
    def __init__(self, manager: CustomToolManager):
        self.manager = manager

    def get_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for name, tool in self.manager._tools.items():
            if not tool.get("enabled", True):
                continue
            
            # Format parameters for LLM tool calling schema
            params = tool.get("parameters", {})
            properties = {}
            if isinstance(params, dict):
                for p_name, p_val in params.items():
                    p_type = p_val if isinstance(p_val, str) else p_val.get("type", "string")
                    p_desc = p_val.get("description", f"Parameter {p_name}") if isinstance(p_val, dict) else f"Parameter {p_name}"
                    properties[p_name] = {"type": p_type, "description": p_desc}

            tools.append({
                "name": name,
                "description": tool.get("description", f"Custom tool {name}"),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties.keys())
                }
            })
        return tools

    def execute_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Any:
        return self.manager.execute_tool(tool_name, args)

# Global singleton
custom_tool_manager = CustomToolManager()
