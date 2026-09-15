import re
from pathlib import Path
from typing import List, Dict, Any


class TextChunker:
    """
    Sentence-boundary aware text chunker with sliding window overlap.
    Tailored for token-efficient desktop RAG queries.
    """

    def __init__(self, chunk_size: int = 450, chunk_overlap: int = 70):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, text: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Splits a document text into structured chunks.
        """
        if not text or not text.strip():
            return []

        clean_text = re.sub(r"\r\n", "\n", text).strip()
        filename = Path(file_path).name

        # If document is short enough, return as a single chunk
        if len(clean_text) <= self.chunk_size:
            return [{
                "chunk_id": 0,
                "text": clean_text,
                "file_path": file_path,
                "file_name": filename,
                "char_start": 0,
                "char_end": len(clean_text)
            }]

        chunks: List[Dict[str, Any]] = []
        start = 0
        text_len = len(clean_text)
        chunk_id = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # If not at the end of the text, look for a natural boundary
            if end < text_len:
                # Look backwards for paragraph break, period, question mark, or newline
                boundary = -1
                for sep in ["\n\n", ".\n", ". ", "?\n", "? ", "!\n", "! ", "\n", " "]:
                    found = clean_text.rfind(sep, start + self.chunk_size // 2, end)
                    if found != -1:
                        boundary = found + len(sep)
                        break

                if boundary != -1:
                    end = boundary

            chunk_content = clean_text[start:end].strip()
            if chunk_content:
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_content,
                    "file_path": file_path,
                    "file_name": filename,
                    "char_start": start,
                    "char_end": end
                })
                chunk_id += 1

            if end >= text_len:
                break

            # Move forward by chunk_size - overlap
            start = max(end - self.chunk_overlap, start + 1)

        return chunks
