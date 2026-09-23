import logging
import urllib.parse
import webbrowser
from typing import Dict, Any, List

logger = logging.getLogger("daisy.mcp.web")


class WebMCPServer:
    """
    Built-in Web & Browser Automation MCP Server.
    Empowers Daisy to actively assist users by searching YouTube, Google,
    or opening web applications in the default browser in < 10ms with 0 tokens.
    """

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_youtube",
                "description": "Searches YouTube for a music video, tutorial, song, or channel and opens it directly in the user's default web browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search term, song title, artist, tutorial topic, or video title to search on YouTube."
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_google",
                "description": "Performs a Google web search and displays the results in the user's default browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search keywords, question, or phrase to search on Google."
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "open_url",
                "description": "Opens any target website, web application, or URL in the user's default browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full HTTP/HTTPS URL or web domain to open (e.g. 'https://github.com')."
                        }
                    },
                    "required": ["url"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "search_youtube":
            raw_query = str(arguments.get("query", "")).strip()
            if not raw_query:
                return {"error": "Query cannot be empty for YouTube search."}

            encoded = urllib.parse.quote_plus(raw_query)
            target_url = f"https://www.youtube.com/results?search_query={encoded}"

            try:
                webbrowser.open(target_url)
                logger.info(f"[WebMCP] Opened YouTube search for '{raw_query}' -> {target_url}")
                return {
                    "action": "search_youtube",
                    "query": raw_query,
                    "url": target_url,
                    "status": "opened",
                    "card_type": "youtube",
                    "card_data": {
                        "query": raw_query,
                        "url": target_url,
                        "platform": "YouTube"
                    },
                    "message": f"Opened YouTube search for '{raw_query}'."
                }
            except Exception as e:
                logger.error(f"[WebMCP] Failed to open YouTube: {e}")
                return {"error": f"Failed to open YouTube: {str(e)}"}

        elif tool_name == "search_google":
            raw_query = str(arguments.get("query", "")).strip()
            if not raw_query:
                return {"error": "Query cannot be empty for Google search."}

            encoded = urllib.parse.quote_plus(raw_query)
            target_url = f"https://www.google.com/search?q={encoded}"

            try:
                webbrowser.open(target_url)
                logger.info(f"[WebMCP] Opened Google search for '{raw_query}' -> {target_url}")
                return {
                    "action": "search_google",
                    "query": raw_query,
                    "url": target_url,
                    "status": "opened",
                    "card_type": "web",
                    "card_data": {
                        "query": raw_query,
                        "url": target_url,
                        "platform": "Google"
                    },
                    "message": f"Opened Google search for '{raw_query}'."
                }
            except Exception as e:
                logger.error(f"[WebMCP] Failed to open Google: {e}")
                return {"error": f"Failed to open Google: {str(e)}"}

        elif tool_name == "open_url":
            raw_url = str(arguments.get("url", "")).strip()
            if not raw_url:
                return {"error": "URL cannot be empty."}

            if not raw_url.startswith(("http://", "https://")):
                target_url = f"https://{raw_url}"
            else:
                target_url = raw_url

            try:
                webbrowser.open(target_url)
                logger.info(f"[WebMCP] Opened URL: {target_url}")
                return {
                    "action": "open_url",
                    "url": target_url,
                    "status": "opened",
                    "card_type": "web",
                    "card_data": {
                        "query": raw_url,
                        "url": target_url,
                        "platform": "Web"
                    },
                    "message": f"Opened {target_url} in browser."
                }
            except Exception as e:
                logger.error(f"[WebMCP] Failed to open URL '{target_url}': {e}")
                return {"error": f"Failed to open URL: {str(e)}"}

        return {"error": f"Unknown Web tool: '{tool_name}'."}


# Instantiate and register into MCP Manager
from backend.mcp.manager import mcp_manager
web_server = WebMCPServer()
mcp_manager.register_server("web", web_server)
