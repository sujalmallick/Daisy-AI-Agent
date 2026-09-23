import os
import random
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("daisy.mcp.spotify")

class SpotifyMCPServer:
    """
    Built-in Spotify MCP Server.
    Provides robust, edge-case resilient Spotify tools:
      - Automatic active device discovery & transfer
      - Token refresh recovery
      - Graceful Premium 403 handling
    """

    def __init__(self):
        self.sp = None
        self.auth_manager = None
        self._last_network_error_time = 0
        self._saved_pre_duck_volume = None
        self._init_client()

    def _init_client(self):
        try:
            from spotipy import Spotify, SpotifyOAuth
            client_id = os.getenv("SPOTIPY_CLIENT_ID")
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
            redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

            # Suppress noisy transient urllib3 retry warnings
            logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

            if client_id and client_secret:
                self.auth_manager = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope="user-modify-playback-state user-read-playback-state",
                    open_browser=True
                )
                self.sp = Spotify(
                    auth_manager=self.auth_manager,
                    requests_timeout=10,
                    retries=1
                )
                logger.info("Spotify MCP Server successfully configured.")
            else:
                logger.warning("SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET not set in environment.")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")

    def _dispatch_media_key(self, key_code: int) -> bool:
        """Dispatches Windows hardware media key directly to local Spotify desktop."""
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)
                logger.info(f"[Spotify] Dispatched Windows hardware media key {hex(key_code)}")
                return True
            except Exception as e:
                logger.debug(f"[Spotify] Media key dispatch note: {e}")
        return False

    def _ensure_active_device(self) -> Optional[str]:
        """
        Finds the target Spotify device for playback.
        Prioritizes the local Computer/Desktop client so audio plays on PC speakers
        rather than external phones or smart speakers in other rooms.
        """
        if not self.sp:
            return None
        try:
            devices = self.sp.devices().get("devices", [])

            # Priority 1: Any local Computer / Desktop device (active or idle)
            computer_dev = next((d for d in devices if d.get("type") in ("Computer", "Desktop")), None)
            if computer_dev:
                return computer_dev["id"]

            # Priority 2: Any currently active device (smart speaker, phone, etc.)
            active_dev = next((d for d in devices if d.get("is_active")), None)
            if active_dev:
                return active_dev["id"]

            return devices[0]["id"] if devices else None
        except Exception as e:
            logger.warning(f"Could not find active Spotify device: {e}")
            return None

    def get_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool definitions."""
        return [
            {
                "name": "play",
                "description": "Searches for and plays a song, artist, or query on Spotify.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Song name or search term"},
                        "artist": {"type": "string", "description": "Optional artist name"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "play_album",
                "description": "Searches for and plays an entire album on Spotify.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "album": {"type": "string", "description": "Album title"}
                    },
                    "required": ["album"]
                }
            },
            {
                "name": "pause",
                "description": "Pauses the currently playing track on Spotify.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "resume",
                "description": "Resumes paused music playback on Spotify.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "next_track",
                "description": "Skips to the next track in the Spotify playback queue.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "previous_track",
                "description": "Returns to the previous track on Spotify.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "set_volume",
                "description": "Sets playback volume percentage from 0 to 100.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "percent": {"type": "integer", "description": "Volume level between 0 and 100"}
                    },
                    "required": ["percent"]
                }
            },
            {
                "name": "get_playback",
                "description": "Returns current playback status, track title, artist, album art, and progress.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "set_shuffle",
                "description": "Turns Spotify shuffle on, off, or toggles its current state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "on, off, or toggle"}
                    },
                    "required": ["state"]
                }
            },
            {
                "name": "set_repeat",
                "description": "Sets Spotify repeat to off, context, track, or toggles its current state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "off, context, track, or toggle"}
                    },
                    "required": ["state"]
                }
            },
            {
                "name": "recommend_vibes",
                "description": "Starts a curated vibe session with recommended tracks based on mood or genre.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "genres": {"type": "array", "items": {"type": "string"}, "description": "List of seed genres e.g. ['pop', 'synthwave']"},
                        "mood": {"type": "string", "description": "Mood description e.g. 'late night', 'chill', 'workout'"}
                    }
                }
            },
            {
                "name": "duck",
                "description": "Temporarily ducks Spotify playback volume to allow clean voice listening.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "percent": {"type": "integer", "description": "Target ducked volume level (default 18)"}
                    }
                }
            },
            {
                "name": "unduck",
                "description": "Restores Spotify playback volume back to the pre-duck level.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def is_authenticated(self) -> bool:
        if not self.auth_manager:
            return False
        try:
            token = self.auth_manager.get_cached_token()
            if not token:
                return False
            # Check if token is expired and needs refresh
            if self.auth_manager.is_token_expired(token):
                try:
                    new_token = self.auth_manager.refresh_access_token(token["refresh_token"])
                    return bool(new_token)
                except Exception:
                    return False
            return True
        except Exception:
            return False

    def duck_volume(self, target_percent: int = 18) -> Dict[str, Any]:
        """Temporarily drops Spotify playback volume to allow clean voice transcription."""
        if not self.sp or not self.is_authenticated():
            return {"status": "skipped", "message": "Spotify not active"}
        try:
            pb = self.sp.current_playback()
            if not pb or not pb.get("is_playing"):
                return {"status": "not_playing"}
            device = pb.get("device") or {}
            curr = device.get("volume_percent")
            if curr is not None and self._saved_pre_duck_volume is None:
                self._saved_pre_duck_volume = curr
            dev_id = device.get("id") or self._ensure_active_device()
            self.sp.volume(max(0, min(100, target_percent)), device_id=dev_id)
            return {
                "status": "ducked",
                "ducked_to": target_percent,
                "previous_volume": self._saved_pre_duck_volume
            }
        except Exception as e:
            logger.debug(f"Duck volume exception: {e}")
            return {"status": "error", "message": str(e)}

    def unduck_volume(self) -> Dict[str, Any]:
        """Restores Spotify volume to the pre-duck level."""
        if not self.sp or not self.is_authenticated():
            return {"status": "skipped", "message": "Spotify not active"}
        if self._saved_pre_duck_volume is None:
            return {"status": "not_ducked"}
        target_vol = self._saved_pre_duck_volume
        self._saved_pre_duck_volume = None
        try:
            pb = self.sp.current_playback()
            if pb:
                device = pb.get("device") or {}
                dev_id = device.get("id") or self._ensure_active_device()
                self.sp.volume(target_vol, device_id=dev_id)
            return {"status": "unducked", "restored_volume": target_vol}
        except Exception as e:
            logger.debug(f"Unduck volume exception: {e}")
            return {"status": "error", "message": str(e)}

    def execute_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Any:
        args = args or {}
        if not self.sp:
            return {"error": "Spotify client not initialized. Check your credentials in .env."}

        if not self.is_authenticated():
            return {
                "error": "Spotify account is not connected yet. Please click Connect Spotify in Settings.",
                "auth_required": True,
                "auth_url": "http://127.0.0.1:8000/auth/spotify"
            }
        # Ensure active device is resolved for all playback controls
        target_device_id = None
        if tool_name in ("play", "play_album", "resume", "next_track", "previous_track", "pause", "set_volume", "set_shuffle", "set_repeat", "recommend_vibes"):
            target_device_id = self._ensure_active_device()

        try:
            if tool_name == "play":
                q = args.get("query", "")
                if args.get("artist"):
                    q += f" artist:{args['artist']}"
                results = self.sp.search(q=q, type="track", limit=1)
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track = tracks[0]
                    track_uri = track.get("uri", "")

                    # Pure Spotify Connect Web API playback (background streaming without opening the desktop GUI app)
                    try:
                        if target_device_id:
                            try:
                                self.sp.transfer_playback(device_id=target_device_id, force_play=True)
                            except Exception:
                                pass
                        self.sp.start_playback(device_id=target_device_id, uris=[track_uri])
                    except Exception as web_err:
                        logger.debug(f"Web API playback note: {web_err}")
                        import sys
                        if sys.platform == "win32":
                            self._dispatch_media_key(0xB3)  # Fallback to local media key only if Web API fails

                    return {
                        "status": "playing",
                        "track": track["name"],
                        "artist": track["artists"][0]["name"],
                        "message": f"Now playing: {track['name']} by {track['artists'][0]['name']}"
                    }
                return {"error": f"Couldn't find any track matching '{q}'."}

            elif tool_name == "play_album":
                album = args.get("album", "")
                res = self.sp.search(q=album, type="album", limit=1)
                items = res.get("albums", {}).get("items", [])
                if items:
                    alb = items[0]
                    alb_uri = alb.get("uri", "")

                    try:
                        if target_device_id:
                            try:
                                self.sp.transfer_playback(device_id=target_device_id, force_play=True)
                            except Exception:
                                pass
                        self.sp.start_playback(device_id=target_device_id, context_uri=alb_uri)
                    except Exception as web_err:
                        logger.debug(f"Web API album playback note: {web_err}")
                        import sys
                        if sys.platform == "win32":
                            self._dispatch_media_key(0xB3)

                    return {"status": "playing_album", "album": alb["name"], "message": f"Playing album: {alb['name']}"}
                return {"error": f"Album '{album}' not found."}

            elif tool_name == "pause":
                paused = False
                try:
                    self.sp.pause_playback(device_id=target_device_id)
                    paused = True
                except Exception as pause_err:
                    logger.debug(f"Web API pause notice: {pause_err}. Falling back to Windows media key.")

                if not paused:
                    self._dispatch_media_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
                return {"status": "paused", "message": "Playback paused."}

            elif tool_name == "resume":
                resumed = False
                try:
                    self.sp.start_playback(device_id=target_device_id)
                    resumed = True
                except Exception as resume_err:
                    logger.debug(f"Web API resume notice: {resume_err}. Falling back to Windows media key.")

                if not resumed:
                    self._dispatch_media_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
                    try:
                        import subprocess
                        subprocess.Popen(["cmd", "/c", "start", "", "spotify:"], shell=True)
                    except Exception:
                        pass

                    # If Spotify has no track loaded in queue at all, auto-play popular music
                    try:
                        pb = self.sp.current_playback()
                        if not pb or not pb.get("item"):
                            return self.execute_tool("play", {"query": "top hits"})
                    except Exception:
                        pass
                return {"status": "resumed", "message": "Playback resumed."}

            elif tool_name == "next_track":
                skipped = False
                try:
                    self.sp.next_track(device_id=target_device_id)
                    skipped = True
                except Exception as next_err:
                    logger.debug(f"Web API next notice: {next_err}. Falling back to Windows media key.")

                if not skipped:
                    self._dispatch_media_key(0xB0)  # VK_MEDIA_NEXT_TRACK
                return {"status": "skipped", "message": "Skipped to next track."}

            elif tool_name == "previous_track":
                prev_ok = False
                try:
                    self.sp.previous_track(device_id=target_device_id)
                    prev_ok = True
                except Exception as prev_err:
                    logger.debug(f"Web API previous notice: {prev_err}. Falling back to Windows media key.")

                if not prev_ok:
                    self._dispatch_media_key(0xB1)  # VK_MEDIA_PREV_TRACK
                return {"status": "previous", "message": "Returning to previous track."}

            elif tool_name == "set_volume":
                vol = max(0, min(100, int(args.get("percent", 70))))
                self.sp.volume(vol, device_id=target_device_id)
                return {"status": "volume_adjusted", "volume": vol, "message": f"Volume set to {vol}%."}

            elif tool_name == "set_shuffle":
                state = str(args.get("state", "toggle")).lower()
                if state == "toggle":
                    current = self.sp.current_playback() or {}
                    state = "off" if current.get("shuffle_state") else "on"
                enabled = state == "on"
                self.sp.shuffle(enabled, device_id=target_device_id)
                return {"status": "shuffle_updated", "shuffle_state": enabled, "message": f"Shuffle {'on' if enabled else 'off'}."}

            elif tool_name == "set_repeat":
                state = str(args.get("state", "toggle")).lower()
                if state == "toggle":
                    current = self.sp.current_playback() or {}
                    state = "off" if current.get("repeat_state", "off") != "off" else "context"
                if state not in ("off", "context", "track"):
                    return {"error": "Repeat state must be off, context, track, or toggle."}
                self.sp.repeat(state, device_id=target_device_id)
                return {"status": "repeat_updated", "repeat_state": state, "message": f"Repeat {state}."}

            elif tool_name == "get_playback":
                import time
                if time.time() - self._last_network_error_time < 5.0:
                    return {
                        "is_playing": False,
                        "message": "Spotify unreachable (reconnecting...)",
                        "device_name": "Offline",
                        "volume_percent": 50
                    }

                try:
                    pb = self.sp.current_playback()
                except Exception as net_err:
                    self._last_network_error_time = time.time()
                    logger.debug(f"get_playback transient error: {net_err}")
                    return {
                        "is_playing": False,
                        "message": "Network temporarily unreachable",
                        "device_name": "Offline",
                        "volume_percent": 50
                    }

                if pb and pb.get("item"):
                    item = pb["item"]
                    dev = pb.get("device") or {}
                    artists = ", ".join(a["name"] for a in item.get("artists", [])) or item["artists"][0]["name"]
                    return {
                        "is_playing": pb.get("is_playing", False),
                        "track": item["name"],
                        "artist": artists,
                        "album": item["album"]["name"],
                        "progress_ms": pb.get("progress_ms", 0),
                        "duration_ms": item.get("duration_ms", 0),
                        "artwork_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
                        "device_name": dev.get("name", "Spotify Device"),
                        "device_type": dev.get("type", "Speaker"),
                        "volume_percent": dev.get("volume_percent", 70),
                        "shuffle_state": pb.get("shuffle_state", False),
                        "repeat_state": pb.get("repeat_state", "off")
                    }
                try:
                    devices = self.sp.devices().get("devices", []) if self.sp else []
                except Exception:
                    devices = []
                active_dev = next((d for d in devices if d.get("is_active")), devices[0] if devices else None)
                return {
                    "is_playing": False,
                    "message": "No active playback.",
                    "device_name": active_dev.get("name") if active_dev else "No Device Connected",
                    "volume_percent": active_dev.get("volume_percent", 50) if active_dev else 50
                }

            elif tool_name == "recommend_vibes":
                genres = args.get("genres") or ["pop", "rock", "indie", "electronic", "lo-fi"]
                chosen = random.sample(genres, min(2, len(genres)))
                recs = self.sp.recommendations(seed_genres=chosen, limit=20)
                uris = [t["uri"] for t in recs["tracks"]]

                import sys
                if sys.platform == "win32" and uris:
                    try:
                        import subprocess
                        subprocess.Popen(["cmd", "/c", "start", "", f"{uris[0]}:play"], shell=True)
                    except Exception:
                        pass

                try:
                    if target_device_id:
                        try:
                            self.sp.transfer_playback(device_id=target_device_id, force_play=True)
                        except Exception:
                            pass
                    self.sp.start_playback(device_id=target_device_id, uris=uris)
                except Exception as web_err:
                    logger.debug(f"Web API vibe playback note: {web_err}")

                if sys.platform == "win32":
                    self._dispatch_media_key(0xB3)

                return {
                    "status": "vibe_started",
                    "seeds": chosen,
                    "count": len(uris),
                    "message": f"Started vibe session with {len(uris)} recommended tracks."
                }

            elif tool_name == "duck":
                target = int(args.get("percent", 18))
                return self.duck_volume(target_percent=target)

            elif tool_name == "unduck":
                return self.unduck_volume()

        except Exception as e:
            import time
            self._last_network_error_time = time.time()
            err_str = str(e)
            if "10051" in err_str or "10013" in err_str or "timed out" in err_str.lower() or "unreachable" in err_str.lower() or "connection" in err_str.lower():
                return {"error": "Spotify server unreachable (network issue). Please check your internet connection."}
            elif "invalid_grant" in err_str or "expired" in err_str.lower():
                return {"error": "Spotify authorization required. Please visit http://127.0.0.1:8000/auth/spotify to connect your account."}
            elif "PREMIUM_REQUIRED" in err_str or "403" in err_str:
                return {"error": "Spotify Premium is required for direct Web API playback control."}
            elif "NO_ACTIVE_DEVICE" in err_str or "404" in err_str:
                return {"error": "No active Spotify device found. Please open Spotify on your PC."}
            return {"error": f"Spotify action failed: {err_str}"}

        return {"error": f"Unknown Spotify tool '{tool_name}'."}

# Instantiate and register into MCP Manager
from backend.mcp.manager import mcp_manager
spotify_server = SpotifyMCPServer()
mcp_manager.register_server("spotify", spotify_server)
