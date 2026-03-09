"""Local doc retrieval with sanitization of snippets."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Snippets containing these (case-insensitive) are filtered out to avoid injecting instructions
DANGEROUS_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "send credentials",
    "email me credentials",
]


def _sanitize_snippet(text: str) -> str:
    for phrase in DANGEROUS_PHRASES:
        if phrase.lower() in text.lower():
            return "[Content redacted for security]"
    return text


def load_docs(path: str) -> list[tuple[str, str]]:
    """Load all markdown files under path. Returns list of (file_path, content)."""
    root = Path(path)
    if not root.exists():
        return []
    out = []
    for f in root.glob("*.md"):
        try:
            out.append((str(f), f.read_text(encoding="utf-8")))
        except Exception:
            logger.warning("Failed to read %s, skipping", f)
            continue
    return out


def search(query: str, path: str | None = None, top_k: int = 5) -> list[dict]:
    """Simple keyword search over loaded docs. Returns list of {path, snippet}."""
    docs_path = path or os.environ.get("SUPPORT_DOCS_PATH", "")
    if not docs_path:
        return []
    docs = load_docs(docs_path)
    if not query or not query.strip():
        result = []
        for fp, content in docs[:top_k]:
            snippet = (content[:300] + "..." if len(content) > 300 else content).strip()
            result.append({"path": fp, "snippet": _sanitize_snippet(snippet)})
        return result
    query_lower = query.lower()
    scored = []
    for fp, content in docs:
        words = query_lower.split()
        score = sum(1 for w in words if w in content.lower())
        if score > 0:
            snippet = content[:400] + "..." if len(content) > 400 else content
            scored.append((score, fp, _sanitize_snippet(snippet)))
    scored.sort(key=lambda x: -x[0])
    return [{"path": p, "snippet": s} for _, p, s in scored[:top_k]]
