"""Pytest fixtures — shared TestClient for FastAPI."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped FastAPI test client (triggers lifespan)."""
    with TestClient(app) as c:
        yield c
