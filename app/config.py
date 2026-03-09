"""Load config from environment."""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def get_config(require_api_key: bool = False):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    db_path = os.environ.get("SUPPORT_DB_PATH", str(_REPO_ROOT / "data" / "support.db"))
    docs_path = os.environ.get("SUPPORT_DOCS_PATH", str(_REPO_ROOT / "data" / "docs"))
    if require_api_key and not api_key:
        raise ValueError("OPENAI_API_KEY is required but not set")
    return {
        "openai_api_key": api_key,
        "support_db_path": db_path,
        "support_docs_path": docs_path,
    }
