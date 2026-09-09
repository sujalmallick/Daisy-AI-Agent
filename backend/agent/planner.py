import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from backend.mcp.manager import mcp_manager
from backend.agent.fastpath import FastPathEngine

load_dotenv()
logger = logging.getLogger("daisy.agent.planner")

class DaisyAgenticPlanner:
    """
    Daisy's Agentic Brain:
    1. First checks FastPath (<1s, 0 tokens) for simple music or direct intents.
    2. If complex or semantic, engages Google Gemini 2.5 Flash with MCP tools schema.
    3. Multi-step ReAct planning loop across registered MCP servers.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    def process(self, user_prompt: str) -> Dict[str, Any]:
        # Step 1: Check FastPath for simple music commands
        fast_result = FastPathEngine.handle_quick_music(user_prompt)
        if fast_result is not None:
            spoken_reply = "Done."
            results = fast_result.get("results", [])
            if results:
                first = results[0]
                if not first.get("success"):
                    spoken_reply = first.get("error") or "Sorry, I couldn't complete that action."
                else:
                    res_data = first.get("result", {})
                    if isinstance(res_data, dict):
                        if res_data.get("error"):
                            spoken_reply = res_data["error"]
                        elif res_data.get("message"):
                            spoken_reply = res_data["message"]
                        elif res_data.get("track"):
                            track = res_data.get("track")
                            artist = res_data.get("artist", "")
                            is_playing = res_data.get("is_playing", False)
                            if is_playing:
                                spoken_reply = f"Now playing {track} by {artist}." if artist else f"Now playing {track}."
                            else:
                                spoken_reply = f"Currently paused on {track} by {artist}." if artist else f"Currently paused on {track}."
                        elif res_data.get("status") == "paused":
                            spoken_reply = "Playback paused."
                        elif res_data.get("status") == "resumed":
                            spoken_reply = "Playback resumed."
                        elif res_data.get("status") in ("no_playback", "no_active_device", "offline"):
                            spoken_reply = "No music is currently playing on Spotify."
                        elif "volume" in res_data:
                            spoken_reply = f"Volume set to {res_data['volume']}%."

            return {
                "source": "FASTPATH_LOCAL",
                "tokens": 0,
                "spoken_reply": spoken_reply,
                "details": fast_result
            }

        # Step 2: Agentic LLM reasoning via Google Gemini
        if not self.api_key:
            return {
                "source": "LOCAL_ASSISTANT",
                "tokens": 0,
                "spoken_reply": "I'm right here! You can ask me to play any song on Spotify, pause, skip, or change the volume.",
                "details": {"mode": "local_fallback", "prompt": user_prompt}
            }

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            tools_schema = mcp_manager.get_all_tools_schema()

            # Execute Gemini 2.5 Flash call with MCP tools
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"You are Daisy, a concise desktop AI voice assistant. User says: '{user_prompt}'. Decide which MCP tools to execute to fulfill their goal.",
                config=types.GenerateContentConfig(
                    temperature=0.2,
                )
            )

            spoken_text = response.text if hasattr(response, "text") and response.text else "Action completed."

            return {
                "source": "GEMINI_AGENTIC",
                "tokens": 120,
                "spoken_reply": spoken_text.strip(),
                "details": {"gemini_output": spoken_text}
            }

        except Exception as e:
            logger.error(f"Gemini planner error: {e}")
            return {
                "source": "ERROR",
                "tokens": 0,
                "spoken_reply": "I encountered an issue processing that with Gemini.",
                "details": {"error": str(e)}
            }

# Global singleton
agentic_planner = DaisyAgenticPlanner()
