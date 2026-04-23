from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _load_image_for_project(session, project_path: Path, image_id: int) -> ImageRecord:
    project = session.scalar(select(ProjectRecord).limit(1))
    if project is None:
        raise ValueError(f"Project database has no project metadata: {project_path}")

    image = session.scalar(select(ImageRecord).where(ImageRecord.id == image_id, ImageRecord.project_id == project.id))
    if image is None:
        raise ValueError(f"Image not found in project: {image_id}")
    return image


def create_caption_candidate(*, project_path: str, image_id: int, text: str, make_active: bool, source: str = "manual") -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)

        if make_active:
            active_captions = session.scalars(select(CaptionRecord).where(CaptionRecord.image_id == image.id, CaptionRecord.is_active.is_(True))).all()
            for caption in active_captions:
                caption.is_active = False

        caption = CaptionRecord(image_id=image.id, text=text, is_active=make_active, source=source)
        session.add(caption)
        session.commit()

        return {
            "id": caption.id,
            "image_id": caption.image_id,
            "text": caption.text,
            "is_active": caption.is_active,
            "source": caption.source,
            "created_at": caption.created_at.isoformat(),
        }


def set_active_caption(*, project_path: str, image_id: int, caption_id: int) -> dict[str, int]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)

        captions = session.scalars(select(CaptionRecord).where(CaptionRecord.image_id == image.id)).all()
        if not captions:
            raise ValueError(f"Image has no captions: {image_id}")

        target = None
        for caption in captions:
            caption.is_active = caption.id == caption_id
            if caption.id == caption_id:
                target = caption

        if target is None:
            raise ValueError(f"Caption not found for image {image_id}: {caption_id}")

        session.commit()
        return {"image_id": image.id, "active_caption_id": target.id}


def update_active_caption_text(*, project_path: str, image_id: int, text: str) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)
        active = session.scalar(select(CaptionRecord).where(CaptionRecord.image_id == image.id, CaptionRecord.is_active.is_(True)).limit(1))

        if active is None:
            active = CaptionRecord(image_id=image.id, text=text, is_active=True, source="manual")
            session.add(active)
        else:
            active.text = text

        session.commit()

        return {
            "id": active.id,
            "image_id": active.image_id,
            "text": active.text,
            "is_active": active.is_active,
            "source": active.source,
            "created_at": active.created_at.isoformat(),
        }


def update_caption_text(*, project_path: str, image_id: int, caption_id: int, text: str) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)
        caption = session.scalar(
            select(CaptionRecord).where(CaptionRecord.id == caption_id, CaptionRecord.image_id == image.id).limit(1)
        )
        if caption is None:
            raise ValueError(f"Caption not found for image {image_id}: {caption_id}")

        caption.text = text
        session.commit()

        return {
            "id": caption.id,
            "image_id": caption.image_id,
            "text": caption.text,
            "is_active": caption.is_active,
            "source": caption.source,
            "created_at": caption.created_at.isoformat(),
        }


def delete_caption(*, project_path: str, image_id: int, caption_id: int) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)
        caption = session.scalar(
            select(CaptionRecord).where(CaptionRecord.id == caption_id, CaptionRecord.image_id == image.id).limit(1)
        )
        if caption is None:
            raise ValueError(f"Caption not found for image {image_id}: {caption_id}")

        was_active = bool(caption.is_active)
        session.delete(caption)
        session.flush()

        new_active_caption_id: int | None = None
        if was_active:
            remaining = session.scalars(
                select(CaptionRecord)
                .where(CaptionRecord.image_id == image.id)
                .order_by(CaptionRecord.created_at.desc(), CaptionRecord.id.desc())
            ).all()
            if remaining:
                new_active = remaining[0]
                for item in remaining:
                    item.is_active = item.id == new_active.id
                new_active_caption_id = new_active.id

        session.commit()

        return {
            "image_id": image.id,
            "deleted_caption_id": caption_id,
            "active_caption_id": new_active_caption_id,
        }


def _apply_generated_caption(
    *,
    project_path: str,
    image_id: int,
    generated_text: str,
    mode: str,
    source: str,
    make_active: bool,
) -> dict[str, object]:
    normalized_mode = mode.strip().lower()
    if normalized_mode == "new_candidate":
        return create_caption_candidate(
            project_path=project_path,
            image_id=image_id,
            text=generated_text,
            make_active=make_active,
            source=source,
        )

    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _load_image_for_project(session, resolved_project_path, image_id)
        active = session.scalar(select(CaptionRecord).where(CaptionRecord.image_id == image.id, CaptionRecord.is_active.is_(True)).limit(1))

        if active is None:
            active = CaptionRecord(image_id=image.id, text="", is_active=True, source=source)
            session.add(active)

        if normalized_mode == "replace_active":
            active.text = generated_text
            active.source = source
        elif normalized_mode == "append_active":
            base = (active.text or "").strip()
            incoming = generated_text.strip()
            if base and incoming:
                active.text = f"{base}\n{incoming}"
            elif incoming:
                active.text = incoming
            else:
                active.text = base
            active.source = source
        else:
            raise ValueError(f"Unsupported output mode: {mode}")

        session.commit()
        return {
            "id": active.id,
            "image_id": active.image_id,
            "text": active.text,
            "is_active": active.is_active,
            "source": active.source,
            "created_at": active.created_at.isoformat(),
        }
