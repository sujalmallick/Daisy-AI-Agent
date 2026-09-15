import logging
from typing import Dict, Any, List
from backend.rag.retriever import desktop_rag

logger = logging.getLogger("daisy.mcp.rag")


class RagMCPServer:
    """
    Built-in Desktop RAG MCP Server.
    Enables Daisy to inspect local documents (.pdf, .txt, .md, .docx),
    perform vector similarity retrieval, and provide context-grounded answers.
    """

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query_desktop_doc",
                "description": "Searches for a document on user's Desktop or Documents and retrieves the most relevant excerpts for a specific query or question.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_name": {
                            "type": "string",
                            "description": "Name or keyword of the document (e.g. 'resume', 'tax_2025.pdf', 'meeting notes')"
                        },
                        "query": {
                            "type": "string",
                            "description": "The specific question or topic to search for inside the document"
                        }
                    },
                    "required": ["doc_name", "query"]
                }
            },
            {
                "name": "summarize_desktop_doc",
                "description": "Retrieves the main sections of a desktop document to create an executive summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doc_name": {
                            "type": "string",
                            "description": "Name or keyword of the document (e.g. 'project_plan.pdf', 'notes')"
                        }
                    },
                    "required": ["doc_name"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        try:
            if tool_name == "query_desktop_doc":
                doc_name = args.get("doc_name", "")
                query = args.get("query", "")
                if not doc_name or not query:
                    return {"error": "Both 'doc_name' and 'query' parameters are required."}
                return desktop_rag.query_document(doc_name, query)

            elif tool_name == "summarize_desktop_doc":
                doc_name = args.get("doc_name", "")
                if not doc_name:
                    return {"error": "Parameter 'doc_name' is required."}
                return desktop_rag.summarize_document(doc_name)

        except Exception as e:
            logger.error(f"Error in RAG MCP server: {e}", exc_info=True)
            return {"error": f"RAG execution failed: {str(e)}"}

        return {"error": f"Unknown RAG tool '{tool_name}'."}


# Register into MCP Manager
from backend.mcp.manager import mcp_manager
rag_server = RagMCPServer()
mcp_manager.register_server("rag", rag_server)
