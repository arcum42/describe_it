from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from sqlalchemy import delete, select

from backend.config import get_settings
from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


@dataclass
class ImportFolderResult:
    project_path: str
    source_folder: str
    imported_images: int
    captions_from_files: int
    blank_captions: int
    total_images_in_project: int


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _read_caption_text(caption_path: Path) -> str:
    if not caption_path.exists():
        return ""
    return caption_path.read_text(encoding="utf-8", errors="replace").strip()


def import_folder_into_project(*, project_path: str, source_folder: str, replace_existing: bool = False) -> ImportFolderResult:
    resolved_project_path = _resolve_path(project_path)
    resolved_source_folder = _resolve_path(source_folder)

    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")
    if not resolved_source_folder.exists() or not resolved_source_folder.is_dir():
        raise ValueError(f"Source folder does not exist: {resolved_source_folder}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    image_paths = [
        child
        for child in sorted(resolved_source_folder.iterdir(), key=lambda item: item.name.lower())
        if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not image_paths:
        raise ValueError(f"No supported image files found in: {resolved_source_folder}")

    imported_images = 0
    captions_from_files = 0
    blank_captions = 0

    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        if replace_existing:
            image_ids = session.scalars(select(ImageRecord.id).where(ImageRecord.project_id == project.id)).all()
            if image_ids:
                session.execute(delete(CaptionRecord).where(CaptionRecord.image_id.in_(image_ids)))
                session.execute(delete(ImageRecord).where(ImageRecord.project_id == project.id))

        for image_path in image_paths:
            image_bytes = image_path.read_bytes()
            with Image.open(image_path) as img:
                width, height = img.size

            image_record = ImageRecord(
                project_id=project.id,
                filename=image_path.name,
                original_blob=image_bytes,
                working_blob=None,
                width=width,
                height=height,
                included=True,
                parent_image_id=None,
            )
            session.add(image_record)
            session.flush()

            caption_text = _read_caption_text(image_path.with_suffix(".txt"))
            if caption_text:
                captions_from_files += 1
            else:
                blank_captions += 1

            caption_record = CaptionRecord(
                image_id=image_record.id,
                text=caption_text,
                is_active=True,
                source="import",
            )
            session.add(caption_record)
            imported_images += 1

        total_images = len(session.scalars(select(ImageRecord).where(ImageRecord.project_id == project.id)).all())
        session.commit()

    return ImportFolderResult(
        project_path=str(resolved_project_path),
        source_folder=str(resolved_source_folder),
        imported_images=imported_images,
        captions_from_files=captions_from_files,
        blank_captions=blank_captions,
        total_images_in_project=total_images,
    )


def project_image_summary(*, project_path: str) -> dict[str, object]:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_project_path}")

        images = session.scalars(select(ImageRecord).where(ImageRecord.project_id == project.id).order_by(ImageRecord.id.asc())).all()
        captions = session.scalars(select(CaptionRecord).join(ImageRecord, CaptionRecord.image_id == ImageRecord.id).where(ImageRecord.project_id == project.id)).all()

    non_empty_caption_count = sum(1 for caption in captions if caption.text.strip())
    previews = [
        {
            "filename": image.filename,
            "width": image.width,
            "height": image.height,
            "included": image.included,
        }
        for image in images[:24]
    ]

    return {
        "project_path": str(resolved_project_path),
        "count": len(images),
        "non_empty_caption_count": non_empty_caption_count,
        "blank_caption_count": max(0, len(images) - non_empty_caption_count),
        "previews": previews,
    }
