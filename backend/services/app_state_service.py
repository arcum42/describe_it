from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.config import get_settings


DEFAULT_LLM_TIMEOUT_SECONDS = 120
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_OLLAMA_TIMEOUT_SECONDS: int | None = None
DEFAULT_LMSTUDIO_TIMEOUT_SECONDS: int | None = None
DEFAULT_OLLAMA_NUM_CTX: int | None = None
DEFAULT_LMSTUDIO_NUM_CTX: int | None = None
DEFAULT_REOPEN_LAST_PROJECT = True
DEFAULT_USE_PRESET_BY_DEFAULT = False
DEFAULT_SHOW_DEBUG_SECTION = False


def _db_path() -> Path:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings.state_dir / "app_state.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS llm_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            backend TEXT NOT NULL,
            model_name TEXT NOT NULL,
            caption_mode_strategy TEXT NOT NULL DEFAULT 'auto',
            system_prompt TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    preset_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(llm_presets)").fetchall()
    }
    if "caption_mode_strategy" not in preset_columns:
        connection.execute(
            "ALTER TABLE llm_presets ADD COLUMN caption_mode_strategy TEXT NOT NULL DEFAULT 'auto'"
        )
    if "tool_web_search" not in preset_columns:
        connection.execute(
            "ALTER TABLE llm_presets ADD COLUMN tool_web_search INTEGER NOT NULL DEFAULT 0"
        )
    if "tool_web_fetch" not in preset_columns:
        connection.execute(
            "ALTER TABLE llm_presets ADD COLUMN tool_web_fetch INTEGER NOT NULL DEFAULT 0"
        )
    if "context_url_template" not in preset_columns:
        connection.execute(
            "ALTER TABLE llm_presets ADD COLUMN context_url_template TEXT NOT NULL DEFAULT ''"
        )
    if "context_file_template" not in preset_columns:
        connection.execute(
            "ALTER TABLE llm_presets ADD COLUMN context_file_template TEXT NOT NULL DEFAULT ''"
        )
    connection.commit()


def _parse_optional_timeout(raw_value: str | None) -> int | None:
    if raw_value in {None, "", "null"}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return min(900, max(10, value))


def _parse_optional_num_ctx(raw_value: str | None) -> int | None:
    if raw_value in {None, "", "null"}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return min(262_144, max(256, value))


def _get_setting(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return row["value"]


def _set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def list_global_presets() -> list[dict[str, object]]:
    with _connect() as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            "SELECT id, name, backend, model_name, caption_mode_strategy, system_prompt, tool_web_search, tool_web_fetch, context_url_template, context_file_template FROM llm_presets ORDER BY name ASC, id ASC"
        ).fetchall()
    presets: list[dict[str, object]] = []
    for row in rows:
        preset = dict(row)
        preset["tool_web_search"] = bool(preset.get("tool_web_search"))
        preset["tool_web_fetch"] = bool(preset.get("tool_web_fetch"))
        presets.append(preset)
    return presets


def get_global_preset(*, preset_id: int) -> dict[str, object]:
    with _connect() as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT id, name, backend, model_name, caption_mode_strategy, system_prompt, tool_web_search, tool_web_fetch, context_url_template, context_file_template FROM llm_presets WHERE id = ?",
            (preset_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Preset not found: {preset_id}")
    preset = dict(row)
    preset["tool_web_search"] = bool(preset.get("tool_web_search"))
    preset["tool_web_fetch"] = bool(preset.get("tool_web_fetch"))
    return preset


def create_global_preset(
    *,
    name: str,
    backend: str,
    model_name: str,
    caption_mode_strategy: str,
    system_prompt: str,
    tool_web_search: bool,
    tool_web_fetch: bool,
    context_url_template: str,
    context_file_template: str,
) -> dict[str, object]:
    clean_name = name.strip()
    clean_model_name = model_name.strip()
    if not clean_name:
        raise ValueError("Preset name is required.")
    if not clean_model_name:
        raise ValueError("Preset model is required.")
    strategy = caption_mode_strategy.strip().lower()
    if strategy not in {"auto", "description", "tags"}:
        raise ValueError("Preset caption mode strategy must be one of: auto, description, tags.")

    with _connect() as connection:
        _ensure_schema(connection)
        duplicate = connection.execute("SELECT id FROM llm_presets WHERE name = ?", (clean_name,)).fetchone()
        if duplicate is not None:
            raise ValueError(f"A preset with this name already exists: {clean_name}")

        cursor = connection.execute(
            "INSERT INTO llm_presets(name, backend, model_name, caption_mode_strategy, system_prompt, tool_web_search, tool_web_fetch, context_url_template, context_file_template) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                clean_name,
                backend,
                clean_model_name,
                strategy,
                system_prompt,
                1 if tool_web_search else 0,
                1 if tool_web_fetch else 0,
                context_url_template,
                context_file_template,
            ),
        )
        connection.commit()
        preset_id = int(cursor.lastrowid)

    return get_global_preset(preset_id=preset_id)


