import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import html
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from backend.hardware import detect_hardware_tier
from backend.agent.planner import agentic_planner
from datetime import datetime
from backend.voice.tts_engine import TTSEngine
from backend.voice.tts_manager import tts_manager

# In-Memory Live Logs Buffer
LOG_BUFFER = []

class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            LOG_BUFFER.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage()
            })
            if len(LOG_BUFFER) > 300:
                LOG_BUFFER.pop(0)
        except Exception:
            pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
mem_handler = MemoryLogHandler()
mem_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(mem_handler)

logger = logging.getLogger("daisy.api")

app = FastAPI(title="Daisy AI Voice Assistant Engine", version="0.1.0")

# Restrict CORS to local application origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Mount desktop production frontend if it exists
DIST_DIR = os.path.join(PROJECT_ROOT, "desktop", "dist")
if os.path.exists(DIST_DIR):
    app.mount("/app", StaticFiles(directory=DIST_DIR, html=True), name="app")

class CommandRequest(BaseModel):
    prompt: str
    speak_backend: bool = True
    assistant_name: Optional[str] = None

class AssistantConfigRequest(BaseModel):
    name: str

@app.get("/config/assistant")
def get_assistant_config():
    from backend.agent.alexa_grammar import AlexaIntentParser
    return {"name": AlexaIntentParser.wake_word.title()}

@app.post("/config/assistant")
def set_assistant_config(req: AssistantConfigRequest):
    from backend.agent.alexa_grammar import AlexaIntentParser
    if req.name and req.name.strip():
        AlexaIntentParser.set_wake_word(req.name.strip())
    return {"name": AlexaIntentParser.wake_word.title(), "status": "updated"}

@app.get("/")
def health_check():
    hw = detect_hardware_tier()
    from backend.agent.alexa_grammar import AlexaIntentParser
    return {
        "status": "online",
        "assistant": AlexaIntentParser.wake_word.title(),
        "hardware_tier": hw["tier_name"],
        "device": hw["device"],
        "gpu_name": hw.get("gpu_name")
    }

@app.post("/command")
async def handle_command(req: CommandRequest):
    """
    Main dispatch endpoint for voice & text commands:
    1. FastPath for simple music (<1s, 0 tokens)
    2. Gemini Agentic Planner for complex goals
    3. Speaks aloud via TTS
    """
    prompt = req.prompt.strip()
    if not prompt:
        return {"error": "Empty prompt received."}

    if req.assistant_name:
        from backend.agent.alexa_grammar import AlexaIntentParser
        AlexaIntentParser.set_wake_word(req.assistant_name)

    logger.info(f"Processing command: '{prompt}'")
    try:
        result = agentic_planner.process(prompt)
    except Exception as e:
        logger.error(f"Error processing command '{prompt}': {e}", exc_info=True)
        return {
            "source": "error_handler",
            "spoken_reply": "I ran into an issue while processing that. Please try again.",
            "error": str(e),
            "status": "failed"
        }

    # Trigger spoken voice response (TTS) asynchronously if enabled
    spoken = result.get("spoken_reply")
    if req.speak_backend and spoken and spoken != "Done.":
        TTSEngine.speak(spoken)

    return result

@app.get("/devices")
def list_devices():
    from backend.mcp.servers.spotify.server import spotify_server
    if spotify_server.sp:
        try:
            return spotify_server.sp.devices()
        except Exception as e:
            return {"error": str(e)}
    return {"devices": []}

class PlaybackActionRequest(BaseModel):
    action: str
    value: Optional[Any] = None

@app.get("/playback")
def current_playback():
    from backend.mcp.manager import mcp_manager
    return mcp_manager.execute("spotify.get_playback")

@app.post("/playback/action")
def execute_playback_action(req: PlaybackActionRequest):
    from backend.mcp.manager import mcp_manager
    act = req.action.lower()
    if act in ("pause", "stop"):
        return mcp_manager.execute("spotify.pause")
    elif act in ("play", "resume"):
        return mcp_manager.execute("spotify.resume")
    elif act in ("next", "skip"):
        return mcp_manager.execute("spotify.next_track")
    elif act in ("previous", "prev"):
        return mcp_manager.execute("spotify.previous_track")
    elif act == "volume":
        vol = int(req.value) if req.value is not None else 70
        return mcp_manager.execute("spotify.set_volume", {"percent": vol})
    return {"error": f"Unknown playback action '{req.action}'"}

