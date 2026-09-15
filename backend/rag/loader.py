import os
import re
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

logger = logging.getLogger("daisy.rag.loader")


class DocumentLoader:
    """
    Extracts plain text from local desktop files (.pdf, .txt, .md, .docx).
    Handles encoding, formatting cleanup, and extraction errors gracefully.
    """

    @classmethod
    def load_text(cls, file_path: str, max_chars: int = 150000) -> Optional[str]:
        """Loads and extracts text content from the specified file path."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning(f"File not found: {file_path}")
            return None

        ext = path.suffix.lower()

        try:
            if ext in (".txt", ".md", ".log", ".csv", ".json"):
                return cls._load_plain_text(path, max_chars)
            elif ext == ".pdf":
                return cls._load_pdf(path, max_chars)
            elif ext == ".docx":
                return cls._load_docx(path, max_chars)
            else:
                logger.warning(f"Unsupported file format: {ext}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None

    @staticmethod
    def _load_plain_text(path: Path, max_chars: int) -> str:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    text = f.read(max_chars)
                    return text.strip()
            except (UnicodeDecodeError, OSError):
                continue
        # Fallback with ignore errors
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars).strip()

    @staticmethod
    def _load_pdf(path: Path, max_chars: int) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            extracted_pages = []
            total_chars = 0

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                if page_text:
                    extracted_pages.append(page_text)
                    total_chars += len(page_text)
                if total_chars >= max_chars:
                    break

            combined = "\n\n".join(extracted_pages)
            return re.sub(r"\n{3,}", "\n\n", combined).strip()
        except ImportError:
            logger.error("pypdf is not installed. PDF extraction unavailable.")
            return ""

    @staticmethod
    def _load_docx(path: Path, max_chars: int) -> str:
        """Extracts text from .docx by parsing word/document.xml inside the zip container."""
        try:
            with zipfile.ZipFile(str(path)) as docx_zip:
                xml_content = docx_zip.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                # Word XML namespace
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for p in tree.iterfind(".//w:p", namespaces):
                    texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                    if sum(len(p) for p in paragraphs) >= max_chars:
                        break
                return "\n\n".join(paragraphs).strip()
        except Exception as e:
            logger.warning(f"Failed to parse .docx container for {path}: {e}")
            return ""
