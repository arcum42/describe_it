from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory


@dataclass
class ExportResult:
    output_folder: str
    exported_images: int
    skipped_images: int
    skipped_missing_blob: int
    skipped_due_to_collision: int
    trigger_word_applied: bool
    metadata_written: bool
    metadata_file: str | None


@dataclass
class ExportPreviewResult:
    output_folder: str
    total_images: int
    images_to_export: int
    excluded_images: int
    blank_captions: int
    existing_target_files: int
    would_overwrite: bool
    trigger_word_will_apply: bool


def _load_project_images_and_captions(*, project_path: Path, included_only: bool) -> tuple[ProjectRecord, list[ImageRecord], dict[int, CaptionRecord]]:
    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {project_path}")

        image_query = select(ImageRecord).where(ImageRecord.project_id == project.id).order_by(ImageRecord.id.asc())
        if included_only:
            image_query = image_query.where(ImageRecord.included.is_(True))
        images = session.scalars(image_query).all()

        image_ids = [image.id for image in images]
        captions = (
            session.scalars(
                select(CaptionRecord)
                .where(CaptionRecord.image_id.in_(image_ids), CaptionRecord.is_active.is_(True))
                .order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
            ).all()
            if image_ids
            else []
        )
        active_caption_by_image = {caption.image_id: caption for caption in captions}

    return project, images, active_caption_by_image


def _resolve_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _apply_trigger_word(caption: str, trigger_word: str) -> str:
    clean_caption = caption.strip()
    clean_trigger = trigger_word.strip()
    if not clean_trigger:
        return clean_caption
    if not clean_caption:
        return clean_trigger

    caption_lower = clean_caption.lower()
    trigger_lower = clean_trigger.lower()
    if caption_lower == trigger_lower:
        return clean_caption
    if caption_lower.startswith(f"{trigger_lower},") or caption_lower.startswith(f"{trigger_lower} "):
        return clean_caption
    return f"{clean_trigger}, {clean_caption}"


def _sanitize_folder_name(raw_name: str) -> str:
    clean = raw_name.strip().replace("\\", "/").strip("/")
    clean = clean.split("/")[-1]
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", clean).strip("._-")
    return clean


def _resolve_output_folder(*, output_folder: str, create_new_folder: bool, new_folder_name: str) -> Path:
    base_output = _resolve_path(output_folder)
    if not create_new_folder:
        return base_output

    folder_name = _sanitize_folder_name(new_folder_name)
    if not folder_name:
        folder_name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return (base_output / folder_name).resolve()


def _validate_clean_target(folder: Path) -> None:
    home = Path.home().resolve()
    base_dir = get_settings().base_dir.resolve()
    if folder == folder.anchor:
        raise ValueError("Refusing to clean filesystem root")
    if folder == home:
        raise ValueError("Refusing to clean home directory")
    if folder == base_dir:
        raise ValueError("Refusing to clean application root directory")


def _clean_output_folder(folder: Path) -> None:
    _validate_clean_target(folder)
    for entry in folder.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def preview_project_export(
    *,
    project_path: str,
    output_folder: str,
    included_only: bool = True,
    apply_trigger_word: bool = False,
    create_new_folder: bool = False,
    new_folder_name: str = "",
) -> ExportPreviewResult:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    resolved_output_folder = _resolve_output_folder(
        output_folder=output_folder,
        create_new_folder=create_new_folder,
        new_folder_name=new_folder_name,
    )

    project, images, active_caption_by_image = _load_project_images_and_captions(project_path=resolved_project_path, included_only=included_only)

    total_images = len(images)
    images_to_export = 0
    blank_captions = 0
    existing_target_files = 0

    for image in images:
        blob = image.working_blob or image.original_blob
        if blob is None:
            continue

        image_output_path = resolved_output_folder / image.filename
        caption_output_path = image_output_path.with_suffix(".txt")
        if image_output_path.exists():
            existing_target_files += 1
        if caption_output_path.exists():
            existing_target_files += 1

        active_caption = active_caption_by_image.get(image.id)
        caption_text = (active_caption.text if active_caption is not None else "").strip()
        if not caption_text:
            blank_captions += 1

        images_to_export += 1

    excluded_images = 0
    if included_only:
        session_factory = create_sqlite_session_factory(resolved_project_path)
        with session_factory() as session:
            project_row = session.scalar(select(ProjectRecord).limit(1))
            if project_row is not None:
                all_images = session.scalars(
                    select(ImageRecord).where(ImageRecord.project_id == project_row.id).order_by(ImageRecord.id.asc())
                ).all()
                excluded_images = max(0, len(all_images) - total_images)

    trigger_word = (project.trigger_word or "").strip() if apply_trigger_word else ""

    return ExportPreviewResult(
        output_folder=str(resolved_output_folder),
        total_images=total_images,
        images_to_export=images_to_export,
        excluded_images=excluded_images,
        blank_captions=blank_captions,
        existing_target_files=existing_target_files,
        would_overwrite=existing_target_files > 0,
        trigger_word_will_apply=bool(trigger_word),
    )


