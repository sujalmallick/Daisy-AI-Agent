"""
Daisy TTS Manager — Centralized Voice Engine
============================================
Single authority for all TTS in Daisy. Manages provider selection, voice
configuration persistence, audio synthesis, and instant stop/barge-in support.

Providers (in priority order):
  1. edge-tts    — Microsoft Edge Neural voices (requires network, returns MP3)
  2. windows-tts — Windows SAPI / System.Speech  (offline, returns WAV)
  3. disabled    — Silent mode (no audio)

Only ONE provider is active at a time. Config is persisted to
  backend/config/voice_config.json
so the chosen voice survives restarts.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("daisy.voice.tts")

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
_CONFIG_DIR = _HERE.parent / "config"
_CONFIG_FILE = _CONFIG_DIR / "voice_config.json"

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "edge-tts",          # "edge-tts" | "windows-tts" | "disabled"
    "voice": "en-US-AvaNeural",      # Edge voice (persistent)
    "windows_voice": "Microsoft Zira Desktop",  # Windows SAPI voice
    "rate": 1.05,
    "pitch": 1.02,
}


# ── Available voice catalogs ───────────────────────────────────────────────────
EDGE_TTS_VOICES: List[Dict[str, str]] = [
    {"name": "en-US-AvaNeural",      "label": "Ava (US Warm Female, Neural)"},
    {"name": "en-US-EmmaNeural",     "label": "Emma (US Conversational Female, Neural)"},
    {"name": "en-US-JennyNeural",    "label": "Jenny (US Female, Neural)"},
    {"name": "en-US-GuyNeural",      "label": "Guy (US Male, Neural)"},
    {"name": "en-US-AriaNeural",     "label": "Aria (US Female, Neural)"},
    {"name": "en-US-EricNeural",     "label": "Eric (US Male, Neural)"},
    {"name": "en-US-MichelleNeural", "label": "Michelle (US Female, Neural)"},
    {"name": "en-GB-SoniaNeural",    "label": "Sonia (GB Female, Neural)"},
    {"name": "en-GB-RyanNeural",     "label": "Ryan (GB Male, Neural)"},
    {"name": "en-AU-NatashaNeural",  "label": "Natasha (AU Female, Neural)"},
    {"name": "en-AU-WilliamNeural",  "label": "William (AU Male, Neural)"},
    {"name": "en-IN-NeerjaNeural",   "label": "Neerja (IN Female, Neural)"},
]

WINDOWS_TTS_VOICES: List[Dict[str, str]] = [
    {"name": "Microsoft Zira Desktop", "label": "Zira (US Female)"},
    {"name": "Microsoft David Desktop", "label": "David (US Male)"},
]


class TTSManager:
    """
    Central TTS Manager — single instance, thread-safe.

    Usage:
        from backend.voice.tts_manager import tts_manager
        tts_manager.speak("Hello!")
        tts_manager.stop()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config: Dict[str, Any] = {}
        self._active_proc: Optional[subprocess.Popen] = None
        self._active_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._load_config()

    # ── Configuration ──────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if _CONFIG_FILE.exists():
            try:
                stored = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
                self._config = {**DEFAULT_CONFIG, **stored}
                logger.info(
                    f"[TTS] Loaded voice config: provider={self._config['provider']}, "
                    f"voice={self._config.get('voice')}"
                )
                return
            except Exception as e:
                logger.warning(f"[TTS] Could not read voice_config.json: {e}. Using defaults.")
        self._config = dict(DEFAULT_CONFIG)
        self._save_config()

    def _save_config(self) -> None:
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            _CONFIG_FILE.write_text(
                json.dumps(self._config, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[TTS] Could not save voice_config.json: {e}")

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            cfg = dict(self._config)
        cfg["available_providers"] = ["edge-tts", "windows-tts", "disabled"]
        cfg["edge_voices"] = EDGE_TTS_VOICES
        cfg["windows_voices"] = _get_windows_voices()
        return cfg

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            allowed = {"provider", "voice", "windows_voice", "rate", "pitch"}
            for k, v in updates.items():
                if k in allowed:
                    if k == "windows_voice" and isinstance(v, str):
                        v = re.sub(r"[^a-zA-Z0-9\s\-]", "", v).strip()
                    self._config[k] = v
            self._save_config()
        return self.get_config()

    @property
    def provider(self) -> str:
        return self._config.get("provider", "edge-tts")

    @property
    def voice(self) -> str:
        return self._config.get("voice", "en-US-AvaNeural")

    @property
    def windows_voice(self) -> str:
        return self._config.get("windows_voice", "Microsoft Zira Desktop")

    @property
    def rate(self) -> float:
        return self._config.get("rate", 1.05)

    @property
    def pitch(self) -> float:
        return self._config.get("pitch", 1.02)

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return getattr(self, "_is_speaking_state", False) or (self._active_proc is not None)

    @staticmethod
    def _format_rate(rate: Any) -> str:
        if isinstance(rate, str):
            return rate if rate.endswith("%") else f"{rate}%"
        try:
            pct = int(round((float(rate) - 1.0) * 100))
            return f"{pct:+d}%"
        except Exception:
            return "+0%"

    @staticmethod
    def _format_pitch(pitch: Any) -> str:
        if isinstance(pitch, str):
            return pitch if pitch.endswith("Hz") else f"{pitch}Hz"
        try:
            hz = int(round((float(pitch) - 1.0) * 100))
            return f"{hz:+d}Hz"
        except Exception:
            return "+0Hz"

    # ── Stop / Barge-In ───────────────────────────────────────────────────────

    def stop(self) -> None:
        """
        Instantly stop any active TTS playback. Thread-safe.
        Called during barge-in to cut Daisy off immediately.
        """
        self._stop_event.set()
        with self._lock:
            if self._active_proc:
                try:
                    self._active_proc.terminate()
                except Exception:
                    pass
                self._active_proc = None

    def _reset_stop_event(self) -> None:
        self._stop_event.clear()

    # ── Synthesis ─────────────────────────────────────────────────────────────

    async def stream_chunks(self, text: str):
        """
        Asynchronously yield MP3 audio chunks as they arrive from edge_tts.
        Enables streaming audio playback in the browser for sub-200ms time-to-first-audio-byte.
        """
        import re
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_#`~]", "", text)
        text = text.strip()
        if not text:
            return

        if self.provider == "disabled":
            return

        if self.provider == "edge-tts":
            try:
                import edge_tts
                voice = self.voice
                rate_str = self._format_rate(self.rate)
                pitch_str = self._format_pitch(self.pitch)
                communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
                async for chunk in communicate.stream():
                    if self._stop_event.is_set():
                        break
                    if chunk["type"] == "audio" and chunk.get("data"):
                        yield chunk["data"]
                return
            except Exception as e:
                logger.warning(f"[TTS] stream_chunks Edge-TTS failed: {e}")

        # Fallback to whole buffer synthesis
        res = await asyncio.to_thread(self.synthesize_to_bytes, text)
        if res:
            audio_bytes, _ = res
            chunk_size = 4096
            for i in range(0, len(audio_bytes), chunk_size):
                if self._stop_event.is_set():
                    break
                yield audio_bytes[i:i + chunk_size]

    def synthesize_to_bytes(self, text: str) -> Optional[Tuple[bytes, str]]:
        """
        Synthesize text to audio bytes.
        Returns (audio_bytes, mime_type) or None on failure.
        """
        if not text or not text.strip():
            return None

        import re
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_#`~]", "", text)
        text = text.strip()
        if not text:
            return None

        provider = self.provider

        if provider == "edge-tts":
            result = self._synthesize_edge_tts(text)
            if result:
                return result
            logger.warning("[TTS] Edge-TTS failed, falling back to Windows TTS.")
            return self._synthesize_windows_tts(text)

        elif provider == "windows-tts":
            return self._synthesize_windows_tts(text)

        return None  # disabled

    def _synthesize_edge_tts(self, text: str) -> Optional[Tuple[bytes, str]]:
        """Synthesize using Edge-TTS, returns (mp3_bytes, 'audio/mpeg'). Safe inside or outside event loops."""
        try:
            import edge_tts
            import concurrent.futures

            async def _run() -> bytes:
                voice = self.voice
                rate_str = self._format_rate(self.rate)
                pitch_str = self._format_pitch(self.pitch)
                communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
                buf = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.extend(chunk["data"])
                return bytes(buf)

            # Check if there is already a running loop in this thread
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    audio_bytes = executor.submit(lambda: asyncio.run(_run())).result()
            else:
                audio_bytes = asyncio.run(_run())

            if audio_bytes:
                logger.info(f"[TTS] Edge-TTS synthesized {len(audio_bytes)} bytes (voice={self.voice})")
                return (audio_bytes, "audio/mpeg")
        except Exception as e:
            logger.warning(f"[TTS] Edge-TTS synthesis error: {e}")
        return None

    def _synthesize_windows_tts(self, text: str) -> Optional[Tuple[bytes, str]]:
        """Synthesize using Windows SAPI, returns (wav_bytes, 'audio/wav')."""
        try:
            voice = re.sub(r"[^a-zA-Z0-9\s\-]", "", self.windows_voice).strip()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            # PowerShell script: uses environment variables instead of string interpolation
            ps = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$pref = $env:DAISY_TTS_VOICE; "
                "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -eq $pref -and $_.Enabled } | Select-Object -First 1; "
                "if (-not $v) { "
                "  $v = $s.GetInstalledVoices() | Where-Object { ($_.VoiceInfo.Gender -eq 'Female' -or $_.VoiceInfo.Name -match 'Zira|Jenny|Aria|Female|Eva|Hazel') -and $_.Enabled } | Select-Object -First 1 "
                "}; "
                "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
                "$s.SetOutputToWaveFile($env:DAISY_TTS_OUTPUT); "
                "$s.Speak($input); "
                "$s.SetOutputToDefaultAudioDevice()"
            )
            env = {**os.environ, "DAISY_TTS_VOICE": voice, "DAISY_TTS_OUTPUT": tmp_path}
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                input=text,
                text=True,
                capture_output=True,
                timeout=12,
                env=env,
            )
            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as wf:
                    wav_bytes = wf.read()
                os.unlink(tmp_path)
                if wav_bytes:
                    logger.info(f"[TTS] Windows TTS synthesized {len(wav_bytes)} bytes (voice={voice})")
                    return (wav_bytes, "audio/wav")
        except Exception as e:
            logger.warning(f"[TTS] Windows TTS synthesis error: {e}")
        return None

    # ── Direct Playback (backend-side, for /voice/test) ───────────────────────

    def speak(self, text: str) -> None:
        """
        Speak text asynchronously via the system audio output.
        Any previous speech is stopped immediately before starting.
        This is ONLY used by the backend /voice/test endpoint.
        Normal voice replies are streamed to the frontend via /voice/synthesize.
        """
        self.stop()
        self._reset_stop_event()

        t = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        with self._lock:
            self._active_thread = t
        t.start()

    def _speak_worker(self, text: str) -> None:
        if self._stop_event.is_set():
            return

        with self._lock:
            self._is_speaking_state = True
        try:
            provider = self.provider

            if provider == "edge-tts":
                self._play_edge_tts(text)
            elif provider == "windows-tts":
                self._play_windows_tts_direct(text)
        finally:
            with self._lock:
                self._is_speaking_state = False

    def _play_edge_tts(self, text: str) -> None:
        """Synthesize Edge-TTS and play via system default media player or mplayer."""
        try:
            import edge_tts

            async def _run():
                voice = self.voice
                rate_str = self._format_rate(self.rate)
                pitch_str = self._format_pitch(self.pitch)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tmp_path = f.name
                communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
                await communicate.save(tmp_path)
                return tmp_path

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    tmp_path = executor.submit(lambda: asyncio.run(_run())).result()
            else:
                tmp_path = asyncio.run(_run())

            if self._stop_event.is_set():
                os.unlink(tmp_path)
                return

            # Use Windows Media Foundation via PowerShell to play the MP3 silently
            ps = (
                f"Add-Type -AssemblyName presentationCore; "
                f"$m = New-Object System.Windows.Media.MediaPlayer; "
                f"$m.Open([uri]'{tmp_path}'); "
                f"$m.Play(); "
                f"Start-Sleep -Milliseconds 500; "
                f"while ($m.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 100 }}; "
                f"$dur = [int]$m.NaturalDuration.TimeSpan.TotalMilliseconds + 300; "
                f"Start-Sleep -Milliseconds $dur; "
                f"$m.Close()"
            )
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with self._lock:
                self._active_proc = proc

            # Wait for completion or stop signal
            while proc.poll() is None:
                if self._stop_event.is_set():
                    proc.terminate()
                    break
                threading.Event().wait(0.05)

            with self._lock:
                self._active_proc = None

            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"[TTS] Edge-TTS playback error: {e}")
            # Fallback
            self._play_windows_tts_direct(text)

    def _play_windows_tts_direct(self, text: str) -> None:
        """Play text via Windows SAPI directly."""
        try:
            voice = re.sub(r"[^a-zA-Z0-9\s\-]", "", self.windows_voice).strip()
            ps = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$pref = $env:DAISY_TTS_VOICE; "
                "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -eq $pref -and $_.Enabled } | Select-Object -First 1; "
                "if (-not $v) { "
                "  $v = $s.GetInstalledVoices() | Where-Object { ($_.VoiceInfo.Gender -eq 'Female' -or $_.VoiceInfo.Name -match 'Zira|Jenny|Aria|Female|Eva|Hazel') -and $_.Enabled } | Select-Object -First 1 "
                "}; "
                "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
                "$s.Speak($input)"
            )
            env = {**os.environ, "DAISY_TTS_VOICE": voice}
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            with self._lock:
                self._active_proc = proc

            proc.stdin.write(text.encode("utf-8"))
            proc.stdin.close()

            while proc.poll() is None:
                if self._stop_event.is_set():
                    proc.terminate()
                    break
                threading.Event().wait(0.05)

            with self._lock:
                self._active_proc = None

        except Exception as e:
            logger.warning(f"[TTS] Windows TTS direct playback error: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

_WINDOWS_VOICES_CACHE: Optional[List[Dict[str, str]]] = None

def _get_windows_voices() -> List[Dict[str, str]]:
    """Query Windows SAPI for actually installed voices (cached)."""
    global _WINDOWS_VOICES_CACHE
    if _WINDOWS_VOICES_CACHE is not None:
        return _WINDOWS_VOICES_CACHE
    try:
        proc = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Add-Type -AssemblyName System.Speech; "
                "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | "
                "ForEach-Object { $_.VoiceInfo.Name }",
            ],
            capture_output=True, text=True, timeout=5,
        )
        names = [n.strip() for n in proc.stdout.splitlines() if n.strip()]
        if names:
            _WINDOWS_VOICES_CACHE = [{"name": n, "label": n} for n in names]
            return _WINDOWS_VOICES_CACHE
    except Exception:
        pass
    _WINDOWS_VOICES_CACHE = WINDOWS_TTS_VOICES  # Fallback to known defaults
    return _WINDOWS_VOICES_CACHE


# ── Global singleton ──────────────────────────────────────────────────────────
tts_manager = TTSManager()
