import logging
from typing import Dict, Any, Optional
from backend.agent.alexa_grammar import AlexaIntentParser
from backend.mcp.manager import mcp_manager

logger = logging.getLogger("daisy.fastpath")

class FastPathEngine:
    """
    Frictionless Fast-Path Policy Engine:
    Ensures simple music playback ("play Starboy", "pause") and direct Q&A
    execute in < 1 second with ZERO deliberation or questionnaire overhead.
    """

    @classmethod
    def handle_quick_music(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to resolve simple music commands immediately via MCP.
        Returns execution result or None if it requires complex reasoning.
        """
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
                app_name = slots.get("app_name", "")
                results.append(mcp_manager.execute("app_launcher.close_app", {"app_name": app_name}))

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