def export_project_dataset(
    *,
    project_path: str,
    output_folder: str,
    included_only: bool = True,
    apply_trigger_word: bool = False,
    include_metadata: bool = False,
    overwrite_existing: bool = False,
    clean_output_folder: bool = False,
    create_new_folder: bool = False,
    new_folder_name: str = "",
) -> ExportResult:
    resolved_project_path = _resolve_path(project_path)
    if not resolved_project_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_project_path}")

    if clean_output_folder and overwrite_existing:
        raise ValueError("Choose either clean output folder or overwrite existing files, not both")

    resolved_output_folder = _resolve_output_folder(
        output_folder=output_folder,
        create_new_folder=create_new_folder,
        new_folder_name=new_folder_name,
    )
    resolved_output_folder.mkdir(parents=True, exist_ok=True)
    if clean_output_folder:
        _clean_output_folder(resolved_output_folder)
        resolved_output_folder.mkdir(parents=True, exist_ok=True)

    project, images, active_caption_by_image = _load_project_images_and_captions(project_path=resolved_project_path, included_only=included_only)

    exported_images = 0
    skipped_images = 0
    skipped_missing_blob = 0
    skipped_due_to_collision = 0
    trigger_word = (project.trigger_word or "").strip() if apply_trigger_word else ""
    trigger_word_applied = bool(trigger_word)
    metadata_images: list[dict[str, object]] = []

    for image in images:
        blob = image.working_blob or image.original_blob
        if blob is None:
            skipped_images += 1
            skipped_missing_blob += 1
            continue

        image_output_path = resolved_output_folder / image.filename
        image_output_path.parent.mkdir(parents=True, exist_ok=True)
        caption_output_path = image_output_path.with_suffix(".txt")

        if not overwrite_existing and (image_output_path.exists() or caption_output_path.exists()):
            skipped_images += 1
            skipped_due_to_collision += 1
            continue

        image_output_path.write_bytes(blob)

        active_caption = active_caption_by_image.get(image.id)
        caption_text = active_caption.text if active_caption is not None else ""
        if trigger_word_applied:
            caption_text = _apply_trigger_word(caption_text, trigger_word)
        else:
            caption_text = caption_text.strip()

        caption_output_path.write_text(caption_text, encoding="utf-8")

        metadata_images.append(
            {
                "image_id": image.id,
                "filename": image.filename,
                "image_file": image_output_path.name,
                "caption_file": caption_output_path.name,
                "included": bool(image.included),
                "caption_is_blank": not bool(caption_text.strip()),
            }
        )

        exported_images += 1

    metadata_file: str | None = None
    if include_metadata:
        metadata_path = resolved_output_folder / "export_manifest.json"
        manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_path": str(resolved_project_path),
            "project_name": project.name,
            "project_description": project.description,
            "project_caption_mode": project.caption_mode,
            "project_trigger_word": project.trigger_word,
            "options": {
                "included_only": included_only,
                "apply_trigger_word": apply_trigger_word,
                "trigger_word_applied": trigger_word_applied,
                "overwrite_existing": overwrite_existing,
                "clean_output_folder": clean_output_folder,
                "create_new_folder": create_new_folder,
                "new_folder_name": _sanitize_folder_name(new_folder_name) if create_new_folder else "",
            },
            "counts": {
                "exported_images": exported_images,
                "skipped_images": skipped_images,
                "skipped_missing_blob": skipped_missing_blob,
                "skipped_due_to_collision": skipped_due_to_collision,
            },
            "images": metadata_images,
        }
        metadata_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        metadata_file = str(metadata_path)

    return ExportResult(
        output_folder=str(resolved_output_folder),
        exported_images=exported_images,
        skipped_images=skipped_images,
        skipped_missing_blob=skipped_missing_blob,
        skipped_due_to_collision=skipped_due_to_collision,
        trigger_word_applied=trigger_word_applied,
        metadata_written=include_metadata,
        metadata_file=metadata_file,
    )