def update_global_preset(
    *,
    preset_id: int,
    name: str,
    backend: str,
    model_name: str,
    caption_mode_strategy: str,
    system_prompt: str,
    tool_web_search: bool,
    tool_web_fetch: bool,
    context_url_template: str,
    context_file_template: str,
) -> dict[str, object]:
    clean_name = name.strip()
    clean_model_name = model_name.strip()
    if not clean_name:
        raise ValueError("Preset name is required.")
    if not clean_model_name:
        raise ValueError("Preset model is required.")
    strategy = caption_mode_strategy.strip().lower()
    if strategy not in {"auto", "description", "tags"}:
        raise ValueError("Preset caption mode strategy must be one of: auto, description, tags.")

    with _connect() as connection:
        _ensure_schema(connection)
        exists = connection.execute("SELECT id FROM llm_presets WHERE id = ?", (preset_id,)).fetchone()
        if exists is None:
            raise ValueError(f"Preset not found: {preset_id}")

        duplicate = connection.execute("SELECT id FROM llm_presets WHERE name = ? AND id != ?", (clean_name, preset_id)).fetchone()
        if duplicate is not None:
            raise ValueError(f"A preset with this name already exists: {clean_name}")

        connection.execute(
            "UPDATE llm_presets SET name = ?, backend = ?, model_name = ?, caption_mode_strategy = ?, system_prompt = ?, tool_web_search = ?, tool_web_fetch = ?, context_url_template = ?, context_file_template = ? WHERE id = ?",
            (
                clean_name,
                backend,
                clean_model_name,
                strategy,
                system_prompt,
                1 if tool_web_search else 0,
                1 if tool_web_fetch else 0,
                context_url_template,
                context_file_template,
                preset_id,
            ),
        )
        connection.commit()

    return get_global_preset(preset_id=preset_id)


def delete_global_preset(*, preset_id: int) -> dict[str, int]:
    with _connect() as connection:
        _ensure_schema(connection)
        cursor = connection.execute("DELETE FROM llm_presets WHERE id = ?", (preset_id,))
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Preset not found: {preset_id}")
    return {"deleted_preset_id": preset_id}


def get_global_settings() -> dict[str, object]:
    with _connect() as connection:
        _ensure_schema(connection)
        raw_timeout = _get_setting(connection, "llm_timeout_seconds")
        raw_use_preset = _get_setting(connection, "llm_use_preset_by_default")
        raw_default_preset_id = _get_setting(connection, "llm_default_preset_id")
        raw_show_debug_section = _get_setting(connection, "ui_show_debug_section")
        raw_ollama_base_url = _get_setting(connection, "ollama_base_url")
        raw_lmstudio_base_url = _get_setting(connection, "lmstudio_base_url")
        raw_ollama_timeout = _get_setting(connection, "ollama_timeout_seconds")
        raw_lmstudio_timeout = _get_setting(connection, "lmstudio_timeout_seconds")
        raw_ollama_num_ctx = _get_setting(connection, "ollama_num_ctx")
        raw_lmstudio_num_ctx = _get_setting(connection, "lmstudio_num_ctx")

    if raw_timeout is None:
        timeout_value = DEFAULT_LLM_TIMEOUT_SECONDS
    else:
        try:
            timeout_value = int(raw_timeout)
        except (TypeError, ValueError):
            timeout_value = DEFAULT_LLM_TIMEOUT_SECONDS
        timeout_value = min(900, max(10, timeout_value))

    try:
        default_preset_id = int(raw_default_preset_id) if raw_default_preset_id not in {None, "", "null"} else None
    except (TypeError, ValueError):
        default_preset_id = None

    use_preset_by_default = (
        DEFAULT_USE_PRESET_BY_DEFAULT
        if raw_use_preset is None
        else raw_use_preset.lower() in {"1", "true", "yes", "on"}
    )

    show_debug_section = (
        DEFAULT_SHOW_DEBUG_SECTION
        if raw_show_debug_section is None
        else raw_show_debug_section.lower() in {"1", "true", "yes", "on"}
    )

    ollama_base_url = (raw_ollama_base_url or "").strip() or DEFAULT_OLLAMA_BASE_URL
    lmstudio_base_url = (raw_lmstudio_base_url or "").strip() or DEFAULT_LMSTUDIO_BASE_URL

    ollama_timeout_seconds = _parse_optional_timeout(raw_ollama_timeout)
    if ollama_timeout_seconds is None:
        ollama_timeout_seconds = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    lmstudio_timeout_seconds = _parse_optional_timeout(raw_lmstudio_timeout)
    if lmstudio_timeout_seconds is None:
        lmstudio_timeout_seconds = DEFAULT_LMSTUDIO_TIMEOUT_SECONDS

    ollama_num_ctx = _parse_optional_num_ctx(raw_ollama_num_ctx)
    if ollama_num_ctx is None:
        ollama_num_ctx = DEFAULT_OLLAMA_NUM_CTX
    lmstudio_num_ctx = _parse_optional_num_ctx(raw_lmstudio_num_ctx)
    if lmstudio_num_ctx is None:
        lmstudio_num_ctx = DEFAULT_LMSTUDIO_NUM_CTX

    return {
        "llm_timeout_seconds": timeout_value,
        "llm_use_preset_by_default": use_preset_by_default,
        "llm_default_preset_id": default_preset_id,
        "ui_show_debug_section": show_debug_section,
        "ollama_base_url": ollama_base_url,
        "lmstudio_base_url": lmstudio_base_url,
        "ollama_timeout_seconds": ollama_timeout_seconds,
        "lmstudio_timeout_seconds": lmstudio_timeout_seconds,
        "ollama_num_ctx": ollama_num_ctx,
        "lmstudio_num_ctx": lmstudio_num_ctx,
    }


