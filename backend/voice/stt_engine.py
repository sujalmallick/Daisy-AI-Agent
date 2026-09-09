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
        self._load_model()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            device = self.hw_info["device"]
            compute_type = self.hw_info["compute_type"]

            logger.info(f"Loading faster-whisper on {device} ({compute_type})...")
            self.model = WhisperModel("small.en", device=device, compute_type=compute_type)
            logger.info("faster-whisper loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load faster-whisper on {self.hw_info['device']}: {e}. Falling back to standard recognizer.")

    def transcribe(self, audio_file_or_data) -> str:
        if self.model:
            try:
                segments, _ = self.model.transcribe(audio_file_or_data, beam_size=2)
                text = " ".join([s.text for s in segments]).strip()
                return text
            except Exception as e:
                logger.error(f"Whisper transcription error: {e}")

        # Fallback to speech_recognition
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            if hasattr(audio_file_or_data, "read"):
                with sr.AudioFile(audio_file_or_data) as source:
                    audio = r.record(source)
                    return r.recognize_google(audio)
        except Exception:
            pass

        return ""

stt_engine = AdaptiveSTTEngine()
