"""
Daisy Local STT Listener — GPU-Accelerated Real-Time Audio Capture
===================================================================
Captures microphone audio locally via PyAudio, applies real-time RMS
energy-based Voice Activity Detection (VAD) with 300ms silence cutoff,
and passes utterances directly to `stt_engine` (faster-whisper on CUDA).

Broadcasts real-time events to connected WebSockets (/ws/voice):
  - {"event": "state_change", "state": "idle" | "listening" | "thinking" | "speaking"}
  - {"event": "transcript", "text": "...", "is_final": true}
  - {"event": "command_result", "data": {...}}
  - {"event": "cancel_tts"}
"""

from __future__ import annotations

import asyncio
import collections
import io
import json
import logging
import math
import struct
import threading
import time
import wave
from typing import Any, Dict, Optional, Set

from backend.agent.alexa_grammar import AlexaIntentParser
from backend.agent.planner import agentic_planner
from backend.voice.stt_engine import stt_engine
from backend.voice.tts_manager import tts_manager

logger = logging.getLogger("daisy.voice.listener")


class STTListener:
    """
    Continuous local microphone capture and VAD processing.
    Connects frontend WebView2 directly to local CUDA STT without browser speech limitations.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    FRAME_SIZE = 512          # 32ms per frame at 16kHz
    FRAME_DURATION_SEC = 512 / 16000  # 0.032s
    SILENCE_THRESHOLD_SEC = 0.300     # 300ms silence ends utterance
    MIN_SPEECH_DURATION_SEC = 0.250   # Ignore clicks under 250ms
    MAX_SPEECH_DURATION_SEC = 10.0    # Safeguard against infinite listening
    PREROLL_FRAMES = 10               # ~320ms audio pre-roll buffer

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self.state: str = "idle"  # "idle" | "listening" | "thinking" | "speaking"
        self.is_direct_listening: bool = False
        self._direct_timeout: float = 0.0
        self.energy_threshold: float = 450.0  # Dynamic VAD RMS threshold
        self.active_websockets: Set[Any] = set()

        self.is_speaking: bool = False
        self.speaking_text: str = ""

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register_websocket(self, ws: Any) -> None:
        with self._lock:
            self.active_websockets.add(ws)
        logger.info(f"[STTListener] Client connected to /ws/voice (total: {len(self.active_websockets)})")

    def unregister_websocket(self, ws: Any) -> None:
        with self._lock:
            self.active_websockets.discard(ws)
        logger.info(f"[STTListener] Client disconnected from /ws/voice (remaining: {len(self.active_websockets)})")

    def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON event payload to all connected WebSocket clients."""
        with self._lock:
            clients = list(self.active_websockets)
        if not clients:
            return

        payload = json.dumps(message)

        async def _send(client: Any) -> None:
            try:
                await client.send_text(payload)
            except Exception:
                with self._lock:
                    self.active_websockets.discard(client)

        if self._loop and self._loop.is_running():
            for ws in clients:
                asyncio.run_coroutine_threadsafe(_send(ws), self._loop)

    def set_state(self, new_state: str) -> None:
        if self.state != new_state:
            self.state = new_state
            self.broadcast({"event": "state_change", "state": new_state})

    def set_speaking(self, is_speaking: bool, text: str = "") -> None:
        with self._lock:
            self.is_speaking = is_speaking
            self.speaking_text = text
        if is_speaking:
            self.set_state("speaking")
        else:
            if self.state == "speaking":
                self.set_state("idle")

    def trigger_listen(self) -> None:
        """Trigger direct microphone listening immediately (e.g. Orb click or hotkey)."""
        logger.info("[STTListener] Direct listening triggered.")
        self.is_direct_listening = True
        self._direct_timeout = time.time() + 6.0
        self.set_state("listening")

    def stop_listen(self) -> None:
        self.is_direct_listening = False
        self.set_state("idle")

    def reset(self) -> None:
        self.is_direct_listening = False
        with self._lock:
            self.is_speaking = False
            self.speaking_text = ""
        self.set_state("idle")

    def start(self) -> None:
        """Starts background audio capture thread."""
        if self._capture_thread and self._capture_thread.is_alive():
            return
        self._stop_event.clear()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True, name="daisy-stt-listener")
        self._capture_thread.start()
        logger.info("[STTListener] Started background audio capture thread.")

    def stop(self) -> None:
        """Stops background audio capture."""
        self._stop_event.set()
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
        logger.info("[STTListener] Stopped background audio capture.")

    @staticmethod
    def _calculate_rms(frame: bytes) -> float:
        count = len(frame) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", frame)
        return math.sqrt(sum(s * s for s in shorts) / count)

    def _calibrate_noise_floor(self, stream: Any) -> None:
        """Measures ambient noise floor to dynamically calibrate VAD sensitivity."""
        samples = []
        try:
            for _ in range(15):
                data = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                samples.append(self._calculate_rms(data))
            if samples:
                avg_rms = sum(samples) / len(samples)
                self.energy_threshold = max(avg_rms * 1.8, 400.0)
                logger.info(f"[STTListener] Calibrated ambient RMS: {avg_rms:.1f}, VAD threshold: {self.energy_threshold:.1f}")
        except Exception as e:
            logger.debug(f"[STTListener] Calibration note: {e}")

    def _capture_loop(self) -> None:
        """Main audio capture and local VAD loop."""
        p = None
        stream = None
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.FRAME_SIZE,
            )
        except Exception as e:
            logger.warning(f"[STTListener] Could not open microphone with PyAudio: {e}. STT listener running in passive mode.")
            return

        self._calibrate_noise_floor(stream)

        preroll_buffer: collections.deque[bytes] = collections.deque(maxlen=self.PREROLL_FRAMES)
        audio_buffer = bytearray()
        is_speech_active = False
        silence_duration = 0.0

        try:
            while not self._stop_event.is_set():
                try:
                    data = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                except Exception:
                    time.sleep(0.02)
                    continue

                now = time.time()

                # Watchdog for direct listening: timeout if user does not begin speaking
                if self.is_direct_listening and not is_speech_active:
                    if now > self._direct_timeout:
                        logger.info("[STTListener] Direct listening timed out without speech.")
                        self.is_direct_listening = False
                        self.set_state("idle")

                # Barge-in / Echo check: If Daisy is currently speaking
                with self._lock:
                    currently_speaking = self.is_speaking or tts_manager.is_speaking

                if currently_speaking:
                    rms = self._calculate_rms(data)
                    # Interruption requires vocal energy significantly higher than speaker bleed
                    if rms > self.energy_threshold * 2.2:
                        logger.info("[STTListener] Barge-in vocal interruption detected! Halting TTS.")
                        with self._lock:
                            self.is_speaking = False
                        tts_manager.stop()
                        self.broadcast({"event": "cancel_tts"})
                        self.set_state("listening")
                        audio_buffer.clear()
                        audio_buffer.extend(data)
                        is_speech_active = True
                        silence_duration = 0.0
                    continue

                rms = self._calculate_rms(data)
                is_above_threshold = rms > self.energy_threshold

                # State machine
                if not is_speech_active:
                    if is_above_threshold:
                        # User physically began vocalizing
                        is_speech_active = True
                        silence_duration = 0.0
                        audio_buffer.clear()
                        # Prepend pre-roll buffer so initial phonemes / consonants are not clipped
                        for pf in preroll_buffer:
                            audio_buffer.extend(pf)
                        audio_buffer.extend(data)
                        self.set_state("listening")
                    else:
                        preroll_buffer.append(data)
                else:
                    audio_buffer.extend(data)
                    if is_above_threshold:
                        silence_duration = 0.0
                    else:
                        silence_duration += self.FRAME_DURATION_SEC

                    total_duration = len(audio_buffer) / (self.SAMPLE_RATE * 2)

                    # Speech utterance completed via silence cutoff (300ms) or max limit (10s)
                    if silence_duration >= self.SILENCE_THRESHOLD_SEC or total_duration >= self.MAX_SPEECH_DURATION_SEC:
                        if total_duration >= self.MIN_SPEECH_DURATION_SEC:
                            speech_bytes = bytes(audio_buffer)
                            was_direct = self.is_direct_listening
                            self.is_direct_listening = False
                            is_speech_active = False
                            silence_duration = 0.0
                            audio_buffer.clear()
                            preroll_buffer.clear()

                            self._process_utterance(speech_bytes, was_direct)
                        else:
                            # Too short, discard transient noise / click
                            is_speech_active = False
                            silence_duration = 0.0
                            audio_buffer.clear()
                            if not self.is_direct_listening:
                                self.set_state("idle")

        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

    def _process_utterance(self, pcm_bytes: bytes, was_direct: bool) -> None:
        """Converts PCM to WAV, transcribes via CUDA faster-whisper, and routes command."""
        self.set_state("thinking")

        # Encode PCM into standard 16kHz 16-bit mono WAV buffer
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
        wav_io.seek(0)

        # Transcribe with local faster-whisper
        t0 = time.time()
        transcript = stt_engine.transcribe(wav_io)
        latency_ms = int((time.time() - t0) * 1000)
        logger.info(f"[STTListener] Transcribed in {latency_ms}ms: '{transcript}'")

        if not transcript or len(transcript.strip()) < 2:
            self.set_state("idle")
            return

        text = transcript.strip()
        self.broadcast({"event": "transcript", "text": text, "is_final": True})

        # Check wake-word triggers if not in direct mode
        wake = AlexaIntentParser.wake_word.lower()
        text_lower = text.lower()
        has_wake = wake in text_lower or "daisy" in text_lower

        if was_direct or has_wake:
            logger.info(f"[STTListener] Executing command: '{text}' (direct={was_direct})")
            try:
                result = agentic_planner.process(text)
            except Exception as e:
                logger.error(f"[STTListener] Planner execution error: {e}")
                result = {
                    "source": "error_handler",
                    "spoken_reply": "I ran into an issue while processing that.",
                    "status": "failed"
                }

            # Broadcast command result to connected UI clients
            self.broadcast({"event": "command_result", "data": result})

            with self._lock:
                has_ui_clients = len(self.active_websockets) > 0

            spoken = result.get("spoken_reply")
            # If NO UI websocket clients are connected, play TTS directly on host system
            if not has_ui_clients and spoken and spoken != "Done.":
                self.set_state("speaking")
                tts_manager.speak(spoken)
            elif not has_ui_clients:
                self.set_state("idle")
            # If UI clients are connected, the frontend plays streaming TTS via speakAloud
            # and informs stt_listener via action: speaking_start / speaking_stop.
        else:
            self.set_state("idle")


stt_listener = STTListener()