@app.get("/auth/status")
def auth_status():
    from backend.mcp.servers.spotify.server import spotify_server
    return {
        "spotify_connected": spotify_server.is_authenticated()
    }

@app.get("/logs")
def get_logs():
    return {"logs": list(reversed(LOG_BUFFER))}

@app.delete("/logs")
def clear_logs():
    LOG_BUFFER.clear()
    return {"status": "cleared"}

@app.get("/system/status")
def get_system_status():
    from backend.mcp.servers.spotify.server import spotify_server
    from backend.mcp.manager import mcp_manager
    hw = detect_hardware_tier()
    return {
        "status": "online",
        "hardware": hw,
        "spotify_connected": spotify_server.is_authenticated(),
        "registered_servers": list(mcp_manager._servers.keys()),
        "tools_count": len(mcp_manager._tools),
        "tools": mcp_manager.get_all_tools_schema()
    }


# ── Voice / TTS Endpoints ─────────────────────────────────────────────────────

class VoiceConfigUpdateRequest(BaseModel):
    provider: Optional[str] = None   # "edge-tts" | "windows-tts" | "disabled"
    voice: Optional[str] = None      # Edge-TTS voice name
    windows_voice: Optional[str] = None  # Windows SAPI voice name
    rate: Optional[float] = None
    pitch: Optional[float] = None

@app.get("/voice/config")
def get_voice_config():
    """Return current voice configuration and available voice options."""
    return tts_manager.get_config()

@app.post("/voice/config")
def update_voice_config(req: VoiceConfigUpdateRequest):
    """Update and persist voice configuration."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    config = tts_manager.update_config(updates)
    logger.info(f"[Voice] Config updated: {updates}")
    return {"status": "ok", **config}

@app.get("/voice/voices")
def list_voices():
    """List all available voices grouped by provider."""
    cfg = tts_manager.get_config()
    return {
        "edge_voices": cfg.get("edge_voices", []),
        "windows_voices": cfg.get("windows_voices", []),
    }

@app.get("/voice/synthesize")
def synthesize_voice(text: str):
    """
    Synthesize text to audio bytes and stream to frontend.
    Used by the TTSClient in the browser to play Daisy's voice.
    Returns MP3 (Edge-TTS) or WAV (Windows TTS).
    """
    from fastapi.responses import Response
    if not text or not text.strip():
        return Response(status_code=204)

    result = tts_manager.synthesize_to_bytes(text.strip())
    if result is None:
        # Provider is disabled or synthesis failed
        return Response(status_code=204)

    audio_bytes, mime = result
    return Response(
        content=audio_bytes,
        media_type=mime,
        headers={
            "Cache-Control": "no-cache",
            "Content-Length": str(len(audio_bytes)),
        }
    )

@app.post("/voice/test")
def test_voice():
    """Trigger a test phrase via the active TTS provider (plays on server speakers)."""
    test_phrase = "Daisy voice engine is online and working."
    tts_manager.speak(test_phrase)
    return {"spoken": test_phrase, "status": "dispatched", "provider": tts_manager.provider}

@app.post("/voice/stop")
def stop_voice():
    """Immediately stop any active TTS playback (called during barge-in)."""
    tts_manager.stop()
    return {"status": "stopped"}

@app.post("/system/exit")
def exit_system():
    """Terminates Daisy backend and host process cleanly after farewell speech."""
    import time
    logger.info("Shutdown requested via voice/system. Exiting Daisy...")
    def _delayed_exit():
        time.sleep(1.8)
        os._exit(0)
    threading.Thread(target=_delayed_exit, daemon=True).start()
    return {"status": "exiting", "message": "Sayonara! Goodbye!"}



# --- Custom MCP & Tools Endpoints ---
class CustomToolCreateRequest(BaseModel):
    name: str
    description: str = ""
    type: str = "command" # 'command' or 'http'
    command: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = "GET"
    headers: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    trigger_phrases: Optional[List[str]] = None
    timeout: Optional[int] = 15
    enabled: bool = True

class CustomToolTestRequest(BaseModel):
    name: str
    args: Optional[Dict[str, Any]] = None

class OpenBrowserRequest(BaseModel):
    url: str

@app.get("/mcp/custom")
def get_custom_tools():
    from backend.mcp.custom_loader import custom_tool_manager
    return {"tools": custom_tool_manager.get_tools()}

@app.post("/mcp/custom")
def add_custom_tool(req: CustomToolCreateRequest):
    from backend.mcp.custom_loader import custom_tool_manager
    try:
        saved = custom_tool_manager.add_or_update_tool(req.model_dump())
        return {"status": "success", "tool": saved}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/mcp/custom/{tool_name}")
def delete_custom_tool(tool_name: str):
    from backend.mcp.custom_loader import custom_tool_manager
    deleted = custom_tool_manager.delete_tool(tool_name)
    return {"status": "deleted" if deleted else "not_found", "tool": tool_name}

@app.post("/mcp/custom/test")
def test_custom_tool(req: CustomToolTestRequest):
    from backend.mcp.custom_loader import custom_tool_manager
    res = custom_tool_manager.test_tool(req.name, req.args or {})
    return res

@app.post("/system/open-browser")
def open_system_browser(req: OpenBrowserRequest):
    import webbrowser
    success = webbrowser.open(req.url)
    return {"status": "launched" if success else "dispatched", "url": req.url}

@app.get("/auth/spotify")
def auth_spotify():
    from fastapi.responses import RedirectResponse
    from backend.mcp.servers.spotify.server import spotify_server
    if spotify_server.auth_manager:
        url = spotify_server.auth_manager.get_authorize_url()
        return RedirectResponse(url)
    return {"error": "Spotify credentials not set in .env"}

@app.get("/callback")
def auth_callback(code: str = None, error: str = None):
    from fastapi.responses import HTMLResponse
    from spotipy import Spotify
    from backend.mcp.servers.spotify.server import spotify_server

    if error:
        safe_error = html.escape(error)
        return HTMLResponse(f"<h3 style='color:red;'>Spotify Auth Failed: {safe_error}</h3>")
    if code and spotify_server.auth_manager:
        try:
            spotify_server.auth_manager.get_access_token(code, as_dict=True)
            spotify_server.sp = Spotify(auth_manager=spotify_server.auth_manager)
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
              <head><title>Daisy Spotify Auth</title></head>
              <body style="background:#07090e;color:#10b981;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
                <div style="text-align:center;padding:2rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);border-radius:1rem;">
                  <h1 style="margin:0 0 0.5rem 0;">Daisy Connected to Spotify!</h1>
                  <p style="color:#a1a1aa;margin:0;">Authentication was successful. You can now close this tab and return to Daisy.</p>
                </div>
              </body>
            </html>
            """)
        except Exception as e:
            safe_e = html.escape(str(e))
            return HTMLResponse(f"<h3 style='color:red;'>Error saving token: {safe_e}</h3>")
    return HTMLResponse("<h3>Missing code parameter</h3>")

