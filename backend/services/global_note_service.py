from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.config import get_settings
from backend.services.rag_service import rag_service

_ALLOWED_FORMATS = {"text", "markdown"}


@dataclass
class GlobalNoteItem:
    id: int
    title: str
    content: str
    format: str
    tags: str
    is_archived: bool
    created_at: str
    updated_at: str


def _db_path() -> Path:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings.state_dir / "app_state.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS global_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            format TEXT NOT NULL DEFAULT 'markdown',
            tags TEXT NOT NULL DEFAULT '',
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def _validate_format(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _ALLOWED_FORMATS:
        raise ValueError("Note format must be one of: text, markdown.")
    return normalized


def _to_item(row: sqlite3.Row) -> GlobalNoteItem:
    return GlobalNoteItem(
        id=int(row["id"]),
        title=str(row["title"] or ""),
        content=str(row["content"] or ""),
        format=str(row["format"] or "markdown"),
        tags=str(row["tags"] or ""),
        is_archived=bool(row["is_archived"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def list_global_notes(*, include_archived: bool = True) -> list[GlobalNoteItem]:
    with _connect() as connection:
        _ensure_schema(connection)
        query = "SELECT id, title, content, format, tags, is_archived, created_at, updated_at FROM global_notes"
        params: tuple[object, ...] = ()
        if not include_archived:
            query += " WHERE is_archived = 0"
        query += " ORDER BY updated_at DESC, id DESC"
        rows = connection.execute(query, params).fetchall()
    return [_to_item(row) for row in rows]


def create_global_note(*, title: str, content: str, format: str, tags: str = "") -> GlobalNoteItem:
    normalized_format = _validate_format(format)
    with _connect() as connection:
        _ensure_schema(connection)
        cursor = connection.execute(
            "INSERT INTO global_notes(title, content, format, tags, is_archived) VALUES(?, ?, ?, ?, 0)",
            ((title or "").strip(), content or "", normalized_format, (tags or "").strip()),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, title, content, format, tags, is_archived, created_at, updated_at FROM global_notes WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
    if row is None:
        raise ValueError("Failed to create global note.")
    item = _to_item(row)
    rag_service.upsert_global_note(
        note_id=item.id,
        title=item.title,
        content=item.content,
        tags=item.tags,
        format=item.format,
        updated_at=item.updated_at,
    )
    return item


def update_global_note(
    *,
    note_id: int,
    title: str,
    content: str,
    format: str,
    tags: str,
    is_archived: bool,
) -> GlobalNoteItem:
    normalized_format = _validate_format(format)
    with _connect() as connection:
        _ensure_schema(connection)
        existing = connection.execute("SELECT id FROM global_notes WHERE id = ?", (note_id,)).fetchone()
        if existing is None:
            raise ValueError(f"Global note not found: {note_id}")

        connection.execute(
            """
            UPDATE global_notes
            SET title = ?, content = ?, format = ?, tags = ?, is_archived = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            ((title or "").strip(), content or "", normalized_format, (tags or "").strip(), 1 if is_archived else 0, note_id),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, title, content, format, tags, is_archived, created_at, updated_at FROM global_notes WHERE id = ?",
            (note_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Global note not found: {note_id}")
    item = _to_item(row)
    rag_service.upsert_global_note(
        note_id=item.id,
        title=item.title,
        content=item.content,
        tags=item.tags,
        format=item.format,
        updated_at=item.updated_at,
    )
    return item


def delete_global_note(*, note_id: int) -> dict[str, int]:
    with _connect() as connection:
        _ensure_schema(connection)
        cursor = connection.execute("DELETE FROM global_notes WHERE id = ?", (note_id,))
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Global note not found: {note_id}")
    rag_service.delete_global_note(note_id=note_id)
    return {"deleted_note_id": note_id}
