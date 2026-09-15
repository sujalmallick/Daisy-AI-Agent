"""
Human-in-the-Loop (HITL) Safety Engine for Daisy.
Manages action risk policies, execution breakpoints, and confirmation state.
"""
from backend.hitl.manager import hitl_manager

__all__ = ["hitl_manager"]
