import os
import re
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from backend.mcp.manager import mcp_manager
from backend.agent.fastpath import FastPathEngine

load_dotenv()
logger = logging.getLogger("daisy.agent.planner")


def normalize_for_voice(text: str) -> str:
    """
    Strip markdown, URLs, code fences, and excessive punctuation from LLM
    responses so the text reads naturally when spoken aloud.
    """
    if not text:
        return text
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Expand symbols
    text = text.replace("%", " percent")
    # Remove markdown emphasis and headers
    text = re.sub(r"[*_#~>]", "", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text)
    # Keep only the first sentence for very long replies (voice should be ≤ 2 sentences)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) > 2:
        text = " ".join(sentences[:2])
    return text.strip()


class DaisyAgenticPlanner:
    """
    Daisy's Agentic Brain:
    1. First checks FastPath (<1s, 0 tokens) for simple music or direct intents.
    2. If complex or semantic, engages Google Gemini 2.5 Flash with MCP tools schema.
    3. Multi-step ReAct planning loop across registered MCP servers.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
        return self._client

    def process(self, user_prompt: str) -> Dict[str, Any]:
        # Step 1: Check FastPath for simple music commands
        fast_result = FastPathEngine.handle_quick_music(user_prompt)
        if fast_result is not None:
            spoken_reply = "Done."
            results = fast_result.get("results", [])
            if results:
                first = results[0]
                if not first.get("success"):
                    spoken_reply = first.get("error") or "Sorry, I couldn't do that."
                else:
                    res_data = first.get("result", {})
                    if isinstance(res_data, dict):
                        if res_data.get("error"):
                            spoken_reply = res_data["error"]
                        elif res_data.get("status") == "playing" and res_data.get("track"):
                            track = res_data["track"]
                            artist = res_data.get("artist", "")
                            spoken_reply = f"Sure, playing {track}." if not artist else f"Playing {track} by {artist}."
                        elif res_data.get("track"):
                            track = res_data["track"]
                            artist = res_data.get("artist", "")
                            is_playing = res_data.get("is_playing", False)
                            if is_playing:
                                spoken_reply = f"Playing {track}." if not artist else f"Playing {track} by {artist}."
                            else:
                                spoken_reply = f"Paused on {track}." if not artist else f"Paused on {track} by {artist}."
                        elif res_data.get("status") == "awaiting_confirmation":
                            spoken_reply = f"Are you sure you want to close {res_data.get('app_name', 'this app')}?"
                        elif res_data.get("status") == "exiting" or res_data.get("action") == "exit_app":
                            spoken_reply = "Sayonara! Goodbye!"
                        elif res_data.get("status") == "paused":
                            spoken_reply = "Paused."
                        elif res_data.get("status") == "resumed":
                            spoken_reply = "Resumed."
                        elif res_data.get("status") in ("no_playback", "no_active_device", "offline"):
                            spoken_reply = "Nothing is playing right now."
                        elif "volume" in res_data:
                            spoken_reply = f"Volume set to {res_data['volume']} percent."
                        elif res_data.get("message"):
                            spoken_reply = normalize_for_voice(res_data["message"])

            should_exit = any(
                isinstance(r.get("result"), dict) and (r.get("result", {}).get("should_exit") or r.get("result", {}).get("action") == "exit_app")
                for r in results
            )
            awaiting_confirmation = any(
                isinstance(r.get("result"), dict) and r.get("result", {}).get("awaiting_confirmation")
                for r in results
            )
            return {
                "source": "FASTPATH_LOCAL",
                "tokens": 0,
                "spoken_reply": spoken_reply,
                "should_exit": should_exit,
                "awaiting_confirmation": awaiting_confirmation,
                "details": fast_result
            }

        # Step 2: Agentic LLM reasoning via Google Gemini
        if not self.api_key:
            return {
                "source": "LOCAL_ASSISTANT",
                "tokens": 0,
                "spoken_reply": "I'm here! Ask me to play a song, pause, skip, or change the volume.",
                "details": {"mode": "local_fallback", "prompt": user_prompt}
            }


        try:
            from google.genai import types

            client = self._get_client()
            if not client:
                raise RuntimeError("Gemini client not initialized")
            tools_schema = mcp_manager.get_all_tools_schema()

            # Build Gemini Function Declarations
            func_decls = []
            for t in tools_schema:
                params_obj = t.get("parameters", {})
                props = {}
                for p_name, p_def in params_obj.get("properties", {}).items():
                    p_type = p_def.get("type", "string").upper()
                    if p_type == "STRING":
                        schema_type = types.Type.STRING
                    elif p_type in ("INTEGER", "INT"):
                        schema_type = types.Type.INTEGER
                    elif p_type in ("NUMBER", "FLOAT"):
                        schema_type = types.Type.NUMBER
                    elif p_type in ("BOOLEAN", "BOOL"):
                        schema_type = types.Type.BOOLEAN
                    else:
                        schema_type = types.Type.STRING

                    props[p_name] = types.Schema(
                        type=schema_type,
                        description=p_def.get("description", "")
                    )

                decl = types.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=props,
                        required=params_obj.get("required", [])
                    )
                )
                func_decls.append(decl)

            gemini_tools = [types.Tool(function_declarations=func_decls)] if func_decls else None

            system_instruction = (
                "You are Daisy, a snappy desktop voice assistant. "
                "You control Spotify, launch Windows apps, and use MCP tools. "
                "CRITICAL: Your spoken reply must be ONE short sentence, under 15 words, "
                "conversational and casual — like Alexa or Siri. "
                "No markdown, no lists, no code, no URLs. "
                "Examples: 'Sure, playing Starboy.' / 'Paused.' / 'Volume set to 60.' / "
                "'Opening Chrome now.' / 'Got it, skipping ahead.' "
                "Execute the right tool calls when needed."
            )

            # Generate content with MCP tool calling enabled
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    tools=gemini_tools
                )
            )

            # Check if model requested tool calls
            executed_tools = []
            if hasattr(response, "function_calls") and response.function_calls:
                for call in response.function_calls:
                    call_name = call.name
                    call_args = dict(call.args) if call.args else {}
                    logger.info(f"Gemini planner executing tool: {call_name} with args {call_args}")
                    exec_result = mcp_manager.execute(call_name, call_args)
                    executed_tools.append({
                        "name": call_name,
                        "args": call_args,
                        "result": exec_result
                    })

            # Formulate spoken reply — always normalized for voice output
            spoken_text = ""
            if hasattr(response, "text") and response.text:
                spoken_text = normalize_for_voice(response.text.strip())
            elif executed_tools:
                # Provide natural speech confirmation based on executed tool
                first_exec = executed_tools[0]
                tool_res = first_exec.get("result", {})
                res_data = tool_res.get("result", {}) if isinstance(tool_res.get("result"), dict) else {}
                if "track" in res_data and res_data.get("status") == "playing":
                    track = res_data["track"]
                    artist = res_data.get("artist", "")
                    spoken_text = f"Sure, playing {track}." if not artist else f"Playing {track} by {artist}."
                elif "message" in res_data:
                    spoken_text = normalize_for_voice(res_data["message"])
                elif "output" in res_data:
                    spoken_text = normalize_for_voice(str(res_data["output"]))
                else:
                    name = first_exec["name"].replace("_", " ")
                    spoken_text = f"Done."
            else:
                spoken_text = "Done."

            return {
                "source": "GEMINI_AGENTIC",
                "tokens": 120,
                "spoken_reply": spoken_text,
                "details": {
                    "gemini_output": spoken_text,
                    "tools_executed": executed_tools
                }
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