# Port 5000 listener for Spotify Redirect URI configured at http://127.0.0.1:5000/callback
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

class SpotifyPort5000Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return # Quiet console

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            if code:
                try:
                    from spotipy import Spotify
                    from backend.mcp.servers.spotify.server import spotify_server
                    if spotify_server.auth_manager:
                        spotify_server.auth_manager.get_access_token(code, as_dict=True)
                        spotify_server.sp = Spotify(auth_manager=spotify_server.auth_manager)
                    
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    success_html = """
                    <!DOCTYPE html>
                    <html>
                      <body style="background:#07090e;color:#10b981;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
                        <div style="text-align:center;padding:2rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);border-radius:1rem;">
                          <h1 style="margin:0 0 0.5rem 0;">Daisy Connected to Spotify!</h1>
                          <p style="color:#a1a1aa;margin:0;">Authentication was successful! You can now close this tab and return to Daisy.</p>
                        </div>
                      </body>
                    </html>
                    """
                    self.wfile.write(success_html.encode("utf-8"))
                    return
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    safe_err = html.escape(str(e))
                    self.wfile.write(f"<h3>Auth token error: {safe_err}</h3>".encode("utf-8"))
                    return

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No auth code received.")
        else:
            self.send_response(404)
            self.end_headers()

def _run_port_5000_listener():
    try:
        server = HTTPServer(('127.0.0.1', 5000), SpotifyPort5000Handler)
        server.serve_forever()
    except Exception as e:
        logger.debug(f"Port 5000 helper notice: {e}")

threading.Thread(target=_run_port_5000_listener, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
