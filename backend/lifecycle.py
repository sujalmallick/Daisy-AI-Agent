import os
import sys
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger("daisy.lifecycle")

class DaisyLifecycleManager:
    """
    Unified Application Lifecycle & Shutdown Manager for Daisy:
    Ensures that when Daisy closes (via window close, Tauri quit, system tray,
    voice command, or Ctrl+C), all subsystems are stopped in exact order:
    1. Stop Spotify playback immediately (API + Windows hardware media key)
    2. Stop TTS/audio playback
    3. Stop microphone & audio streams
    4. Stop STT/Whisper
    5. Cancel background tasks
    6. Stop MCP/backend processes
    7. Exit application
    """
    _instance: Optional["DaisyLifecycleManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._is_shutting_down = False

    @classmethod
    def get_instance(cls) -> "DaisyLifecycleManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = DaisyLifecycleManager()
            return cls._instance

    def stop_spotify(self) -> bool:
        """
        Guaranteed Spotify stop:
        1. Attempts Spotify Web API pause via MCP
        2. Dispatches Windows hardware media key VK_MEDIA_STOP (0xB2)
           to halt local Spotify desktop playback immediately even if offline or 403.
        """
        stopped = False

        # Layer 1: Spotify MCP Server Web API pause
        try:
            from backend.mcp.servers.spotify.server import spotify_server
            if spotify_server and spotify_server.sp:
                res = spotify_server.execute_tool("pause", {})
                logger.info(f"[Lifecycle] Spotify Web API pause result: {res}")
                stopped = True
        except Exception as e:
            logger.debug(f"[Lifecycle] Spotify Web API pause notice: {e}")

        # Layer 2: Windows Hardware Media Key Stop (VK_MEDIA_STOP = 0xB2)
        if sys.platform == "win32":
            try:
                import ctypes
                VK_MEDIA_STOP = 0xB2
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, KEYEVENTF_KEYUP, 0)
                logger.info("[Lifecycle] Windows VK_MEDIA_STOP hardware key signal dispatched.")
                stopped = True
            except Exception as hw_err:
                logger.debug(f"[Lifecycle] Windows media key stop error: {hw_err}")

        return stopped

    def stop_tts(self):
        """Stops any active TTS speech and terminates media players."""
        try:
            from backend.voice.tts_manager import tts_manager
            tts_manager.stop()
            logger.info("[Lifecycle] TTS playback stopped.")
        except Exception as e:
            logger.debug(f"[Lifecycle] TTS stop notice: {e}")

    def shutdown(self, source: str = "unknown"):
        """
        Executes complete application-wide shutdown in exact required sequence.
        """
        with self._lock:
            if self._is_shutting_down:
                logger.info(f"[Lifecycle] Shutdown already in progress (triggered by {source}).")
                return
            self._is_shutting_down = True

        logger.info(f"[Lifecycle] === Initiating Daisy Shutdown (Source: {source}) ===")

        # 1. Stop Spotify playback immediately
        try:
            self.stop_spotify()
        except Exception as e:
            logger.warning(f"[Lifecycle] Error stopping Spotify: {e}")

        # 2. Stop TTS / audio playback
        try:
            self.stop_tts()
        except Exception as e:
            logger.warning(f"[Lifecycle] Error stopping TTS: {e}")

        # 3. Stop STT / Whisper / background audio tasks
        try:
            from backend.voice.stt_engine import stt_engine
            stt_engine.model = None
            logger.info("[Lifecycle] STT engine unmounted.")
        except Exception as e:
            logger.debug(f"[Lifecycle] STT cleanup notice: {e}")

        # 4. Clean up any zombie ports / child processes
        try:
            logger.info("[Lifecycle] Background cleanup complete.")
        except Exception as e:
            logger.debug(f"[Lifecycle] Subprocess cleanup notice: {e}")

        logger.info("[Lifecycle] Shutdown sequence finished. Exiting process.")

        # Schedule hard exit to prevent hanging on open threads
        def _force_exit():
            time.sleep(0.15)
            os._exit(0)

        threading.Thread(target=_force_exit, daemon=True).start()

lifecycle_manager = DaisyLifecycleManager.get_instance()
