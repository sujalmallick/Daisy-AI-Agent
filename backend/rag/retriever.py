import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.rag.path_resolver import find_matching_files
from backend.rag.loader import DocumentLoader
from backend.rag.chunker import TextChunker
from backend.rag.vector_store import desktop_vector_store

logger = logging.getLogger("daisy.rag.retriever")


class DesktopRAGRetriever:
    """
    High-level Desktop RAG coordinator:
    - Locates user documents across Desktop, Documents, Downloads.
    - Handles disambiguation when multiple documents match.
    - Chunks, indexes, and retrieves top-k excerpts for token-efficient LLM answering.
    """

    def __init__(self):
        self.chunker = TextChunker(chunk_size=450, chunk_overlap=70)

    def resolve_and_index(self, doc_name: str) -> Dict[str, Any]:
        """
        Locates a document matching doc_name.
        Returns:
            - {"status": "not_found", "doc_name": doc_name}
            - {"status": "multiple_candidates", "candidates": [...]}
            - {"status": "ready", "file_path": str, "file_name": str}
        """
        matches = find_matching_files(doc_name)
        if not matches:
            return {
                "status": "not_found",
                "doc_name": doc_name,
                "error": f"Could not find any document matching '{doc_name}' on your Desktop or Documents."
            }

        if len(matches) > 1:
            # Check if one is an exact match
            exact = [m for m in matches if Path(m).stem.lower() == doc_name.strip().lower()]
            if len(exact) == 1:
                target_path = exact[0]
            else:
                return {
                    "status": "multiple_candidates",
                    "doc_name": doc_name,
                    "candidates": [Path(m).name for m in matches],
                    "candidate_paths": matches,
                    "message": f"I found {len(matches)} files matching '{doc_name}': {', '.join(Path(m).name for m in matches[:3])}. Which one would you like?"
                }
        else:
            target_path = matches[0]

        # Index document if not cached or modified
        if not desktop_vector_store.is_cached_and_fresh(target_path):
            text = DocumentLoader.load_text(target_path)
            if not text:
                return {
                    "status": "read_error",
                    "file_path": target_path,
                    "error": f"Unable to read text from {Path(target_path).name}."
                }
            chunks = self.chunker.chunk_document(text, target_path)
            desktop_vector_store.index_chunks(target_path, chunks)

        return {
            "status": "ready",
            "file_path": target_path,
            "file_name": Path(target_path).name
        }

    def query_document(self, doc_name: str, query: str, top_k: int = 2) -> Dict[str, Any]:
        """
        Retrieves top_k relevant snippets from doc_name matching query.
        Returns structured context ready for LLM synthesis.
        """
        resolved = self.resolve_and_index(doc_name)
        if resolved["status"] != "ready":
            return resolved

        file_path = resolved["file_path"]
        chunks = desktop_vector_store.search(file_path, query, top_k=top_k)

        if not chunks:
            return {
                "status": "no_relevant_content",
                "file_name": resolved["file_name"],
                "file_path": file_path,
                "context": "",
                "message": f"Found no specific details in {resolved['file_name']} about '{query}'."
            }

        context_text = "\n\n---\n\n".join(f"[Excerpt {i+1}]:\n{c['text']}" for i, c in enumerate(chunks))

        return {
            "status": "success",
            "file_name": resolved["file_name"],
            "file_path": file_path,
            "chunk_count": len(chunks),
            "context": context_text,
            "chunks": chunks
        }

    def summarize_document(self, doc_name: str) -> Dict[str, Any]:
        """
        Provides a concise excerpt set for document summarization.
        """
        resolved = self.resolve_and_index(doc_name)
        if resolved["status"] != "ready":
            return resolved

        file_path = resolved["file_path"]
        # Search for overview / summary / introduction keywords or take the first 2 chunks
        chunks = desktop_vector_store.search(file_path, "summary introduction overview conclusion key points", top_k=3)
        context_text = "\n\n---\n\n".join(f"[Section {i+1}]:\n{c['text']}" for i, c in enumerate(chunks))

        return {
            "status": "success",
            "file_name": resolved["file_name"],
            "file_path": file_path,
            "chunk_count": len(chunks),
            "context": context_text,
            "chunks": chunks
        }


# Global singleton
desktop_rag = DesktopRAGRetriever()
