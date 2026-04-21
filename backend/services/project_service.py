from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database


@dataclass
class RecentProjectEntry:
    name: str
    path: str
    last_opened_at: str


@dataclass
class ProjectSummary:
    name: str
    path: str
    description: str = ""
    trigger_word: str = ""
    caption_mode: str = "description"


@dataclass
class BrowserEntry:
    name: str
    path: str
    kind: str


@dataclass
class BrowserListing:
    current_path: str
    parent_path: str | None
    directories: list[BrowserEntry]
    db_files: list[BrowserEntry]
    roots: list[str]


def _settings_paths() -> tuple[Path, Path]:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings.state_dir, settings.recent_projects_path


def _resolve_project_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = get_settings().base_dir / path
    return path.resolve()


def _allowed_browser_roots() -> list[Path]:
    base_dir = get_settings().base_dir.resolve()
    home_dir = Path.home().resolve()
    roots = [base_dir]
    if home_dir != base_dir:
        roots.append(home_dir)
    return roots


def _resolve_browser_path(raw_path: str | None) -> Path:
    candidate = get_settings().base_dir if not raw_path else Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    candidate = candidate.resolve()

    for root in _allowed_browser_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue

    raise ValueError(f"Path is outside allowed browser roots: {candidate}")


def _read_recent_entries() -> list[RecentProjectEntry]:
    _, registry_path = _settings_paths()
    if not registry_path.exists():
        return []
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    return [RecentProjectEntry(**item) for item in payload.get("projects", [])]


def _write_recent_entries(entries: list[RecentProjectEntry]) -> None:
    _, registry_path = _settings_paths()
    payload = {"projects": [asdict(entry) for entry in entries]}
    registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_recent_projects() -> list[RecentProjectEntry]:
    return _read_recent_entries()


def register_recent_project(summary: ProjectSummary) -> None:
    now = datetime.now(UTC).isoformat()
    entries = [entry for entry in _read_recent_entries() if entry.path != summary.path]
    entries.insert(0, RecentProjectEntry(name=summary.name, path=summary.path, last_opened_at=now))
    _write_recent_entries(entries[:20])


def create_project(*, name: str, path: str, description: str = "") -> ProjectSummary:
    project_path = _resolve_project_path(path)
    if project_path.exists():
        raise ValueError(f"Project file already exists: {project_path}")

    project_path.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(project_path)
    session_factory = create_sqlite_session_factory(project_path)

    with session_factory() as session:
        record = ProjectRecord(name=name, description=description)
        session.add(record)
        session.commit()

    summary = ProjectSummary(name=name, path=str(project_path), description=description)
    register_recent_project(summary)
    return summary


def open_project(*, path: str) -> ProjectSummary:
    project_path = _resolve_project_path(path)
    if not project_path.exists():
        raise ValueError(f"Project file does not exist: {project_path}")

    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        record = session.scalar(select(ProjectRecord).limit(1))
        if record is None:
            raise ValueError(f"Project database has no project metadata: {project_path}")

        summary = ProjectSummary(
            name=record.name,
            path=str(project_path),
            description=record.description,
            trigger_word=record.trigger_word,
            caption_mode=record.caption_mode,
        )

    register_recent_project(summary)
    return summary


def update_project_metadata(*, path: str, name: str, description: str, trigger_word: str, caption_mode: str) -> ProjectSummary:
    project_path = _resolve_project_path(path)
    if not project_path.exists():
        raise ValueError(f"Project file does not exist: {project_path}")
    if caption_mode not in {"description", "tags"}:
        raise ValueError(f"Unsupported caption mode: {caption_mode}")

    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        record = session.scalar(select(ProjectRecord).limit(1))
        if record is None:
            raise ValueError(f"Project database has no project metadata: {project_path}")

        record.name = name
        record.description = description
        record.trigger_word = trigger_word
        record.caption_mode = caption_mode
        session.commit()

        summary = ProjectSummary(
            name=record.name,
            path=str(project_path),
            description=record.description,
            trigger_word=record.trigger_word,
            caption_mode=record.caption_mode,
        )

    register_recent_project(summary)
    return summary


def browse_project_paths(*, path: str | None = None) -> BrowserListing:
    current_path = _resolve_browser_path(path)
    if not current_path.exists():
        raise ValueError(f"Path does not exist: {current_path}")
    if current_path.is_file():
        current_path = current_path.parent

    directories: list[BrowserEntry] = []
    db_files: list[BrowserEntry] = []
    for child in sorted(current_path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name.startswith('.') and child.name not in {'.github'}:
            continue
        resolved = child.resolve()
        entry = BrowserEntry(name=child.name, path=str(resolved), kind="directory" if child.is_dir() else "file")
        if child.is_dir():
            directories.append(entry)
        elif child.suffix == ".db":
            db_files.append(entry)

    parent_path: str | None = None
    for root in _allowed_browser_roots():
        try:
            current_path.relative_to(root)
            if current_path != root:
                parent_path = str(current_path.parent)
            break
        except ValueError:
            continue

    return BrowserListing(
        current_path=str(current_path),
        parent_path=parent_path,
        directories=directories,
        db_files=db_files,
        roots=[str(root) for root in _allowed_browser_roots()],
    )
