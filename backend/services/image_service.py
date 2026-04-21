from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory


@dataclass
class ImageListItem:
    id: int
    filename: str
    width: int | None
    height: int | None
    included: bool
    active_caption_preview: str


@dataclass
class CaptionCandidate:
    id: int
    text: str
    is_active: bool
    source: str
    created_at: str


@dataclass
class ImageDetail:
    id: int
    filename: str
    width: int | None
    height: int | None
    included: bool
    captions: list[CaptionCandidate]


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _load_project(session_factory, resolved_project_path: Path) -> ProjectRecord:
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")
        return project


def list_project_images(*, project_path: str) -> list[ImageListItem]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        images = session.scalars(select(ImageRecord).where(ImageRecord.project_id == project.id).order_by(ImageRecord.id.asc())).all()
        image_ids = [image.id for image in images]
        captions = session.scalars(select(CaptionRecord).where(CaptionRecord.image_id.in_(image_ids), CaptionRecord.is_active.is_(True))).all() if image_ids else []
        active_by_image = {caption.image_id: caption for caption in captions}

    items: list[ImageListItem] = []
    for image in images:
        active_caption = active_by_image.get(image.id)
        preview = (active_caption.text or "").strip()
        if len(preview) > 90:
            preview = f"{preview[:87]}..."
        items.append(
            ImageListItem(
                id=image.id,
                filename=image.filename,
                width=image.width,
                height=image.height,
                included=image.included,
                active_caption_preview=preview,
            )
        )
    return items


def get_image_detail(*, project_path: str, image_id: int) -> ImageDetail:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        image = session.scalar(select(ImageRecord).where(ImageRecord.id == image_id, ImageRecord.project_id == project.id))
        if image is None:
            raise ValueError(f"Image not found in project: {image_id}")

        captions = session.scalars(
            select(CaptionRecord).where(CaptionRecord.image_id == image.id).order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
        ).all()

    candidates = [
        CaptionCandidate(
            id=caption.id,
            text=caption.text,
            is_active=caption.is_active,
            source=caption.source,
            created_at=caption.created_at.isoformat(),
        )
        for caption in captions
    ]

    return ImageDetail(
        id=image.id,
        filename=image.filename,
        width=image.width,
        height=image.height,
        included=image.included,
        captions=candidates,
    )


def get_image_content(*, project_path: str, image_id: int) -> tuple[bytes, str]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        image = session.scalar(select(ImageRecord).where(ImageRecord.id == image_id, ImageRecord.project_id == project.id))
        if image is None:
            raise ValueError(f"Image not found in project: {image_id}")

        blob = image.working_blob or image.original_blob
        if blob is None:
            raise ValueError(f"No image bytes available for image: {image_id}")

        media_type = mimetypes.guess_type(image.filename)[0] or "application/octet-stream"
        return blob, media_type


def update_image_included(*, project_path: str, image_id: int, included: bool) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        image = session.scalar(select(ImageRecord).where(ImageRecord.id == image_id, ImageRecord.project_id == project.id))
        if image is None:
            raise ValueError(f"Image not found in project: {image_id}")

        image.included = included
        session.commit()

        return {"image_id": image.id, "included": image.included}
