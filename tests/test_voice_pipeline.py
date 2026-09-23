import asyncio
import os
import sys
import time
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.voice.tts_manager import tts_manager, EDGE_TTS_VOICES
from backend.voice.stt_listener import stt_listener
from backend.main import app


class TestVoicePipeline(unittest.TestCase):

    def test_tts_config_and_formatting(self):
        """Verify Ava is default voice, and rate/pitch formatting works."""
        cfg = tts_manager.get_config()
        self.assertEqual(tts_manager.voice, "en-US-AvaNeural")
        self.assertEqual(tts_manager._format_rate(1.05), "+5%")
        self.assertEqual(tts_manager._format_pitch(1.02), "+2Hz")

        voice_names = [v["name"] for v in EDGE_TTS_VOICES]
        self.assertIn("en-US-AvaNeural", voice_names)
        self.assertIn("en-US-EmmaNeural", voice_names)

    def test_stream_chunks(self):
        """Verify stream_chunks async generator yields audio bytes."""
        async def _test():
            chunks = []
            async for chunk in tts_manager.stream_chunks("Testing Daisy voice pipeline."):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(_test())
        total_bytes = sum(len(c) for c in chunks)
        self.assertGreater(total_bytes, 0)

    def test_stt_listener_lifecycle(self):
        """Verify STT listener state transitions and direct listening triggers."""
        self.assertEqual(stt_listener.state, "idle")
        stt_listener.trigger_listen()
        self.assertTrue(stt_listener.is_direct_listening)
        self.assertEqual(stt_listener.state, "listening")
        stt_listener.reset()
        self.assertFalse(stt_listener.is_direct_listening)
        self.assertEqual(stt_listener.state, "idle")

    def test_fastapi_voice_routes(self):
        """Verify all new voice and streaming routes are present in FastAPI app."""
        routes = [route.path for route in app.routes]
        self.assertIn("/voice/synthesize/stream", routes)
        self.assertIn("/voice/listen", routes)
        self.assertIn("/ws/voice", routes)


if __name__ == "__main__":
    unittest.main()
