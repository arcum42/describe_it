from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
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
    source_image_id: int | None
    derived_operation: str | None
    derived_operation_params: str | None
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


def _load_image_for_project(session, resolved_project_path: Path, image_id: int, *, include_deleted: bool = False) -> ImageRecord:
    project = session.scalar(select(ProjectRecord).limit(1))
    if project is None:
        raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

    image = session.scalar(select(ImageRecord).where(ImageRecord.id == image_id, ImageRecord.project_id == project.id))
    if image is None or (image.deleted_at is not None and not include_deleted):
        raise ValueError(f"Image not found in project: {image_id}")
    return image


def _build_duplicate_filename(existing_filenames: set[str], filename: str) -> str:
    path = Path(filename)
    stem = path.stem or "image"
    suffix = path.suffix

    candidate = f"{stem}_copy{suffix}"
    counter = 2
    while candidate in existing_filenames:
        candidate = f"{stem}_copy{counter}{suffix}"
        counter += 1
    return candidate


def list_project_images(*, project_path: str) -> list[ImageListItem]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        images = session.scalars(
            select(ImageRecord)
            .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
            .order_by(ImageRecord.id.asc())
        ).all()
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

        image = _load_image_for_project(session, resolved_project_path, image_id)

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
        source_image_id=image.source_image_id,
        derived_operation=image.derived_operation,
        derived_operation_params=image.derived_operation_params,
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

        image = _load_image_for_project(session, resolved_project_path, image_id)

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

        image = _load_image_for_project(session, resolved_project_path, image_id)

        image.included = included
        session.commit()

        return {"image_id": image.id, "included": image.included}


def duplicate_image(*, project_path: str, image_id: int, include_captions: bool = True, copy_mode: str = "all_candidates") -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")
    if copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported copy mode: {copy_mode}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        blob = source_image.working_blob or source_image.original_blob
        if blob is None:
            raise ValueError(f"No image bytes available for image: {image_id}")

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_duplicate_filename(existing_filenames, source_image.filename)
        duplicate = ImageRecord(
            project_id=source_image.project_id,
            filename=new_filename,
            original_blob=blob,
            working_blob=blob,
            width=source_image.width,
            height=source_image.height,
            included=source_image.included,
            parent_image_id=source_image.id,
            source_image_id=source_image.id,
            derived_operation="duplicate",
            derived_operation_params=json.dumps({"copy_mode": copy_mode, "include_captions": include_captions}),
            deleted_at=None,
        )
        session.add(duplicate)
        session.flush()

        copied_caption_count = 0
        if include_captions and copy_mode != "none":
            source_captions = session.scalars(
                select(CaptionRecord)
                .where(CaptionRecord.image_id == source_image.id)
                .order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
            ).all()
            if copy_mode == "active_only":
                source_captions = [caption for caption in source_captions if caption.is_active]

            for caption in source_captions:
                session.add(
                    CaptionRecord(
                        image_id=duplicate.id,
                        text=caption.text,
                        is_active=caption.is_active if copy_mode == "all_candidates" else True,
                        source=caption.source,
                    )
                )
                copied_caption_count += 1

        session.commit()
        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": duplicate.id,
                "filename": duplicate.filename,
                "width": duplicate.width,
                "height": duplicate.height,
                "included": duplicate.included,
                "source_image_id": duplicate.source_image_id,
                "derived_operation": duplicate.derived_operation,
                "derived_operation_params": duplicate.derived_operation_params,
            },
            "copied_caption_count": copied_caption_count,
        }


def delete_image(*, project_path: str, image_id: int, mode: str = "soft", confirm_hard_delete: bool = False) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")
    if mode not in {"soft", "hard"}:
        raise ValueError(f"Unsupported delete mode: {mode}")
    if mode == "hard" and not confirm_hard_delete:
        raise ValueError("Hard delete requires confirm_hard_delete=true")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id, include_deleted=True)

        if mode == "soft":
            image.deleted_at = datetime.now(UTC)
            session.commit()
            return {
                "image_id": image.id,
                "deleted_at": image.deleted_at.isoformat(),
                "mode": mode,
            }

        captions = session.scalars(select(CaptionRecord).where(CaptionRecord.image_id == image.id)).all()
        for caption in captions:
            session.delete(caption)
        session.delete(image)
        session.commit()
        return {
            "image_id": image_id,
            "deleted_at": None,
            "mode": mode,
        }


def restore_image(*, project_path: str, image_id: int) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id, include_deleted=True)
        image.deleted_at = None
        session.commit()
        return {
            "image_id": image.id,
            "deleted_at": None,
            "mode": "soft",
        }
