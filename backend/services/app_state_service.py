from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.config import get_settings


DEFAULT_LLM_TIMEOUT_SECONDS = 120
DEFAULT_REOPEN_LAST_PROJECT = True
DEFAULT_USE_PRESET_BY_DEFAULT = False


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
            system_prompt TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    connection.commit()


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
            "SELECT id, name, backend, model_name, system_prompt FROM llm_presets ORDER BY name ASC, id ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_global_preset(*, preset_id: int) -> dict[str, object]:
    with _connect() as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT id, name, backend, model_name, system_prompt FROM llm_presets WHERE id = ?",
            (preset_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Preset not found: {preset_id}")
    return dict(row)


def create_global_preset(*, name: str, backend: str, model_name: str, system_prompt: str) -> dict[str, object]:
    clean_name = name.strip()
    clean_model_name = model_name.strip()
    if not clean_name:
        raise ValueError("Preset name is required.")
    if not clean_model_name:
        raise ValueError("Preset model is required.")

    with _connect() as connection:
        _ensure_schema(connection)
        duplicate = connection.execute("SELECT id FROM llm_presets WHERE name = ?", (clean_name,)).fetchone()
        if duplicate is not None:
            raise ValueError(f"A preset with this name already exists: {clean_name}")

        cursor = connection.execute(
            "INSERT INTO llm_presets(name, backend, model_name, system_prompt) VALUES(?, ?, ?, ?)",
            (clean_name, backend, clean_model_name, system_prompt),
        )
        connection.commit()
        preset_id = int(cursor.lastrowid)

    return get_global_preset(preset_id=preset_id)


def update_global_preset(*, preset_id: int, name: str, backend: str, model_name: str, system_prompt: str) -> dict[str, object]:
    clean_name = name.strip()
    clean_model_name = model_name.strip()
    if not clean_name:
        raise ValueError("Preset name is required.")
    if not clean_model_name:
        raise ValueError("Preset model is required.")

    with _connect() as connection:
        _ensure_schema(connection)
        exists = connection.execute("SELECT id FROM llm_presets WHERE id = ?", (preset_id,)).fetchone()
        if exists is None:
            raise ValueError(f"Preset not found: {preset_id}")

        duplicate = connection.execute("SELECT id FROM llm_presets WHERE name = ? AND id != ?", (clean_name, preset_id)).fetchone()
        if duplicate is not None:
            raise ValueError(f"A preset with this name already exists: {clean_name}")

        connection.execute(
            "UPDATE llm_presets SET name = ?, backend = ?, model_name = ?, system_prompt = ? WHERE id = ?",
            (clean_name, backend, clean_model_name, system_prompt, preset_id),
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

    return {
        "llm_timeout_seconds": timeout_value,
        "llm_use_preset_by_default": use_preset_by_default,
        "llm_default_preset_id": default_preset_id,
    }


def update_global_settings(
    *,
    llm_timeout_seconds: int,
    llm_use_preset_by_default: bool,
    llm_default_preset_id: int | None,
) -> dict[str, object]:
    timeout_value = min(900, max(10, int(llm_timeout_seconds)))
    with _connect() as connection:
        _ensure_schema(connection)
        _set_setting(connection, "llm_timeout_seconds", str(timeout_value))
        _set_setting(connection, "llm_use_preset_by_default", "true" if llm_use_preset_by_default else "false")
        _set_setting(connection, "llm_default_preset_id", "" if llm_default_preset_id is None else str(llm_default_preset_id))
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
