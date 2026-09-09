import os
import subprocess
import threading
import logging

logger = logging.getLogger("daisy.voice.tts")

class TTSEngine:
    """
    Two-way Voice Output (TTS) Engine:
    Synthesizes Daisy's spoken replies aloud using native Windows System.Speech
    in a dedicated background thread to guarantee zero event loop contention.
    """

    @classmethod
    def _speak_worker(cls, text: str):
        if not text:
            return

        import re
        text = re.sub(r"https?://\S+", "", text).strip()
        if not text:
            return

        # Method 1: Edge-TTS (if installed)
        try:
            import edge_tts
            import asyncio
            async def _run_edge():
                communicate = edge_tts.Communicate(text, voice="en-US-JennyNeural")
                output_file = os.path.join(os.getcwd(), "response.mp3")
                await communicate.save(output_file)
            asyncio.run(_run_edge())
            logger.info(f"Synthesized Edge-TTS speech: '{text}'")
            return
        except Exception:
            pass

        # Method 2: Native Windows System.Speech via stdin (zero shell injection risk)
        try:
            ps_script = "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; $text = [Console]::In.ReadToEnd(); if ($text) { Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak($text) }"
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            logger.info(f"Spoken aloud: '{text}'")
        except Exception as e:
            logger.debug(f"Native Windows speech error: {e}")

    @classmethod
    def speak(cls, text: str):
        """Asynchronously dispatches speech in a daemon thread."""
        if not text:
            return
        threading.Thread(target=cls._speak_worker, args=(text,), daemon=True).start()

if __name__ == "__main__":
    TTSEngine.speak("Daisy voice assistant is online.")

