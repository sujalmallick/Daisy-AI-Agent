import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger("daisy.hitl")


class RiskTier:
    SAFE = 1           # Auto-execute (Spotify, file search/read, RAG query, volume)
    AMBIGUOUS = 2      # Disambiguation (Multiple documents or ambiguous commands)
    DESTRUCTIVE = 3    # Hard confirmation required (App close, file deletion, system shutdown)


class HITLManager:
    """
    Human-In-The-Loop (HITL) Safety & Disambiguation Coordinator.
    - Evaluates action risk policies against desktop operations.
    - Pauses agentic loops or fastpath execution at risk boundaries.
    - Resumes or aborts actions based on 0-token voice (AMAZON.Yes/No) or UI button clicks.
    """

    CONFIRMATION_TIMEOUT_SECS = 30.0

    # Explicit risk mappings for MCP tools
    DESTRUCTIVE_TOOLS = {
        "app_launcher.close_app",
        "filesystem.delete_file",
        "filesystem.write_file",
        "system.exit_app",
        "system.close_window",
    }

    def __init__(self):
        self._pending_action: Optional[Dict[str, Any]] = None

    def evaluate_risk(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> int:
        """Determines the risk tier of a given tool call."""
        norm_name = tool_name.replace("_", ".")
        if norm_name in self.DESTRUCTIVE_TOOLS or tool_name in self.DESTRUCTIVE_TOOLS:
            return RiskTier.DESTRUCTIVE

        # Any tool with explicit 'delete', 'remove', 'kill', 'terminate'
        lower_name = tool_name.lower()
        if any(w in lower_name for w in ["delete", "remove", "kill", "terminate", "format"]):
            return RiskTier.DESTRUCTIVE

        return RiskTier.SAFE

    def has_pending(self) -> bool:
        """Checks if a valid, unexpired confirmation is currently waiting for input."""
        if self._pending_action is None:
            return False
        if time.time() - self._pending_action["created_at"] > self.CONFIRMATION_TIMEOUT_SECS:
            logger.info("Pending HITL confirmation expired.")
            self._pending_action = None
            return False
        return True

    def get_pending(self) -> Optional[Dict[str, Any]]:
        """Returns the active pending confirmation if not expired."""
        if self.has_pending():
            return self._pending_action
        return None

    def request_confirmation(
        self,
        action_type: str,
        tool_name: str,
        args: Dict[str, Any],
        prompt_message: str,
        display_name: str = "",
        risk_tier: int = RiskTier.DESTRUCTIVE,
        candidates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Creates an active confirmation breakpoint.
        """
        action_id = uuid.uuid4().hex[:8]
        self._pending_action = {
            "action_id": action_id,
            "action_type": action_type,
            "tool_name": tool_name,
            "args": args,
            "prompt_message": prompt_message,
            "display_name": display_name or tool_name,
            "risk_tier": risk_tier,
            "candidates": candidates or [],
            "created_at": time.time()
        }
        logger.info(f"HITL breakpoint registered: {action_type} for '{tool_name}' (ID: {action_id})")

        return {
            "status": "awaiting_confirmation",
            "action_id": action_id,
            "action_type": action_type,
            "prompt_message": prompt_message,
            "display_name": display_name or tool_name,
            "risk_tier": risk_tier,
            "candidates": candidates or [],
            "awaiting_confirmation": True
        }

    def resolve(self, approved: bool) -> Dict[str, Any]:
        """
        Resolves pending confirmation with approval or denial.
        Executes the pending tool if approved.
        """
        if not self.has_pending():
            return {
                "success": False,
                "status": "no_pending_action",
                "message": "No action is currently waiting for confirmation."
            }

        action = self._pending_action
        self._pending_action = None
        display = action.get("display_name", "the requested action")

        if not approved:
            logger.info(f"HITL action {action['action_id']} rejected by user.")
            return {
                "success": True,
                "status": "cancelled",
                "action": "cancel",
                "tool": action["tool_name"],
                "message": f"Okay, cancelled {display}."
            }

        logger.info(f"HITL action {action['action_id']} approved by user. Executing tool {action['tool_name']}...")
        from backend.mcp.manager import mcp_manager

        # Special handling for app exit
        if action["tool_name"] == "system.exit_app":
            return {
                "success": True,
                "status": "exiting",
                "action": "exit_app",
                "should_exit": True,
                "message": "Sayonara! Goodbye!"
            }

        exec_res = mcp_manager.execute(action["tool_name"], action["args"])
        return {
            "success": exec_res.get("success", False),
            "status": "executed",
            "tool": action["tool_name"],
            "result": exec_res.get("result", {}),
            "message": f"Confirmed and completed: {display}."
        }

    def clear(self):
        """Clears active pending confirmation."""
        self._pending_action = None


# Global singleton
hitl_manager = HITLManager()
