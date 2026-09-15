import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("daisy.rag.path_resolver")

BLOCKED_PATTERNS = [
    ".env", ".git", ".cache", "id_rsa", "id_ed25519", "id_dsa",
    "authorized_keys", "known_hosts", "credentials", ".aws",
    "passwd", "shadow", "sam", "system32", "windows", "ntds.dit", ".ssh",
    "node_modules", "venv", "__pycache__"
]

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md", ".docx")


def is_safe_path(target_path: str) -> bool:
    """Validates that a path does not target sensitive system files, keys, or credentials."""
    if not target_path:
        return False
    try:
        normalized = os.path.normpath(os.path.abspath(os.path.expanduser(target_path)))
        parts = normalized.lower().split(os.sep)
        for part in parts:
            for blocked in BLOCKED_PATTERNS:
                if part == blocked or (blocked.startswith(".") and part == blocked):
                    return False
                # For Windows SAM file (C:\Windows\System32\config\SAM), check exact stem
                if blocked == "sam" and (part == "sam" or part.startswith("sam.")):
                    return False
                if blocked in ["id_rsa", "id_ed25519", "id_dsa", "authorized_keys", "known_hosts", "credentials", "passwd", "shadow", "system32", "ntds.dit"] and blocked in part:
                    return False
        return True
    except Exception:
        return False


def get_search_directories() -> List[Path]:
    """
    Returns the list of directories to scan for user documents.
    Defaults to Desktop, Documents, and Downloads.
    Also parses DAISY_SEARCH_PATHS environment variable if provided.
    """
    home = Path.home()
    dirs: List[Path] = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads"
    ]

    # Additional custom paths from environment
    custom_paths = os.getenv("DAISY_SEARCH_PATHS", "")
    if custom_paths:
        for p_str in custom_paths.split(","):
            p_str = p_str.strip()
            if p_str:
                expanded = Path(os.path.expanduser(p_str)).resolve()
                if expanded.exists() and expanded.is_dir() and is_safe_path(str(expanded)):
                    if expanded not in dirs:
                        dirs.append(expanded)

    # Filter only existing directories
    valid_dirs = [d for d in dirs if d.exists() and d.is_dir() and is_safe_path(str(d))]
    return valid_dirs


def find_matching_files(doc_name: str, extensions: tuple = SUPPORTED_EXTENSIONS) -> List[str]:
    """
    Searches for documents matching doc_name across user directories.
    Handles exact names, names without extension, or substring matching.
    Returns a list of absolute file paths sorted by match quality.
    """
    if not doc_name or not doc_name.strip():
        return []

    clean_query = doc_name.strip().lower()
    # Strip extension if provided for uniform matching
    query_stem = Path(clean_query).stem.lower()

    directories = get_search_directories()
    candidates: List[tuple[int, float, str]] = []  # (priority, mtime, path)

    for search_dir in directories:
        try:
            # Shallow + 1-level deep search to keep scanning fast (<50ms)
            for item in search_dir.iterdir():
                if item.is_file():
                    _check_file(item, clean_query, query_stem, extensions, candidates)
                elif item.is_dir() and not item.name.startswith("."):
                    # Scan subfolders one level deep (e.g. Desktop/Project/notes.txt)
                    try:
                        for sub_item in item.iterdir():
                            if sub_item.is_file():
                                _check_file(sub_item, clean_query, query_stem, extensions, candidates)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError) as e:
            logger.debug(f"Could not read directory {search_dir}: {e}")
            continue

    # Sort candidates by:
    # 1. priority (0 = exact filename, 1 = exact stem, 2 = query in stem, 3 = stem in query)
    # 2. modified time (newest first)
    candidates.sort(key=lambda x: (x[0], -x[1]))

    # Return top 5 unique paths
    seen = set()
    result = []
    for _, _, path_str in candidates:
        if path_str not in seen:
            seen.add(path_str)
            result.append(path_str)
        if len(result) >= 5:
            break

    return result


def _check_file(
    file_path: Path,
    clean_query: str,
    query_stem: str,
    extensions: tuple,
    candidates: List[tuple[int, float, str]]
):
    if not is_safe_path(str(file_path)):
        return

    ext = file_path.suffix.lower()
    if ext not in extensions:
        return

    name_lower = file_path.name.lower()
    stem_lower = file_path.stem.lower()

    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        mtime = 0.0

    path_str = str(file_path.resolve())

    # Match ranking:
    if name_lower == clean_query:
        candidates.append((0, mtime, path_str))
    elif stem_lower == query_stem or stem_lower == clean_query:
        candidates.append((1, mtime, path_str))
    elif query_stem in stem_lower:
        candidates.append((2, mtime, path_str))
    elif stem_lower in query_stem and len(stem_lower) >= 3:
        candidates.append((3, mtime, path_str))
