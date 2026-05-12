from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.native_picker_service import NativePickerResult

client = TestClient(app)


def test_native_picker_returns_selected_path(monkeypatch) -> None:
    def fake_picker(*, kind: str, title: str, start_path: str | None = None) -> NativePickerResult:
        assert kind == "db_file"
        assert "project database" in title.lower()
        assert start_path == "/tmp"
        return NativePickerResult(available=True, selected_path="/tmp/project.db", backend="fake")

    monkeypatch.setattr("backend.routers.projects.open_native_path_picker", fake_picker)

    response = client.post(
        "/api/projects/native-picker",
        json={"kind": "db_file", "title": "Select project database", "start_path": "/tmp"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["selected_path"] == "/tmp/project.db"
    assert payload["backend"] == "fake"
    assert payload["reason"] is None


def test_native_picker_handles_unavailable_backend(monkeypatch) -> None:
    def fake_picker(*, kind: str, title: str, start_path: str | None = None) -> NativePickerResult:
        return NativePickerResult(available=False, selected_path=None, reason="No GUI session", backend=None)

    monkeypatch.setattr("backend.routers.projects.open_native_path_picker", fake_picker)

    response = client.post(
        "/api/projects/native-picker",
        json={"kind": "directory", "title": "Select export folder", "start_path": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["selected_path"] is None
    assert payload["reason"] == "No GUI session"
    assert payload["backend"] is None


def test_native_picker_request_validation() -> None:
    response = client.post(
        "/api/projects/native-picker",
        json={"kind": "invalid_kind", "title": "Select", "start_path": ""},
    )
    assert response.status_code == 422


def test_native_picker_setting_round_trip() -> None:
    get_resp = client.get("/api/llm/settings")
    assert get_resp.status_code == 200
    original = get_resp.json()

    update_payload = {
        "llm_timeout_seconds": original.get("llm_timeout_seconds", 120),
        "llm_use_preset_by_default": original.get("llm_use_preset_by_default", False),
        "llm_default_preset_id": original.get("llm_default_preset_id"),
        "ui_show_debug_section": original.get("ui_show_debug_section", False),
        "ui_use_native_path_picker": False,
        "ollama_base_url": original.get("ollama_base_url", "http://127.0.0.1:11434"),
        "lmstudio_base_url": original.get("lmstudio_base_url", "http://127.0.0.1:1234"),
        "ollama_timeout_seconds": original.get("ollama_timeout_seconds"),
        "lmstudio_timeout_seconds": original.get("lmstudio_timeout_seconds"),
        "ollama_num_ctx": original.get("ollama_num_ctx"),
        "lmstudio_num_ctx": original.get("lmstudio_num_ctx"),
        "editor_default_image_zoom_mode": original.get("editor_default_image_zoom_mode", "fit"),
        "editor_default_image_zoom_percent": original.get("editor_default_image_zoom_percent", 100),
    }

    update_resp = client.post("/api/llm/settings", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["ui_use_native_path_picker"] is False

    restore_payload = dict(update_payload)
    restore_payload["ui_use_native_path_picker"] = bool(original.get("ui_use_native_path_picker", True))
    restore_resp = client.post("/api/llm/settings", json=restore_payload)
    assert restore_resp.status_code == 200


def test_panel_state_round_trip() -> None:
    get_resp = client.get("/api/llm/settings")
    assert get_resp.status_code == 200
    original = get_resp.json()

    update_payload = {
        "llm_timeout_seconds": original.get("llm_timeout_seconds", 120),
        "llm_use_preset_by_default": original.get("llm_use_preset_by_default", False),
        "llm_default_preset_id": original.get("llm_default_preset_id"),
        "ui_show_debug_section": original.get("ui_show_debug_section", False),
        "ui_use_native_path_picker": original.get("ui_use_native_path_picker", True),
        "ollama_base_url": original.get("ollama_base_url", "http://127.0.0.1:11434"),
        "lmstudio_base_url": original.get("lmstudio_base_url", "http://127.0.0.1:1234"),
        "ollama_timeout_seconds": original.get("ollama_timeout_seconds"),
        "lmstudio_timeout_seconds": original.get("lmstudio_timeout_seconds"),
        "ollama_num_ctx": original.get("ollama_num_ctx"),
        "lmstudio_num_ctx": original.get("lmstudio_num_ctx"),
        "editor_default_image_zoom_mode": original.get("editor_default_image_zoom_mode", "fit"),
        "editor_default_image_zoom_percent": original.get("editor_default_image_zoom_percent", 100),
        "ui_panel_state": {"editorLLM": False, "notesAssistant": False, "ioImport": True},
    }

    update_resp = client.post("/api/llm/settings", json=update_payload)
    assert update_resp.status_code == 200
    panel_state = update_resp.json().get("ui_panel_state", {})
    assert panel_state.get("editorLLM") is False
    assert panel_state.get("notesAssistant") is False
    assert panel_state.get("ioImport") is True

    restore_payload = dict(update_payload)
    restore_payload["ui_panel_state"] = original.get("ui_panel_state", {})
    restore_resp = client.post("/api/llm/settings", json=restore_payload)
    assert restore_resp.status_code == 200
