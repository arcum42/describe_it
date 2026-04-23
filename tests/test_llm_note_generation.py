"""Tests for POST /api/llm/generate-note-text endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_MOCK_RESULT = {
    "text": "This is a generated note.",
    "backend": "ollama",
    "model": "test-model",
    "generation_mode": "context_injection",
    "tool_usage_log": [],
}


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_missing_backend_returns_422() -> None:
    """Missing required 'backend' field → 422 Unprocessable Entity."""
    response = client.post(
        "/api/llm/generate-note-text",
        json={"model": "llama3", "prompt": "Write a note about cats."},
    )
    assert response.status_code == 422


def test_empty_prompt_returns_422() -> None:
    """Empty string prompt fails min_length=1 validation → 422."""
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "llama3", "prompt": ""},
    )
    assert response.status_code == 422


def test_empty_model_returns_422() -> None:
    """Empty string model fails min_length=1 validation → 422."""
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "", "prompt": "Write a note."},
    )
    assert response.status_code == 422


def test_timeout_below_minimum_returns_422() -> None:
    """timeout_seconds below 10 fails ge=10 validation → 422."""
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "llama3", "prompt": "Note.", "timeout_seconds": 5},
    )
    assert response.status_code == 422


def test_timeout_above_maximum_returns_422() -> None:
    """timeout_seconds above 900 fails le=900 validation → 422."""
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "llama3", "prompt": "Note.", "timeout_seconds": 9999},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Happy-path mock test
# ---------------------------------------------------------------------------

def test_generate_note_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid request with mocked service returns 200 with expected shape."""
    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        lambda **_kwargs: _MOCK_RESULT,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "test-model", "prompt": "Write a note."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "This is a generated note."
    assert payload["backend"] == "ollama"
    assert payload["model"] == "test-model"
    assert "generation_mode" in payload
    assert "tool_usage_log" in payload


def test_generate_note_text_all_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """All optional fields accepted without error."""
    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        lambda **_kwargs: _MOCK_RESULT,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={
            "backend": "ollama",
            "model": "test-model",
            "prompt": "Write about my project.",
            "project_path": "/tmp/project",
            "timeout_seconds": 60,
            "tools_enabled": ["web_search"],
            "context_urls": ["https://example.com"],
            "context_files": ["/tmp/context.txt"],
            "include_project_notes": True,
            "project_note_ids": [1, 2],
            "include_global_notes": True,
            "global_note_ids": [3],
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "This is a generated note."


def test_generate_note_text_with_image_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """image_id field is accepted and passed through."""
    received: dict = {}

    def _mock(**kwargs: object) -> dict:
        received.update(kwargs)
        return _MOCK_RESULT

    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        _mock,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={
            "backend": "ollama",
            "model": "test-model",
            "prompt": "Describe this image.",
            "project_path": "/tmp/project",
            "image_id": 42,
        },
    )
    assert response.status_code == 200
    assert received.get("image_id") == 42
    assert received.get("project_path") == "/tmp/project"


# ---------------------------------------------------------------------------
# Error propagation tests
# ---------------------------------------------------------------------------

def test_service_value_error_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError from service layer → 400 Bad Request."""
    def _raise(**_kwargs: object) -> None:
        raise ValueError("Unknown backend: bad_backend")

    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        _raise,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "bad_backend", "model": "llama3", "prompt": "Write something."},
    )
    assert response.status_code == 400
    assert "bad_backend" in response.json()["detail"]


def test_service_unexpected_error_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected exception from service layer → 500 Internal Server Error."""
    def _raise(**_kwargs: object) -> None:
        raise RuntimeError("Unexpected crash")

    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        _raise,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "ollama", "model": "llama3", "prompt": "Write something."},
    )
    assert response.status_code == 500
    assert "Unexpected" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Whitespace stripping test
# ---------------------------------------------------------------------------

def test_backend_and_model_are_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Leading/trailing whitespace in backend and model is stripped before calling service."""
    received: dict = {}

    def _mock(**kwargs: object) -> dict:
        received.update(kwargs)
        return _MOCK_RESULT

    monkeypatch.setattr(
        "backend.routers.llm.generate_note_text_with_tools",
        _mock,
    )
    response = client.post(
        "/api/llm/generate-note-text",
        json={"backend": "  ollama  ", "model": "  test-model  ", "prompt": "A note."},
    )
    assert response.status_code == 200
    assert received.get("backend") == "ollama"
    assert received.get("model") == "test-model"
