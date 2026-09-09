import os
import glob
import logging
from typing import Dict, Any, List

logger = logging.getLogger("daisy.mcp.filesystem")

class FilesystemMCPServer:
    """
    Built-in Filesystem MCP Server.
    Enables Daisy's Agentic AI to interact with the local operating system,
    search research notes, read documents, and automate desktop tasks.
    """

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_files",
                "description": "Searches for files matching a pattern or name within user documents or a folder.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Search pattern e.g. '*.txt', 'notes'"},
                        "directory": {"type": "string", "description": "Optional directory path to search"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "read_file",
                "description": "Reads text content from a specified file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to read"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "list_directory",
                "description": "Lists contents of a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory path to list"}
                    }
                }
            }
        ]

    BLOCKED_PATTERNS = [
        ".env", ".git", ".cache", "id_rsa", "id_ed25519", "id_dsa",
        "authorized_keys", "known_hosts", "credentials", ".aws",
        "passwd", "shadow", "sam", "system32", "ntds.dit", ".ssh"
    ]

    def _is_safe_path(self, target_path: str) -> bool:
        """Validates that a path does not target sensitive system files or credentials."""
        if not target_path:
            return False
        try:
            normalized = os.path.normpath(os.path.abspath(os.path.expanduser(target_path)))
            parts = normalized.lower().split(os.sep)
            for part in parts:
                for blocked in self.BLOCKED_PATTERNS:
                    if blocked in part:
                        return False
            return True
        except Exception:
            return False

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        try:
            if tool_name == "search_files":
                pattern = args.get("pattern", "*")
                directory = args.get("directory") or os.path.expanduser("~/Documents")
                if not os.path.exists(directory):
                    directory = os.getcwd()
                if not self._is_safe_path(directory):
                    return {"error": "Access denied: Directory contains sensitive system or credential paths."}

                search_query = os.path.join(directory, f"**/*{pattern}*")
                raw_matches = glob.glob(search_query, recursive=True)
                # Filter out sensitive matches
                matches = [m for m in raw_matches if self._is_safe_path(m)][:10]
                return {
                    "count": len(matches),
                    "matches": [os.path.basename(m) for m in matches],
                    "paths": matches
                }

            elif tool_name == "read_file":
                path = args.get("file_path", "")
                if not path:
                    return {"error": "No file path provided."}
                if not self._is_safe_path(path):
                    return {"error": "Access denied: Reading credentials, secrets, or system files is forbidden."}
                if not os.path.exists(path):
                    return {"error": f"File '{path}' does not exist."}
                if os.path.isdir(path):
                    return {"error": f"Path '{path}' is a directory, not a file."}
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(2000) # limit to 2000 chars
                return {"content": content, "size_chars": len(content)}

            elif tool_name == "list_directory":
                directory = args.get("directory") or os.getcwd()
                if not self._is_safe_path(directory):
                    return {"error": "Access denied: Directory contains sensitive system or credential paths."}
                if not os.path.exists(directory):
                    return {"error": f"Directory '{directory}' does not exist."}
                items = [item for item in os.listdir(directory) if not any(b in item.lower() for b in self.BLOCKED_PATTERNS)][:20]
                return {"directory": directory, "items": items}

        except Exception as e:
            return {"error": f"Filesystem error: {str(e)}"}

        return {"error": f"Unknown Filesystem tool '{tool_name}'."}

# Register into MCP Manager
from backend.mcp.manager import mcp_manager
fs_server = FilesystemMCPServer()
mcp_manager.register_server("filesystem", fs_server)
