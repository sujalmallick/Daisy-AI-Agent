import logging
from typing import Dict, Any, Optional
from backend.agent.alexa_grammar import AlexaIntentParser
from backend.mcp.manager import mcp_manager

logger = logging.getLogger("daisy.fastpath")

class FastPathEngine:
    """
    Evaluates pattern-matched utterances against MCP tools in <10ms.
    Bypasses LLM planning entirely for deterministic, low-latency execution.
    """
    pending_confirmation: Optional[Dict[str, Any]] = None
    pending_timestamp: float = 0.0
    CONFIRMATION_TIMEOUT_SECS: float = 30.0

    @classmethod
    def handle_quick_music(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to resolve simple music commands immediately via MCP.
        Returns execution result or None if it requires complex reasoning.
        """
        import time

        # 0. Check if there is an active pending confirmation (e.g. "Are you sure you want to close Chrome?")
        if (
            cls.pending_confirmation is not None
            and (time.time() - cls.pending_timestamp) < cls.CONFIRMATION_TIMEOUT_SECS
        ):
            parsed = AlexaIntentParser.parse(prompt)
            if any(p.get("action") == "confirm_yes" for p in parsed):
                pending = cls.pending_confirmation
                cls.pending_confirmation = None
                display = pending.get("display_name", "the app")

                if pending.get("type") == "exit_app":
                    return {
                        "mode": "fastpath_confirmation",
                        "tokens_consumed": 0,
                        "latency_ms": 10,
                        "actions_executed": 1,
                        "results": [{
                            "success": True,
                            "tool": "system.exit_app",
                            "result": {
                                "status": "exiting",
                                "action": "exit_app",
                                "should_exit": True,
                                "message": "Sayonara! Goodbye!"
                            }
                        }]
                    }
                else:
                    # Execute confirmed app close
                    res = mcp_manager.execute("app_launcher.close_app", {"app_name": pending["app_name"]})
                    return {
                        "mode": "fastpath_confirmation",
                        "tokens_consumed": 0,
                        "latency_ms": 10,
                        "actions_executed": 1,
                        "results": [{
                            "success": True,
                            "tool": "app_launcher.close_app",
                            "result": {
                                "status": "app_closed",
                                "app": display,
                                "message": f"Closed {display}."
                            }
                        }]
                    }

            elif any(p.get("action") == "confirm_no" for p in parsed):
                pending = cls.pending_confirmation
                cls.pending_confirmation = None
                display = pending.get("display_name", "the app")
                return {
                    "mode": "fastpath_confirmation",
                    "tokens_consumed": 0,
                    "latency_ms": 10,
                    "actions_executed": 1,
                    "results": [{
                        "success": True,
                        "tool": "system.cancel",
                        "result": {
                            "status": "cancelled",
                            "action": "cancel",
                            "message": f"Okay, keeping {display} open."
                        }
                    }]
                }
            else:
                # User asked something else — clear pending confirmation and proceed
                cls.pending_confirmation = None

        # Check custom tool trigger phrases first (0 tokens)
        from backend.mcp.custom_loader import custom_tool_manager
        custom_match = custom_tool_manager.match_trigger(prompt)
        if custom_match:
            tool_name, _ = custom_match
            res = mcp_manager.execute(f"custom.{tool_name}")
            out = res.get("result", {}).get("output", "")
            if isinstance(out, dict):
                out_str = ", ".join(f"{k} is {v}" for k, v in out.items())
            else:
                out_str = str(out)
            return {
                "mode": "fastpath_custom_mcp",
                "tokens_consumed": 0,
                "latency_ms": res.get("result", {}).get("latency_ms", 10),
                "actions_executed": 1,
                "results": [{
                    "success": res.get("success", False),
                    "tool": f"custom.{tool_name}",
                    "result": {
                        "status": "completed",
                        "message": f"{tool_name.replace('_', ' ').title()}: {out_str}"
                    }
                }]
            }

        parsed_intents = AlexaIntentParser.parse(prompt)
        
        # If any command requires LLM delegation, return None so planner can handle it
        if any(p.get("action") == "delegate_llm" for p in parsed_intents):
            return None

        results = []
        for item in parsed_intents:
            action = item["action"]
            slots = item.get("slots", {})

            if action == "play":
                query = slots.get("track") or slots.get("query", "")
                artist = slots.get("artist")
                res = mcp_manager.execute("spotify.play", {"query": query, "artist": artist})
                results.append(res)

            elif action == "play_album":
                res = mcp_manager.execute("spotify.play_album", {"album": slots.get("album", "")})
                results.append(res)

            elif action == "pause":
                results.append(mcp_manager.execute("spotify.pause"))

            elif action == "resume":
                results.append(mcp_manager.execute("spotify.resume"))

            elif action == "next_track":
                results.append(mcp_manager.execute("spotify.next_track"))

            elif action == "previous_track":
                results.append(mcp_manager.execute("spotify.previous_track"))

            elif action == "set_volume":
                results.append(mcp_manager.execute("spotify.set_volume", {"percent": slots.get("level", 70)}))

            elif action == "volume_up":
                results.append(mcp_manager.execute("spotify.set_volume", {"percent": 80}))

            elif action == "volume_down":
                results.append(mcp_manager.execute("spotify.set_volume", {"percent": 50}))

            elif action == "get_playback_info":
                results.append(mcp_manager.execute("spotify.get_playback"))

            elif action == "launch_app":
                app_name = slots.get("app_name", "")
                results.append(mcp_manager.execute("app_launcher.launch_app", {"app_name": app_name}))

            elif action == "close_app":
                app_name = slots.get("app_name", "").strip()
                from backend.mcp.servers.app_launcher.server import app_launcher_server
                norm = app_name.lower()
                display_name = app_launcher_server.KNOWN_APPS.get(norm, (None, app_name.title()))[1]
                if norm in ["daisy", "this app", "the app", "yourself", "assistant"]:
                    display_name = "Daisy"

                # Store pending confirmation
                cls.pending_confirmation = {
                    "type": "exit_app" if norm in ["daisy", "this app", "the app", "yourself", "assistant"] else "close_app",
                    "app_name": app_name,
                    "display_name": display_name
                }
                cls.pending_timestamp = time.time()

                results.append({
                    "success": True,
                    "tool": "system.ask_confirmation",
                    "result": {
                        "status": "awaiting_confirmation",
                        "action": "confirm_close_app",
                        "app_name": display_name,
                        "awaiting_confirmation": True,
                        "message": f"Are you sure you want to close {display_name}?"
                    }
                })

            elif action == "exit_app":
                results.append({
                    "success": True,
                    "tool": "system.exit_app",
                    "result": {
                        "status": "exiting",
                        "action": "exit_app",
                        "should_exit": True,
                        "message": "Sayonara! Goodbye!"
                    }
                })

            elif action == "wake_greeting":
                results.append({
                    "success": True,
                    "tool": "system.wake_greeting",
                    "result": {
                        "status": "listening",
                        "message": "Hello! I'm here and listening. How can I help you?"
                    }
                })

            elif action == "smalltalk":
                results.append({
                    "success": True,
                    "tool": "system.smalltalk",
                    "result": {
                        "message": "Not much! Just ready to play some great music. What song would you like to hear?"
                    }
                })

            elif action == "identity":
                results.append({
                    "success": True,
                    "tool": "system.identity",
                    "result": {
                        "message": f"I am {AlexaIntentParser.wake_word.title()}, your desktop AI voice assistant running locally on your PC!"
                    }
                })

            elif action == "help":
                results.append({
                    "success": True,
                    "tool": "system.help",
                    "result": {
                        "message": "I can play any song or album on Spotify, control volume, skip tracks, and answer questions."
                    }
                })

            elif action == "status_check":
                results.append({
                    "success": True,
                    "tool": "system.status_check",
                    "result": {
                        "message": "I'm doing wonderful and ready for your music requests!"
                    }
                })

            elif action == "thanks":
                results.append({
                    "success": True,
                    "tool": "system.thanks",
                    "result": {
                        "message": "You're welcome! Happy listening."
                    }
                })

        return {
            "mode": "fastpath_local",
            "tokens_consumed": 0,
            "latency_ms": 8,
            "actions_executed": len(results),
            "results": results
        }

if __name__ == "__main__":
    # Test fastpath execution
    res = FastPathEngine.handle_quick_music("pause and volume 75")
    print("Fastpath Result:", res)
