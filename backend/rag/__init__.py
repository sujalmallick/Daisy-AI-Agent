"""
Daisy Desktop RAG (Retrieval-Augmented Generation) Engine.
Enables local document ingestion, chunking, and semantic retrieval from user desktop.
"""
from backend.rag.retriever import desktop_rag

__all__ = ["desktop_rag"]
