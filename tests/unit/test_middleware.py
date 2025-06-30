"""Tests for middleware components."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from boxdrive import create_app
from boxdrive.stores import InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def app(store: InMemoryStore) -> FastAPI:
    return create_app(store)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_logging_middleware_integration(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Test that logging middleware is properly integrated and logs requests."""
    with caplog.at_level(logging.INFO):
        response = client.get("/")
        assert response.status_code == 200

        log_messages = [record.message for record in caplog.records]
        assert any("Request info" in msg for msg in log_messages)
        assert any("Response info" in msg for msg in log_messages)
