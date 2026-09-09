"""
TTSEngine — backwards-compatibility shim.
Delegates to the centralized TTSManager.
"""
import logging
from backend.voice.tts_manager import tts_manager

logger = logging.getLogger("daisy.voice.tts")


class TTSEngine:
    """
    Backwards-compatible wrapper around TTSManager.
    All callers using TTSEngine.speak() continue to work without changes.
    Voice/provider selection is now centralized in TTSManager.
    """

    @classmethod
    def speak(cls, text: str) -> None:
        """Asynchronously dispatches speech via the centralized TTS Manager."""
        if not text:
            return
        tts_manager.speak(text)

    @classmethod
    def stop(cls) -> None:
        """Stop any active speech immediately."""
        tts_manager.stop()


if __name__ == "__main__":
    TTSEngine.speak("Daisy voice assistant is online.")
