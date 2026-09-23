import unittest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.mcp.manager import mcp_manager
from backend.mcp.servers.screen.server import screen_server
from backend.agent.alexa_grammar import AlexaIntentParser
from backend.agent.fastpath import FastPathEngine
from backend.agent.planner import agentic_planner


class TestScreenVisionSystem(unittest.TestCase):

    def test_screen_tools_registered(self):
        """Verify screen MCP server tools are registered in mcp_manager."""
        tools = screen_server.get_tools()
        names = [t["name"] for t in tools]
        self.assertIn("capture_screen", names)
        self.assertIn("get_active_window", names)
        self.assertIn("highlight_element", names)

    def test_screen_domain_pruning(self):
        """Verify domain schema returns screen tools when requested."""
        schema = mcp_manager.get_domain_tools_schema(["screen"])
        names = [t["name"] for t in schema]
        self.assertTrue(any("screen_" in n for n in names))

    def test_win32_screen_capture(self):
        """Verify Win32 GDI screen capture returns valid image and dimensions."""
        res = screen_server.execute_tool("capture_screen", {"max_dimension": 640})
        self.assertEqual(res.get("status"), "captured")
        self.assertGreater(res.get("width", 0), 0)
        self.assertGreater(res.get("height", 0), 0)
        self.assertTrue(os.path.exists(res.get("path", "")))
        self.assertTrue(res.get("preview_data_url", "").startswith("data:image/jpeg;base64,"))
        self.assertEqual(res.get("card_type"), "vision")

    def test_highlight_element_tool(self):
        """Verify highlight_element returns pointer target coordinates."""
        res = screen_server.execute_tool("highlight_element", {"x": 500, "y": 300, "label": "Search Box"})
        self.assertEqual(res.get("status"), "highlighted")
        self.assertEqual(res.get("x"), 500)
        self.assertEqual(res.get("y"), 300)
        self.assertEqual(res.get("card_type"), "vision")
        self.assertEqual(res.get("card_data", {}).get("pointer_target", {}).get("x"), 500)

    def test_alexa_screen_intent_parsing(self):
        """Verify screen vision and agent mode intents parse accurately."""
        res1 = AlexaIntentParser.parse("what's on my screen")
        self.assertEqual(res1[0]["intent"], "Daisy.ScreenVisionIntent")
        self.assertEqual(res1[0]["action"], "screen_vision")

        res2 = AlexaIntentParser.parse("look at my screen")
        self.assertEqual(res2[0]["intent"], "Daisy.ScreenVisionIntent")

        res3 = AlexaIntentParser.parse("where is the login button")
        self.assertEqual(res3[0]["intent"], "Daisy.ScreenVisionIntent")

        res4 = AlexaIntentParser.parse("daisy agent summarize these files")
        self.assertEqual(res4[0]["intent"], "Daisy.AgentModeIntent")
        self.assertEqual(res4[0]["action"], "agent_mode")

    def test_fastpath_delegates_screen_vision(self):
        """Verify FastPath returns None for screen queries so Gemini handles multimodal reasoning."""
        fp_res = FastPathEngine.handle_quick_music("what is on my screen")
        self.assertIsNone(fp_res)

        fp_res2 = FastPathEngine.handle_quick_music("daisy agent do research")
        self.assertIsNone(fp_res2)

    def test_planner_screen_vision_response(self):
        """Verify agentic planner processes screen vision and returns a vision card."""
        plan_res = agentic_planner.process("what is on my screen")
        self.assertEqual(plan_res.get("card_type"), "vision")
        self.assertTrue(plan_res.get("card_data", {}).get("preview_url", "").startswith("data:image/jpeg;base64,"))
        self.assertIsNotNone(plan_res.get("card_data", {}).get("active_window"))
        self.assertTrue("screen" in plan_res.get("spoken_reply", "").lower() or "look" in plan_res.get("spoken_reply", "").lower())


if __name__ == "__main__":
    unittest.main()
