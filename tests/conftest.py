"""Pytest fixtures for support agent tests."""
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def db_path(tmp_path):
    """Temporary DB path. Caller must run init_db or create schema."""
    return str(tmp_path / "support.db")


@pytest.fixture
def docs_path():
    """Path to checked-in docs."""
    return str(REPO_ROOT / "data" / "docs")


@pytest.fixture
def env_config(db_path, docs_path):
    """Set env vars for DB and docs; restore after."""
    old_db = os.environ.get("SUPPORT_DB_PATH")
    old_docs = os.environ.get("SUPPORT_DOCS_PATH")
    os.environ["SUPPORT_DB_PATH"] = db_path
    os.environ["SUPPORT_DOCS_PATH"] = docs_path
    yield {"support_db_path": db_path, "support_docs_path": docs_path}
    if old_db is not None:
        os.environ["SUPPORT_DB_PATH"] = old_db
    else:
        os.environ.pop("SUPPORT_DB_PATH", None)
    if old_docs is not None:
        os.environ["SUPPORT_DOCS_PATH"] = old_docs
    else:
        os.environ.pop("SUPPORT_DOCS_PATH", None)


@pytest.fixture
def sample_messages():
    return [
        {"role": "user", "content": "What plan is ACME-001 on?"},
    ]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for component tests."""
    return MagicMock()


@pytest.fixture
def agent_instance(env_config, db_path, docs_path):
    """Agent run with real DB and docs; OpenAI must be mocked when needed."""
    from app.agent import run
    # Ensure DB exists and is populated for integration tests
    return run
