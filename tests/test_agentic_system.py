import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


class TestDaisyAgenticSystem(unittest.TestCase):

    def setUp(self):
        # Create a sample test document in .daisy_cache directory
        self.cache_dir = PROJECT_ROOT / ".daisy_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.test_file = self.cache_dir / "sample_test_doc.txt"
        self.test_file.write_text(
            "Project Alpha Overview.\n"
            "The goal of Project Alpha is to develop an autonomous agentic system for Windows.\n"
            "Key milestones include speech recognition integration, Alexa intent parsing, and RAG document search.\n"
            "The final delivery deadline is scheduled for November 25th 2026.\n"
            "Budget allocation is estimated at 15000 dollars.",
            encoding="utf-8"
        )

    def tearDown(self):
        if self.test_file.exists():
            try:
                self.test_file.unlink()
            except OSError:
                pass

    def test_01_path_resolver_safety(self):
        from backend.rag.path_resolver import is_safe_path
        self.assertTrue(is_safe_path(str(self.test_file)))
        self.assertFalse(is_safe_path("C:/Windows/System32/config/sam"))
        self.assertFalse(is_safe_path("~/.ssh/id_rsa"))
        self.assertFalse(is_safe_path("d:/workspace/.env"))

    def test_02_loader_and_chunker(self):
        from backend.rag.loader import DocumentLoader
        from backend.rag.chunker import TextChunker

        text = DocumentLoader.load_text(str(self.test_file))
        self.assertIsNotNone(text)
        self.assertIn("Project Alpha", text)

        chunker = TextChunker(chunk_size=150, chunk_overlap=30)
        chunks = chunker.chunk_document(text, str(self.test_file))
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["file_name"], "sample_test_doc.txt")

    def test_03_vector_store_retrieval(self):
        from backend.rag.loader import DocumentLoader
        from backend.rag.chunker import TextChunker
        from backend.rag.vector_store import desktop_vector_store

        text = DocumentLoader.load_text(str(self.test_file))
        chunker = TextChunker(chunk_size=200, chunk_overlap=40)
        chunks = chunker.chunk_document(text, str(self.test_file))
        desktop_vector_store.index_chunks(str(self.test_file), chunks)

        results = desktop_vector_store.search(str(self.test_file), "deadline delivery date", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("November 25th", results[0]["text"])

    def test_04_alexa_intent_rag_patterns(self):
        from backend.agent.alexa_grammar import AlexaIntentParser

        # Document Query
        parsed_query = AlexaIntentParser.parse("Daisy, what does my resume say about Python")
        self.assertEqual(len(parsed_query), 1)
        self.assertEqual(parsed_query[0]["intent"], "Daisy.DocumentQueryIntent")
        self.assertEqual(parsed_query[0]["slots"]["doc_name"], "resume")
        self.assertIn("python", parsed_query[0]["slots"]["query"].lower())
        self.assertEqual(parsed_query[0]["tokens"], 0)

        # Document Summarize
        parsed_sum = AlexaIntentParser.parse("Daisy, summarize project_plan on my desktop")
        self.assertEqual(len(parsed_sum), 1)
        self.assertEqual(parsed_sum[0]["intent"], "Daisy.DocumentSummarizeIntent")
        self.assertEqual(parsed_sum[0]["slots"]["doc_name"], "project_plan")
        self.assertEqual(parsed_sum[0]["tokens"], 0)

        # Confirmations
        parsed_yes = AlexaIntentParser.parse("yes please")
        self.assertEqual(parsed_yes[0]["action"], "confirm_yes")
        self.assertEqual(parsed_yes[0]["tokens"], 0)

        parsed_no = AlexaIntentParser.parse("cancel it")
        self.assertEqual(parsed_no[0]["action"], "confirm_no")
        self.assertEqual(parsed_no[0]["tokens"], 0)

    def test_05_hitl_manager(self):
        from backend.hitl.manager import hitl_manager, RiskTier

        # Check risk classification
        self.assertEqual(hitl_manager.evaluate_risk("spotify.play"), RiskTier.SAFE)
        self.assertEqual(hitl_manager.evaluate_risk("rag.query_desktop_doc"), RiskTier.SAFE)
        self.assertEqual(hitl_manager.evaluate_risk("app_launcher.close_app"), RiskTier.DESTRUCTIVE)

        # Register pending confirmation
        hitl_manager.request_confirmation(
            action_type="close_app",
            tool_name="app_launcher.close_app",
            args={"app_name": "notepad"},
            prompt_message="Are you sure you want to close Notepad?",
            display_name="Notepad"
        )
        self.assertTrue(hitl_manager.has_pending())
        pending = hitl_manager.get_pending()
        self.assertEqual(pending["display_name"], "Notepad")

        # Resolve rejection
        res_reject = hitl_manager.resolve(approved=False)
        self.assertEqual(res_reject["status"], "cancelled")
        self.assertFalse(hitl_manager.has_pending())

    def test_06_fastpath_hitl_integration(self):
        from backend.hitl.manager import hitl_manager
        from backend.agent.fastpath import FastPathEngine

        # Register pending confirmation
        hitl_manager.request_confirmation(
            action_type="exit_app",
            tool_name="system.exit_app",
            args={},
            prompt_message="Are you sure you want to exit Daisy?",
            display_name="Daisy"
        )

        # 0-token confirmation via FastPath
        fp_res = FastPathEngine.handle_quick_music("yes do it")
        self.assertIsNotNone(fp_res)
        self.assertEqual(fp_res["mode"], "fastpath_confirmation")
        self.assertEqual(fp_res["tokens_consumed"], 0)
        self.assertFalse(hitl_manager.has_pending())

    def test_07_mcp_domain_tool_pruning(self):
        from backend.mcp.manager import mcp_manager

        all_tools = mcp_manager.get_all_tools_schema()
        media_tools = mcp_manager.get_domain_tools_schema(["media"])
        rag_tools = mcp_manager.get_domain_tools_schema(["rag"])

        # Domain pruning should significantly reduce the number of tools sent to LLM
        self.assertGreater(len(all_tools), len(media_tools))
        self.assertTrue(all("spotify" in t["name"] for t in media_tools))
        self.assertTrue(any("rag" in t["name"] for t in rag_tools))

    def test_08_rag_mcp_tools(self):
        from backend.mcp.manager import mcp_manager
        os.environ["DAISY_SEARCH_PATHS"] = str(self.cache_dir)

        # Query doc via MCP
        res = mcp_manager.execute("rag.query_desktop_doc", {
            "doc_name": "sample_test_doc",
            "query": "budget allocation"
        })
        self.assertTrue(res["success"])
        res_data = res["result"]
        self.assertEqual(res_data["status"], "success")
        self.assertIn("15000", res_data["context"])

        # Summarize doc via MCP
        res_sum = mcp_manager.execute("rag.summarize_desktop_doc", {
            "doc_name": "sample_test_doc"
        })
        self.assertTrue(res_sum["success"])
        self.assertEqual(res_sum["result"]["status"], "success")

    def test_09_fastapi_hitl_endpoints(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.hitl.manager import hitl_manager

        client = TestClient(app)

        # Initial state: no pending
        hitl_manager.clear()
        r = client.get("/hitl/pending")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["pending"])

        # Trigger confirmation
        hitl_manager.request_confirmation(
            action_type="close_app",
            tool_name="app_launcher.close_app",
            args={"app_name": "chrome"},
            prompt_message="Close Chrome?",
            display_name="Google Chrome"
        )
        r = client.get("/hitl/pending")
        self.assertTrue(r.json()["pending"])
        self.assertEqual(r.json()["action"]["display_name"], "Google Chrome")

        # Respond approve
        r_resp = client.post("/hitl/respond", json={"approved": True})
        self.assertEqual(r_resp.status_code, 200)
        self.assertEqual(r_resp.json()["status"], "executed")
        self.assertFalse(hitl_manager.has_pending())


if __name__ == "__main__":
    unittest.main(verbosity=2)
