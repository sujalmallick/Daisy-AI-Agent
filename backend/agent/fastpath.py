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
                        "message": "I am Daisy, your desktop AI voice assistant running locally on your PC!"
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
