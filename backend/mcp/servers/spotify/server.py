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

    def _ensure_active_device(self) -> Optional[str]:
        """Edge Case: Checks for an active device; auto-transfers playback if found."""
        if not self.sp:
            return None
        try:
            devices = self.sp.devices().get("devices", [])
            # Priority 1: Always prefer local Computer / Desktop device over third-party smart speakers
            # Smart speakers (Amazon Echo, Nest, etc.) enforce strict API restrictions (403 Restriction violated)
            computer_dev = next((d for d in devices if d.get("type") in ("Computer", "Desktop")), None)
            if computer_dev:
                return computer_dev["id"]

            # Priority 2: If no Computer device is registered yet, launch Spotify desktop on PC
            logger.info("No Computer Spotify device found. Launching Spotify desktop on PC...")
            try:
                import subprocess, time
                subprocess.Popen(["cmd", "/c", "start", "", "spotify:"], shell=True)
                time.sleep(1.8)
                refreshed = self.sp.devices().get("devices", [])
                comp = next((d for d in refreshed if d.get("type") in ("Computer", "Desktop")), None)
                if comp:
                    return comp["id"]
            except Exception as e:
                logger.debug(f"Auto-launch Spotify notice: {e}")

            # Priority 3: Check if an active device exists
            for dev in devices:
                if dev.get("is_active"):
                    return dev.get("id")

            # Priority 4: Fallback to first available device
            if devices:
                return devices[0]["id"]

            return None
        except Exception as e:
            logger.warning(f"Could not auto-transfer playback: {e}")
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
                "name": "recommend_vibes",
                "description": "Starts a curated vibe session with recommended tracks based on mood or genre.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "genres": {"type": "array", "items": {"type": "string"}, "description": "List of seed genres e.g. ['pop', 'synthwave']"},
                        "mood": {"type": "string", "description": "Mood description e.g. 'late night', 'chill', 'workout'"}
                    }
                }
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
        if tool_name in ("play", "play_album", "resume", "next_track", "previous_track", "pause", "set_volume", "recommend_vibes"):
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
                    playback_succeeded = False
                    try:
                        self.sp.start_playback(device_id=target_device_id, uris=[track["uri"]])
                        playback_succeeded = True
                    except Exception as play_err:
                        logger.warning(f"Playback on {target_device_id} error: {play_err}")
                        # Auto-retry by opening Spotify on PC if it failed on smart speaker
                        try:
                            import subprocess, time
                            subprocess.Popen(["cmd", "/c", "start", "", "spotify:"], shell=True)
                            time.sleep(1.8)
                            refreshed = self.sp.devices().get("devices", [])
                            comp = next((d for d in refreshed if d.get("type") in ("Computer", "Desktop")), None)
                            if comp:
                                self.sp.start_playback(device_id=comp["id"], uris=[track["uri"]])
                                playback_succeeded = True
                        except Exception as fallback_err:
                            logger.warning(f"PC fallback playback error: {fallback_err}")

                    if not playback_succeeded:
                        return {
                            "status": "device_error",
                            "error": "Could not start playback. Please make sure Spotify is open on your PC.",
                            "message": "Spotify could not start playback. Please make sure Spotify is open on your PC."
                        }

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
                    tracks = self.sp.album_tracks(alb["id"])["items"]
                    uris = [t["uri"] for t in tracks]
                    playback_succeeded = False
                    try:
                        self.sp.start_playback(device_id=target_device_id, uris=uris)
                        playback_succeeded = True
                    except Exception:
                        try:
                            import subprocess, time
                            subprocess.Popen(["cmd", "/c", "start", "", "spotify:"], shell=True)
                            time.sleep(1.8)
                            refreshed = self.sp.devices().get("devices", [])
                            comp = next((d for d in refreshed if d.get("type") in ("Computer", "Desktop")), None)
                            if comp:
                                self.sp.start_playback(device_id=comp["id"], uris=uris)
                                playback_succeeded = True
                        except Exception:
                            pass

                    if not playback_succeeded:
                        return {
                            "status": "device_error",
                            "error": "Could not start playback. Please make sure Spotify is open on your PC.",
                            "message": "Spotify could not start playback. Please make sure Spotify is open on your PC."
                        }

                    return {"status": "playing_album", "album": alb["name"], "message": f"Playing album: {alb['name']}"}
                return {"error": f"Album '{album}' not found."}

            elif tool_name == "pause":
                self.sp.pause_playback(device_id=target_device_id)
                return {"status": "paused", "message": "Playback paused."}

            elif tool_name == "resume":
                self.sp.start_playback(device_id=target_device_id)
                return {"status": "resumed", "message": "Playback resumed."}

            elif tool_name == "next_track":
                try:
                    self.sp.next_track(device_id=target_device_id)
                except Exception as next_err:
                    if "NO_ACTIVE_DEVICE" in str(next_err) or "404" in str(next_err):
                        target_device_id = self._ensure_active_device()
                        self.sp.next_track(device_id=target_device_id)
                    else:
                        raise next_err
                return {"status": "skipped", "message": "Skipped to next track."}

            elif tool_name == "previous_track":
                try:
                    self.sp.previous_track(device_id=target_device_id)
                except Exception as prev_err:
                    if "NO_ACTIVE_DEVICE" in str(prev_err) or "404" in str(prev_err):
                        target_device_id = self._ensure_active_device()
                        self.sp.previous_track(device_id=target_device_id)
                    else:
                        raise prev_err
                return {"status": "previous", "message": "Returning to previous track."}

            elif tool_name == "set_volume":
                vol = max(0, min(100, int(args.get("percent", 70))))
                self.sp.volume(vol, device_id=target_device_id)
                return {"status": "volume_adjusted", "volume": vol, "message": f"Volume set to {vol}%."}

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
                self.sp.start_playback(device_id=target_device_id, uris=uris)
                return {
                    "status": "vibe_started",
                    "seeds": chosen,
                    "count": len(uris),
                    "message": f"Started vibe session with {len(uris)} recommended tracks."
                }

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
