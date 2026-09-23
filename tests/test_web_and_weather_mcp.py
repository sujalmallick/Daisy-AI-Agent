import os
import sys
sys.path.insert(0, os.getcwd())
import unittest
import time
from backend.mcp.manager import mcp_manager
from backend.agent.alexa_grammar import AlexaIntentParser
from backend.agent.planner import agentic_planner


class TestWebAndWeatherMCP(unittest.TestCase):
    def test_01_web_tools_registered(self):
        tools = mcp_manager.get_server_tools("web")
        tool_names = [t["name"] for t in tools]
        self.assertIn("search_youtube", tool_names)
        self.assertIn("search_google", tool_names)
        self.assertIn("open_url", tool_names)

    def test_02_weather_tools_registered(self):
        tools = mcp_manager.get_server_tools("weather")
        tool_names = [t["name"] for t in tools]
        self.assertIn("get_current_weather", tool_names)

    def test_03_weather_execution_and_caching(self):
        res = mcp_manager.execute("weather.get_current_weather", {"location": "London"})
        self.assertTrue(res.get("success"))
        result = res.get("result", {})
        self.assertIn("temp_c", result)
        self.assertEqual(result.get("card_type"), "weather")
        self.assertIn("card_data", result)

        # Verify in-memory cache speed (< 5ms)
        t0 = time.time()
        res_cached = mcp_manager.execute("weather.get_current_weather", {"location": "London"})
        elapsed = time.time() - t0
        self.assertTrue(res_cached.get("success"))
        self.assertLess(elapsed, 0.05)

    def test_04_alexa_intent_parsing(self):
        yt_cmd = AlexaIntentParser.parse("open lofi hip hop on youtube")
        self.assertTrue(len(yt_cmd) > 0)
        self.assertEqual(yt_cmd[0]["action"], "search_youtube")
        self.assertEqual(yt_cmd[0]["slots"]["query"], "lofi hip hop")

        google_cmd = AlexaIntentParser.parse("search google for mechanical keyboards")
        self.assertTrue(len(google_cmd) > 0)
        self.assertEqual(google_cmd[0]["action"], "search_google")
        self.assertEqual(google_cmd[0]["slots"]["query"], "mechanical keyboards")

        weather_cmd = AlexaIntentParser.parse("what's the weather in Tokyo")
        self.assertTrue(len(weather_cmd) > 0)
        self.assertEqual(weather_cmd[0]["action"], "get_weather")
        self.assertEqual(weather_cmd[0]["slots"]["location"].lower(), "tokyo")

    def test_05_planner_payload_structure(self):
        # Weather query
        w_plan = agentic_planner.process("weather in Tokyo")
        self.assertEqual(w_plan.get("card_type"), "weather")
        self.assertIn("card_data", w_plan)
        self.assertIn("spoken_reply", w_plan)
        self.assertIn("display_text", w_plan)

        # YouTube query
        yt_plan = agentic_planner.process("search youtube for synthwave beats")
        self.assertEqual(yt_plan.get("card_type"), "youtube")
        self.assertIn("card_data", yt_plan)
        self.assertIn("spoken_reply", yt_plan)
        self.assertIn("display_text", yt_plan)


if __name__ == "__main__":
    unittest.main()
