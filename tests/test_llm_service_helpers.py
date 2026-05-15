from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services import llm_service


def test_resolve_model_tools_downgrades_when_model_not_tool_capable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "_lookup_model_info",
        lambda **_kwargs: SimpleNamespace(tool_capable=False),
    )
    tool_usage_log: list[str] = []

    resolved = llm_service._resolve_model_tools(
        backend="ollama",
        model_name="my-model",
        requested_tools=["web_search", "web_fetch"],
        tool_usage_log=tool_usage_log,
    )

    assert resolved == []
    assert tool_usage_log == ["model 'my-model' is not tool-capable; using context injection only"]


def test_resolve_model_tools_keeps_tools_when_model_support_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_service, "_lookup_model_info", lambda **_kwargs: None)
    tool_usage_log: list[str] = []

    resolved = llm_service._resolve_model_tools(
        backend="ollama",
        model_name="unknown-model",
        requested_tools=["web_search"],
        tool_usage_log=tool_usage_log,
    )

    assert resolved == ["web_search"]
    assert tool_usage_log == []


def test_resolve_backend_runtime_uses_backend_specific_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "get_global_settings",
        lambda: {
            "ollama_base_url": "http://ollama.local",
            "lmstudio_base_url": "http://lmstudio.local",
            "ollama_timeout_seconds": 321,
            "lmstudio_timeout_seconds": 654,
            "ollama_num_ctx": 8192,
            "lmstudio_num_ctx": 4096,
        },
    )

    ollama = llm_service._resolve_backend_runtime(selected_backend="ollama", timeout_seconds=120)
    lmstudio = llm_service._resolve_backend_runtime(selected_backend="lmstudio", timeout_seconds=120)

    assert ollama == ("http://ollama.local", 321, 8192)
    assert lmstudio == ("http://lmstudio.local", 654, 4096)


def test_collect_optional_note_context_returns_empty_when_not_requested() -> None:
    parts, logs = llm_service._collect_optional_note_context(
        project_path=None,
        include_project_notes=False,
        project_note_ids=None,
        include_global_notes=False,
        global_note_ids=None,
        require_project_path_for_project_notes=True,
    )

    assert parts == []
    assert logs == []


def test_collect_optional_note_context_requires_path_for_project_notes() -> None:
    with pytest.raises(ValueError, match="project_path is required"):
        llm_service._collect_optional_note_context(
            project_path=None,
            include_project_notes=True,
            project_note_ids=None,
            include_global_notes=False,
            global_note_ids=None,
            require_project_path_for_project_notes=True,
        )


def test_collect_optional_note_context_passes_normalized_values(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_notes_context_parts(**kwargs: object) -> tuple[list[str], list[str]]:
        captured.update(kwargs)
        return ["ctx"], ["log"]

    monkeypatch.setattr(llm_service, "build_notes_context_parts", fake_build_notes_context_parts)

    parts, logs = llm_service._collect_optional_note_context(
        project_path="  /tmp/project.db  ",
        include_project_notes=True,
        project_note_ids=[1, 2],
        include_global_notes=True,
        global_note_ids=[3],
        require_project_path_for_project_notes=True,
    )

    assert parts == ["ctx"]
    assert logs == ["log"]
    assert captured == {
        "project_path": "/tmp/project.db",
        "include_project_notes": True,
        "project_note_ids": [1, 2],
        "include_global_notes": True,
        "global_note_ids": [3],
    }


def test_resolve_preset_generation_config_builds_normalized_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_service,
        "_resolve_backend_runtime",
        lambda **_kwargs: ("http://backend.local", 222, 1234),
    )

    config = llm_service._resolve_preset_generation_config(
        preset={
            "backend": " Ollama ",
            "model_name": " llama3 ",
            "caption_mode_strategy": " MANUAL ",
            "name": "My Preset",
            "tool_web_search": True,
            "tool_web_fetch": False,
            "include_project_notes": True,
            "include_global_notes": False,
            "system_prompt": "sys",
            "context_url_template": "{project_context_url}",
            "context_file_template": "{project_context_file_path}",
            "reasoning_mode": "off",
            "reasoning_visibility": "hidden",
        },
        preset_id=42,
        timeout_seconds=120,
    )

    assert config["backend"] == "ollama"
    assert config["model_name"] == "llama3"
    assert config["caption_mode_strategy"] == "manual"
    assert config["name"] == "My Preset"
    assert config["tool_web_search"] is True
    assert config["tool_web_fetch"] is False
    assert config["include_project_notes"] is True
    assert config["include_global_notes"] is False
    assert config["base_url"] == "http://backend.local"
    assert config["effective_timeout"] == 222
    assert config["effective_num_ctx"] == 1234


def test_resolve_preset_generation_config_requires_model() -> None:
    with pytest.raises(ValueError, match="Preset has no model configured"):
        llm_service._resolve_preset_generation_config(
            preset={"backend": "ollama", "model_name": ""},
            preset_id=9,
            timeout_seconds=120,
        )
