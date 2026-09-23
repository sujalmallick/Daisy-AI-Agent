import logging
from backend.hardware import detect_hardware_tier

logger = logging.getLogger("daisy.voice.stt")

class AdaptiveSTTEngine:
    """
    Adaptive Speech-to-Text Engine:
    Auto-detects host hardware (RTX 3050 CUDA -> DirectML -> CPU int8)
    and loads the fastest available speech model.
    """

    def __init__(self):
        self.hw_info = detect_hardware_tier()
        self.model = None
        self._load_attempted = False

    def _load_model(self):
        self._load_attempted = True
        try:
            from faster_whisper import WhisperModel
            device = self.hw_info["device"]
            compute_type = self.hw_info["compute_type"]

            model_size = "tiny.en"
            logger.info(f"Loading faster-whisper ({model_size}) on {device} ({compute_type})...")
            try:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=4, local_files_only=True)
            except Exception:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=4, local_files_only=False)
            logger.info(f"faster-whisper ({model_size}) loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load faster-whisper on {self.hw_info['device']}: {e}. Falling back to standard recognizer.")

    def warmup(self):
        """Pre-loads model and runs a 0.1s blank audio warmup to eliminate cold-start latency."""
        if self.model is None and not self._load_attempted:
            self._load_model()
        if self.model:
            try:
                import io, wave
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b"\x00" * 3200)  # 0.1s audio
                buf.seek(0)
                segments, _ = self.model.transcribe(buf, beam_size=1)
                list(segments)
                logger.info("faster-whisper model warmed up and ready.")
            except Exception as e:
                logger.debug(f"STT warmup note: {e}")

    def transcribe(self, audio_file_or_data) -> str:
        if self.model is None and not self._load_attempted:
            self._load_model()

        if hasattr(audio_file_or_data, "seek"):
            audio_file_or_data.seek(0)

        if self.model:
            try:
                segments, _ = self.model.transcribe(audio_file_or_data, beam_size=1)
                text = " ".join([s.text for s in segments]).strip()
                return text
            except Exception as e:
                logger.error(f"Whisper transcription error on {self.hw_info.get('device')}: {e}")
                # If CUDA library missing, seamlessly downgrade to CPU int8
                if "cublas" in str(e).lower() or "cuda" in str(e).lower():
                    try:
                        logger.info("Falling back to faster-whisper on CPU (int8)...")
                        from faster_whisper import WhisperModel
                        self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=4)
                        self.hw_info["device"] = "cpu"
                        self.hw_info["compute_type"] = "int8"
                        if hasattr(audio_file_or_data, "seek"):
                            audio_file_or_data.seek(0)
                        segments, _ = self.model.transcribe(audio_file_or_data, beam_size=1)
                        text = " ".join([s.text for s in segments]).strip()
                        return text
                    except Exception as cpu_err:
                        logger.error(f"CPU Whisper fallback error: {cpu_err}")

        # Fallback to speech_recognition
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            if hasattr(audio_file_or_data, "seek"):
                audio_file_or_data.seek(0)
            if hasattr(audio_file_or_data, "read"):
                with sr.AudioFile(audio_file_or_data) as source:
                    audio = r.record(source)
                    return r.recognize_google(audio)
        except Exception:
            pass

        return ""

stt_engine = AdaptiveSTTEngine()
