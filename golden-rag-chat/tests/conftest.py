"""Shared test fixtures.

Pins the golden-data directory to the bundled fixtures (absolute path, so tests
pass regardless of the working directory) and exposes a FastAPI test client with
caches cleared per test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# Set before importing the app so Settings picks it up.
os.environ["GRC_GOLDEN_DATA_DIR"] = str(FIXTURES_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from golden_rag_chat.api.dependencies import get_chat_service  # noqa: E402
from golden_rag_chat.api.main import create_app  # noqa: E402
from golden_rag_chat.config import get_settings  # noqa: E402


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture()
def client() -> TestClient:
    get_settings.cache_clear()
    get_chat_service.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_chat_service.cache_clear()
    get_settings.cache_clear()
