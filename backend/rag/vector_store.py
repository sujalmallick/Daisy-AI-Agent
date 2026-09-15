import os
import json
import math
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("daisy.rag.vector_store")

CACHE_DIR = Path(".daisy_cache")
INDEX_FILE = CACHE_DIR / "rag_index.json"


def _tokenize(text: str) -> List[str]:
    """Simple lowercase alphanumeric word tokenizer."""
    return re.findall(r"\b\w{2,}\b", text.lower())


class DesktopVectorStore:
    """
    Lightweight, zero-token local vector & lexical retrieval store.
    Uses TF-IDF and BM25 cosine scoring for instant, token-free semantic search.
    Caches document indices in .daisy_cache/rag_index.json with file mtime tracking.
    """

    def __init__(self):
        self._index: Dict[str, Any] = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def _load_cache(self):
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.debug(f"Could not load vector store cache: {e}")
                self._index = {}

    def _save_cache(self):
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not persist vector store cache: {e}")

    def is_cached_and_fresh(self, file_path: str) -> bool:
        """Returns True if the document is indexed and hasn't been modified."""
        norm_path = os.path.normpath(file_path)
        if norm_path not in self._index:
            return False
        entry = self._index[norm_path]
        try:
            current_mtime = os.path.getmtime(file_path)
            return entry.get("mtime") == current_mtime
        except OSError:
            return False

    def index_chunks(self, file_path: str, chunks: List[Dict[str, Any]]):
        """
        Indexes document chunks and computes term frequency statistics.
        """
        norm_path = os.path.normpath(file_path)
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            mtime = 0.0

        # Compute document frequencies across chunks
        doc_count = len(chunks)
        term_dfs: Dict[str, int] = {}
        processed_chunks = []

        for ch in chunks:
            tokens = _tokenize(ch["text"])
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for t in tf.keys():
                term_dfs[t] = term_dfs.get(t, 0) + 1

            processed_chunks.append({
                "chunk_id": ch["chunk_id"],
                "text": ch["text"],
                "file_path": file_path,
                "file_name": ch["file_name"],
                "tf": tf,
                "token_count": len(tokens)
            })

        # Calculate IDF for each term
        idfs: Dict[str, float] = {}
        for term, df in term_dfs.items():
            idfs[term] = math.log((doc_count - df + 0.5) / (df + 0.5) + 1.0)

        self._index[norm_path] = {
            "mtime": mtime,
            "file_name": Path(file_path).name,
            "chunks": processed_chunks,
            "idfs": idfs,
            "doc_count": doc_count
        }
        self._save_cache()

    def search(self, file_path: str, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Performs BM25 relevance ranking against chunks of the target document.
        Returns top_k most relevant chunks.
        """
        norm_path = os.path.normpath(file_path)
        if norm_path not in self._index:
            return []

        doc_data = self._index[norm_path]
        chunks = doc_data["chunks"]
        idfs = doc_data.get("idfs", {})
        doc_count = doc_data.get("doc_count", len(chunks))

        if not chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            # Return first top_k chunks if query is empty
            return chunks[:top_k]

        # Average chunk length
        avg_dl = sum(ch.get("token_count", 1) for ch in chunks) / max(len(chunks), 1)
        k1 = 1.5
        b = 0.75

        scored: List[tuple[float, Dict[str, Any]]] = []

        for ch in chunks:
            tf_map = ch.get("tf", {})
            doc_len = ch.get("token_count", 1)
            score = 0.0

            for q_term in query_tokens:
                if q_term in tf_map:
                    tf = tf_map[q_term]
                    idf = idfs.get(q_term, math.log(doc_count + 1))
                    # BM25 formula
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_len / max(avg_dl, 1)))
                    score += idf * (numerator / max(denominator, 1e-5))

            scored.append((score, ch))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, ch in scored[:top_k]:
            results.append({
                "chunk_id": ch["chunk_id"],
                "text": ch["text"],
                "file_path": ch["file_path"],
                "file_name": ch["file_name"],
                "score": round(score, 3)
            })

        return results


# Global singleton
desktop_vector_store = DesktopVectorStore()
