from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import ProjectRecord


def resolve_project_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def require_existing_project_path(raw_path: str) -> Path:
    resolved_path = resolve_project_path(raw_path)
    if not resolved_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_path}")
    return resolved_path


def load_project_record(session, resolved_project_path: Path) -> ProjectRecord:
    project = session.scalar(select(ProjectRecord).limit(1))
    if project is None:
        raise ValueError(f"Project database has no project metadata: {resolved_project_path}")
    return project