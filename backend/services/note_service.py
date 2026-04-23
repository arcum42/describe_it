from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import NoteRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.services.rag_service import rag_service

_ALLOWED_FORMATS = {"text", "markdown"}


@dataclass
class NoteItem:
    id: int
    project_id: int
    title: str
    content: str
    format: str
    tags: str
    is_archived: bool
    created_at: str
    updated_at: str


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _validate_format(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _ALLOWED_FORMATS:
        raise ValueError("Note format must be one of: text, markdown.")
    return normalized


def _serialize_note(note: NoteRecord) -> NoteItem:
    return NoteItem(
        id=note.id,
        project_id=note.project_id,
        title=note.title,
        content=note.content,
        format=note.format,
        tags=note.tags,
        is_archived=bool(note.is_archived),
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


def _load_project(session, project_path: Path) -> ProjectRecord:
    project = session.scalar(select(ProjectRecord).limit(1))
    if project is None:
        raise ValueError(f"Project database has no project metadata: {project_path}")
    return project


def list_notes(*, project_path: str, include_archived: bool = True) -> list[NoteItem]:
    resolved = _resolve_path(project_path)
    if not resolved.exists():
        raise ValueError(f"Project file does not exist: {resolved}")

    session_factory = create_sqlite_session_factory(resolved)
    with session_factory() as session:
        project = _load_project(session, resolved)
        query = select(NoteRecord).where(NoteRecord.project_id == project.id)
        if not include_archived:
            query = query.where(NoteRecord.is_archived.is_(False))
        notes = session.scalars(query.order_by(NoteRecord.updated_at.desc(), NoteRecord.id.desc())).all()
        return [_serialize_note(note) for note in notes]


def create_note(
    *,
    project_path: str,
    title: str,
    content: str,
    format: str,
    tags: str = "",
) -> NoteItem:
    resolved = _resolve_path(project_path)
    if not resolved.exists():
        raise ValueError(f"Project file does not exist: {resolved}")

    normalized_format = _validate_format(format)
    session_factory = create_sqlite_session_factory(resolved)
    with session_factory() as session:
        project = _load_project(session, resolved)
        note = NoteRecord(
            project_id=project.id,
            title=(title or "").strip(),
            content=content or "",
            format=normalized_format,
            tags=(tags or "").strip(),
            is_archived=False,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        result = _serialize_note(note)

    rag_service.upsert_project_note(
        project_path=str(resolved),
        note_id=result.id,
        title=result.title,
        content=result.content,
        tags=result.tags,
        format=result.format,
        updated_at=result.updated_at,
    )
    return result


def update_note(
    *,
    project_path: str,
    note_id: int,
    title: str,
    content: str,
    format: str,
    tags: str,
    is_archived: bool,
) -> NoteItem:
    resolved = _resolve_path(project_path)
    if not resolved.exists():
        raise ValueError(f"Project file does not exist: {resolved}")

    normalized_format = _validate_format(format)
    session_factory = create_sqlite_session_factory(resolved)
    with session_factory() as session:
        project = _load_project(session, resolved)
        note = session.scalar(
            select(NoteRecord).where(NoteRecord.id == note_id, NoteRecord.project_id == project.id).limit(1)
        )
        if note is None:
            raise ValueError(f"Note not found: {note_id}")

        note.title = (title or "").strip()
        note.content = content or ""
        note.format = normalized_format
        note.tags = (tags or "").strip()
        note.is_archived = bool(is_archived)
        note.updated_at = datetime.now(UTC).replace(tzinfo=None)

        session.commit()
        session.refresh(note)
        result = _serialize_note(note)

    rag_service.upsert_project_note(
        project_path=str(resolved),
        note_id=result.id,
        title=result.title,
        content=result.content,
        tags=result.tags,
        format=result.format,
        updated_at=result.updated_at,
    )
    return result


def delete_note(*, project_path: str, note_id: int) -> dict[str, int]:
    resolved = _resolve_path(project_path)
    if not resolved.exists():
        raise ValueError(f"Project file does not exist: {resolved}")

    session_factory = create_sqlite_session_factory(resolved)
    with session_factory() as session:
        project = _load_project(session, resolved)
        note = session.scalar(
            select(NoteRecord).where(NoteRecord.id == note_id, NoteRecord.project_id == project.id).limit(1)
        )
        if note is None:
            raise ValueError(f"Note not found: {note_id}")
        session.delete(note)
        session.commit()

    rag_service.delete_project_note(project_path=str(resolved), note_id=note_id)
    return {"deleted_note_id": note_id}