def update_global_settings(
    *,
    llm_timeout_seconds: int,
    llm_use_preset_by_default: bool,
    llm_default_preset_id: int | None,
    ui_show_debug_section: bool,
    ollama_base_url: str,
    lmstudio_base_url: str,
    ollama_timeout_seconds: int | None,
    lmstudio_timeout_seconds: int | None,
    ollama_num_ctx: int | None,
    lmstudio_num_ctx: int | None,
) -> dict[str, object]:
    timeout_value = min(900, max(10, int(llm_timeout_seconds)))
    clean_ollama_base_url = ollama_base_url.strip() or DEFAULT_OLLAMA_BASE_URL
    clean_lmstudio_base_url = lmstudio_base_url.strip() or DEFAULT_LMSTUDIO_BASE_URL
    clean_ollama_timeout = None if ollama_timeout_seconds is None else min(900, max(10, int(ollama_timeout_seconds)))
    clean_lmstudio_timeout = None if lmstudio_timeout_seconds is None else min(900, max(10, int(lmstudio_timeout_seconds)))
    clean_ollama_num_ctx = None if ollama_num_ctx is None else min(262_144, max(256, int(ollama_num_ctx)))
    clean_lmstudio_num_ctx = None if lmstudio_num_ctx is None else min(262_144, max(256, int(lmstudio_num_ctx)))
    with _connect() as connection:
        _ensure_schema(connection)
        _set_setting(connection, "llm_timeout_seconds", str(timeout_value))
        _set_setting(connection, "llm_use_preset_by_default", "true" if llm_use_preset_by_default else "false")
        _set_setting(connection, "llm_default_preset_id", "" if llm_default_preset_id is None else str(llm_default_preset_id))
        _set_setting(connection, "ui_show_debug_section", "true" if ui_show_debug_section else "false")
        _set_setting(connection, "ollama_base_url", clean_ollama_base_url)
        _set_setting(connection, "lmstudio_base_url", clean_lmstudio_base_url)
        _set_setting(connection, "ollama_timeout_seconds", "" if clean_ollama_timeout is None else str(clean_ollama_timeout))
        _set_setting(connection, "lmstudio_timeout_seconds", "" if clean_lmstudio_timeout is None else str(clean_lmstudio_timeout))
        _set_setting(connection, "ollama_num_ctx", "" if clean_ollama_num_ctx is None else str(clean_ollama_num_ctx))
        _set_setting(connection, "lmstudio_num_ctx", "" if clean_lmstudio_num_ctx is None else str(clean_lmstudio_num_ctx))
        connection.commit()
    return get_global_settings()


def get_project_session_state() -> dict[str, object]:
    with _connect() as connection:
        _ensure_schema(connection)
        last_project_path = _get_setting(connection, "last_project_path") or ""
        last_project_directory = _get_setting(connection, "last_project_directory") or ""
        raw_reopen = _get_setting(connection, "reopen_last_project")

    reopen_last_project = DEFAULT_REOPEN_LAST_PROJECT if raw_reopen is None else raw_reopen.lower() in {"1", "true", "yes", "on"}
    return {
        "last_project_path": last_project_path,
        "last_project_directory": last_project_directory,
        "reopen_last_project": reopen_last_project,
    }


def update_project_session_state(
    *,
    last_project_path: str,
    last_project_directory: str,
    reopen_last_project: bool,
) -> dict[str, object]:
    with _connect() as connection:
        _ensure_schema(connection)
        _set_setting(connection, "last_project_path", last_project_path.strip())
        _set_setting(connection, "last_project_directory", last_project_directory.strip())
        _set_setting(connection, "reopen_last_project", "true" if reopen_last_project else "false")
        connection.commit()
    return get_project_session_state()
