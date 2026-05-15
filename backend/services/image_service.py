from __future__ import annotations

import hashlib
import io
import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import func, select

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.services.project_db_utils import load_project_record, require_existing_project_path


@dataclass
class ImageListItem:
    id: int
    filename: str
    width: int | None
    height: int | None
    included: bool
    active_caption_preview: str
    all_captions_search_text: str


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


@dataclass
class DuplicateImageGroup:
    hash_value: str
    kept_image_id: int
    kept_filename: str
    kept_caption_count: int
    duplicate_images: list[dict[str, object]]


def _load_image_for_project(session, resolved_project_path: Path, image_id: int, *, include_deleted: bool = False) -> ImageRecord:
    project = load_project_record(session, resolved_project_path)

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


def _image_format_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
        ".bmp": "BMP",
        ".gif": "GIF",
    }.get(suffix, "PNG")


def _load_image_blob(image: ImageRecord, image_id: int) -> bytes:
    blob = image.working_blob or image.original_blob
    if blob is None:
        raise ValueError(f"No image bytes available for image: {image_id}")
    return blob


def _normalize_caption_text(text: str | None) -> str:
    return (text or "").strip()


def _build_duplicate_groups(session) -> list[tuple[str, list[ImageRecord]]]:
    images = session.scalars(
        select(ImageRecord)
        .where(ImageRecord.deleted_at.is_(None), ImageRecord.original_blob.is_not(None))
        .order_by(ImageRecord.id.asc())
    ).all()

    grouped: dict[str, list[ImageRecord]] = {}
    for image in images:
        if image.original_blob is None:
            continue
        hash_value = hashlib.sha256(image.original_blob).hexdigest()
        grouped.setdefault(hash_value, []).append(image)

    return [(hash_value, grouped_images) for hash_value, grouped_images in grouped.items() if len(grouped_images) > 1]


def _build_duplicate_group_summary(session, hash_value: str, images: list[ImageRecord]) -> DuplicateImageGroup:
    caption_counts = {
        image.id: session.scalar(select(func.count(CaptionRecord.id)).where(CaptionRecord.image_id == image.id)) or 0
        for image in images
    }
    kept_image = images[0]
    duplicate_images = [
        {
            "id": image.id,
            "filename": image.filename,
            "caption_count": int(caption_counts.get(image.id, 0)),
        }
        for image in images[1:]
    ]
    return DuplicateImageGroup(
        hash_value=hash_value,
        kept_image_id=kept_image.id,
        kept_filename=kept_image.filename,
        kept_caption_count=int(caption_counts.get(kept_image.id, 0)),
        duplicate_images=duplicate_images,
    )


def _build_output_filename(
    *,
    existing_filenames: set[str],
    source_filename: str,
    suggested_suffix: str,
    output_name: str | None,
) -> str:
    source_suffix = Path(source_filename).suffix
    if output_name and output_name.strip():
        raw = output_name.strip()
        suffix = Path(raw).suffix
        candidate = raw if suffix else f"{raw}{source_suffix}"
    else:
        stem = Path(source_filename).stem or "image"
        candidate = f"{stem}_{suggested_suffix}{source_suffix}"

    if candidate not in existing_filenames:
        return candidate

    path = Path(candidate)
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        next_candidate = f"{stem}_{counter}{suffix}"
        if next_candidate not in existing_filenames:
            return next_candidate
        counter += 1


def _copy_captions(
    *,
    session,
    source_image_id: int,
    target_image_id: int,
    include_captions: bool,
    copy_mode: str,
) -> int:
    if not include_captions or copy_mode == "none":
        return 0

    source_captions = session.scalars(
        select(CaptionRecord)
        .where(CaptionRecord.image_id == source_image_id)
        .order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
    ).all()

    if copy_mode == "active_only":
        source_captions = [caption for caption in source_captions if caption.is_active]

    copied = 0
    for idx, caption in enumerate(source_captions):
        is_active = caption.is_active if copy_mode == "all_candidates" else idx == 0
        session.add(
            CaptionRecord(
                image_id=target_image_id,
                text=caption.text,
                is_active=is_active,
                source=caption.source,
            )
        )
        copied += 1
    return copied


def _create_derived_image(
    *,
    session,
    source_image: ImageRecord,
    filename: str,
    image_bytes: bytes,
    width: int,
    height: int,
    operation_type: str,
    operation_params: dict[str, object],
    include_captions: bool,
    caption_copy_mode: str,
) -> tuple[ImageRecord, int]:
    derived = ImageRecord(
        project_id=source_image.project_id,
        filename=filename,
        original_blob=image_bytes,
        working_blob=None,
        width=width,
        height=height,
        included=source_image.included,
        parent_image_id=source_image.id,
        source_image_id=source_image.id,
        derived_operation=operation_type,
        derived_operation_params=json.dumps(operation_params),
        deleted_at=None,
    )
    session.add(derived)
    session.flush()

    copied_caption_count = _copy_captions(
        session=session,
        source_image_id=source_image.id,
        target_image_id=derived.id,
        include_captions=include_captions,
        copy_mode=caption_copy_mode,
    )

    return derived, copied_caption_count


def list_project_images(*, project_path: str) -> list[ImageListItem]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = load_project_record(session, resolved_project_path)

        images = session.scalars(
            select(ImageRecord)
            .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
            .order_by(ImageRecord.id.asc())
        ).all()
        image_ids = [image.id for image in images]
        active_captions = session.scalars(
            select(CaptionRecord).where(CaptionRecord.image_id.in_(image_ids), CaptionRecord.is_active.is_(True))
        ).all() if image_ids else []
        all_captions = session.scalars(
            select(CaptionRecord).where(CaptionRecord.image_id.in_(image_ids))
        ).all() if image_ids else []
        active_by_image = {caption.image_id: caption for caption in active_captions}
        all_text_by_image: dict[int, list[str]] = {}
        for caption in all_captions:
            text_value = (caption.text or '').strip()
            if not text_value:
                continue
            all_text_by_image.setdefault(caption.image_id, []).append(text_value)

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
                all_captions_search_text='\n'.join(all_text_by_image.get(image.id, [])),
            )
        )
    return items


def get_image_detail(*, project_path: str, image_id: int) -> ImageDetail:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        load_project_record(session, resolved_project_path)

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
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        load_project_record(session, resolved_project_path)

        image = _load_image_for_project(session, resolved_project_path, image_id)

        blob = _load_image_blob(image, image_id)

        media_type = mimetypes.guess_type(image.filename)[0] or "application/octet-stream"
        return blob, media_type


def _normalize_image_ids(image_ids: list[int]) -> list[int]:
    if not image_ids:
        raise ValueError("At least one image id is required")

    ordered_ids: list[int] = []
    seen: set[int] = set()
    for image_id in image_ids:
        if image_id in seen:
            continue
        seen.add(image_id)
        ordered_ids.append(image_id)
    return ordered_ids


def _set_image_included_for_project(*, session, resolved_project_path: Path, image_id: int, included: bool) -> ImageRecord:
    image = _load_image_for_project(session, resolved_project_path, image_id)
    image.included = included
    return image


def _duplicate_image_for_project(
    *,
    session,
    resolved_project_path: Path,
    image_id: int,
    include_captions: bool,
    copy_mode: str,
    existing_filenames: set[str],
) -> tuple[ImageRecord, ImageRecord, int]:
    source_image = _load_image_for_project(session, resolved_project_path, image_id)
    blob = _load_image_blob(source_image, image_id)

    new_filename = _build_duplicate_filename(existing_filenames, source_image.filename)
    existing_filenames.add(new_filename)
    duplicate, copied_caption_count = _create_derived_image(
        session=session,
        source_image=source_image,
        filename=new_filename,
        image_bytes=blob,
        width=source_image.width or 0,
        height=source_image.height or 0,
        operation_type="duplicate",
        operation_params={"copy_mode": copy_mode, "include_captions": include_captions},
        include_captions=include_captions,
        caption_copy_mode=copy_mode,
    )
    return source_image, duplicate, copied_caption_count


def _delete_image_for_project(
    *,
    session,
    resolved_project_path: Path,
    image_id: int,
    mode: str,
    confirm_hard_delete: bool,
) -> dict[str, object]:
    if mode not in {"soft", "hard"}:
        raise ValueError(f"Unsupported delete mode: {mode}")
    if mode == "hard" and not confirm_hard_delete:
        raise ValueError("Hard delete requires confirm_hard_delete=true")

    image = _load_image_for_project(session, resolved_project_path, image_id, include_deleted=True)

    if mode == "soft":
        image.deleted_at = datetime.now(UTC)
        return {
            "image_id": image.id,
            "deleted_at": image.deleted_at.isoformat(),
            "mode": mode,
        }

    captions = session.scalars(select(CaptionRecord).where(CaptionRecord.image_id == image.id)).all()
    for caption in captions:
        session.delete(caption)
    session.delete(image)
    return {
        "image_id": image_id,
        "deleted_at": None,
        "mode": mode,
    }


def update_image_included(*, project_path: str, image_id: int, included: bool) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        image = _set_image_included_for_project(
            session=session,
            resolved_project_path=resolved_project_path,
            image_id=image_id,
            included=included,
        )
        session.commit()

        return {"image_id": image.id, "included": image.included}


def batch_update_image_included(*, project_path: str, image_ids: list[int], included: bool) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)
    normalized_image_ids = _normalize_image_ids(image_ids)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        updated_ids: list[int] = []
        for image_id in normalized_image_ids:
            image = _set_image_included_for_project(
                session=session,
                resolved_project_path=resolved_project_path,
                image_id=image_id,
                included=included,
            )
            updated_ids.append(image.id)
        session.commit()

    return {
        "image_ids": updated_ids,
        "updated_count": len(updated_ids),
        "included": included,
    }


def duplicate_image(*, project_path: str, image_id: int, include_captions: bool = True, copy_mode: str = "all_candidates") -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)
    if copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported copy mode: {copy_mode}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        source_image, duplicate, copied_caption_count = _duplicate_image_for_project(
            session=session,
            resolved_project_path=resolved_project_path,
            image_id=image_id,
            include_captions=include_captions,
            copy_mode=copy_mode,
            existing_filenames=existing_filenames,
        )

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


def batch_duplicate_images(
    *,
    project_path: str,
    image_ids: list[int],
    include_captions: bool = True,
    copy_mode: str = "all_candidates",
) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)
    normalized_image_ids = _normalize_image_ids(image_ids)
    if copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported copy mode: {copy_mode}")

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_images: list[dict[str, object]] = []
        source_image_ids: list[int] = []
        copied_caption_count = 0

        for image_id in normalized_image_ids:
            source_image, duplicate, copied_count = _duplicate_image_for_project(
                session=session,
                resolved_project_path=resolved_project_path,
                image_id=image_id,
                include_captions=include_captions,
                copy_mode=copy_mode,
                existing_filenames=existing_filenames,
            )
            source_image_ids.append(source_image.id)
            copied_caption_count += copied_count
            new_images.append(
                {
                    "id": duplicate.id,
                    "filename": duplicate.filename,
                    "width": duplicate.width,
                    "height": duplicate.height,
                    "included": duplicate.included,
                    "source_image_id": duplicate.source_image_id,
                    "derived_operation": duplicate.derived_operation,
                    "derived_operation_params": duplicate.derived_operation_params,
                }
            )

        session.commit()

    return {
        "source_image_ids": source_image_ids,
        "created_count": len(new_images),
        "new_images": new_images,
        "copied_caption_count": copied_caption_count,
    }


def crop_image(
    *,
    project_path: str,
    image_id: int,
    x: int,
    y: int,
    width: int,
    height: int,
    output_name: str | None = None,
    include_captions: bool = True,
    caption_copy_mode: str = "all_candidates",
) -> dict[str, object]:
    if width <= 0 or height <= 0:
        raise ValueError("Crop width and height must be > 0")
    if x < 0 or y < 0:
        raise ValueError("Crop x/y must be >= 0")
    if caption_copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported caption copy mode: {caption_copy_mode}")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        source_blob = _load_image_blob(source_image, image_id)

        with Image.open(io.BytesIO(source_blob)) as src:
            if x + width > src.width or y + height > src.height:
                raise ValueError("Crop rectangle must be within source image bounds")

            cropped = src.crop((x, y, x + width, y + height))
            out = io.BytesIO()
            cropped.save(out, format=_image_format_for_filename(source_image.filename))
            derived_bytes = out.getvalue()
            derived_width, derived_height = cropped.size

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_output_filename(
            existing_filenames=existing_filenames,
            source_filename=source_image.filename,
            suggested_suffix="crop",
            output_name=output_name,
        )

        derived, _ = _create_derived_image(
            session=session,
            source_image=source_image,
            filename=new_filename,
            image_bytes=derived_bytes,
            width=derived_width,
            height=derived_height,
            operation_type="crop",
            operation_params={"x": x, "y": y, "width": width, "height": height},
            include_captions=include_captions,
            caption_copy_mode=caption_copy_mode,
        )
        session.commit()

        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": derived.id,
                "filename": derived.filename,
                "width": derived.width,
                "height": derived.height,
                "included": derived.included,
                "source_image_id": derived.source_image_id,
                "derived_operation": derived.derived_operation,
                "derived_operation_params": derived.derived_operation_params,
            },
            "operation": {
                "type": "crop",
                "params": {"x": x, "y": y, "width": width, "height": height},
            },
        }


def scale_image(
    *,
    project_path: str,
    image_id: int,
    mode: str,
    percent: float | None = None,
    width: int | None = None,
    height: int | None = None,
    keep_aspect_ratio: bool = True,
    upscale: bool = False,
    output_name: str | None = None,
    include_captions: bool = True,
    caption_copy_mode: str = "all_candidates",
) -> dict[str, object]:
    if mode not in {"percent", "dimensions"}:
        raise ValueError(f"Unsupported scale mode: {mode}")
    if caption_copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported caption copy mode: {caption_copy_mode}")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        source_blob = _load_image_blob(source_image, image_id)

        with Image.open(io.BytesIO(source_blob)) as src:
            src_w, src_h = src.size

            if mode == "percent":
                if percent is None or percent <= 0:
                    raise ValueError("percent must be > 0 for percent mode")
                target_w = max(1, int(round(src_w * (percent / 100.0))))
                target_h = max(1, int(round(src_h * (percent / 100.0))))
            else:
                if width is None or height is None or width <= 0 or height <= 0:
                    raise ValueError("width and height must be > 0 for dimensions mode")
                if keep_aspect_ratio:
                    ratio = min(width / src_w, height / src_h)
                    target_w = max(1, int(round(src_w * ratio)))
                    target_h = max(1, int(round(src_h * ratio)))
                else:
                    target_w = width
                    target_h = height

            if not upscale and (target_w > src_w or target_h > src_h):
                raise ValueError("Target dimensions exceed source bounds while upscale is disabled")

            resized = src.resize((target_w, target_h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            resized.save(out, format=_image_format_for_filename(source_image.filename))
            derived_bytes = out.getvalue()

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_output_filename(
            existing_filenames=existing_filenames,
            source_filename=source_image.filename,
            suggested_suffix="scale",
            output_name=output_name,
        )

        operation_params = {
            "mode": mode,
            "percent": percent,
            "width": width,
            "height": height,
            "keep_aspect_ratio": keep_aspect_ratio,
            "upscale": upscale,
            "target_width": target_w,
            "target_height": target_h,
        }
        derived, _ = _create_derived_image(
            session=session,
            source_image=source_image,
            filename=new_filename,
            image_bytes=derived_bytes,
            width=target_w,
            height=target_h,
            operation_type="scale",
            operation_params=operation_params,
            include_captions=include_captions,
            caption_copy_mode=caption_copy_mode,
        )
        session.commit()

        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": derived.id,
                "filename": derived.filename,
                "width": derived.width,
                "height": derived.height,
                "included": derived.included,
                "source_image_id": derived.source_image_id,
                "derived_operation": derived.derived_operation,
                "derived_operation_params": derived.derived_operation_params,
            },
            "operation": {
                "type": "scale",
                "params": operation_params,
            },
        }


def flip_image(
    *,
    project_path: str,
    image_id: int,
    mode: str,
    output_name: str | None = None,
    include_captions: bool = True,
    caption_copy_mode: str = "all_candidates",
) -> dict[str, object]:
    if mode not in {"horizontal", "vertical", "both"}:
        raise ValueError(f"Unsupported flip mode: {mode}")
    if caption_copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported caption copy mode: {caption_copy_mode}")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        source_blob = _load_image_blob(source_image, image_id)

        with Image.open(io.BytesIO(source_blob)) as src:
            transformed = src
            if mode in {"horizontal", "both"}:
                transformed = ImageOps.mirror(transformed)
            if mode in {"vertical", "both"}:
                transformed = ImageOps.flip(transformed)

            out = io.BytesIO()
            transformed.save(out, format=_image_format_for_filename(source_image.filename))
            derived_bytes = out.getvalue()
            derived_width, derived_height = transformed.size

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_output_filename(
            existing_filenames=existing_filenames,
            source_filename=source_image.filename,
            suggested_suffix=f"flip_{mode}",
            output_name=output_name,
        )

        derived, _ = _create_derived_image(
            session=session,
            source_image=source_image,
            filename=new_filename,
            image_bytes=derived_bytes,
            width=derived_width,
            height=derived_height,
            operation_type="flip",
            operation_params={"mode": mode},
            include_captions=include_captions,
            caption_copy_mode=caption_copy_mode,
        )
        session.commit()

        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": derived.id,
                "filename": derived.filename,
                "width": derived.width,
                "height": derived.height,
                "included": derived.included,
                "source_image_id": derived.source_image_id,
                "derived_operation": derived.derived_operation,
                "derived_operation_params": derived.derived_operation_params,
            },
            "operation": {
                "type": "flip",
                "params": {"mode": mode},
            },
        }


def rotate_image(
    *,
    project_path: str,
    image_id: int,
    angle: int,
    output_name: str | None = None,
    include_captions: bool = True,
    caption_copy_mode: str = "all_candidates",
) -> dict[str, object]:
    if angle not in {90, 180, 270}:
        raise ValueError("angle must be one of 90, 180, or 270")
    if caption_copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported caption copy mode: {caption_copy_mode}")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        source_blob = _load_image_blob(source_image, image_id)

        with Image.open(io.BytesIO(source_blob)) as src:
            transformed = src.rotate(-angle, expand=True)
            out = io.BytesIO()
            transformed.save(out, format=_image_format_for_filename(source_image.filename))
            derived_bytes = out.getvalue()
            derived_width, derived_height = transformed.size

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_output_filename(
            existing_filenames=existing_filenames,
            source_filename=source_image.filename,
            suggested_suffix=f"rot{angle}",
            output_name=output_name,
        )

        derived, _ = _create_derived_image(
            session=session,
            source_image=source_image,
            filename=new_filename,
            image_bytes=derived_bytes,
            width=derived_width,
            height=derived_height,
            operation_type="rotate",
            operation_params={"angle": angle},
            include_captions=include_captions,
            caption_copy_mode=caption_copy_mode,
        )
        session.commit()

        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": derived.id,
                "filename": derived.filename,
                "width": derived.width,
                "height": derived.height,
                "included": derived.included,
                "source_image_id": derived.source_image_id,
                "derived_operation": derived.derived_operation,
                "derived_operation_params": derived.derived_operation_params,
            },
            "operation": {
                "type": "rotate",
                "params": {"angle": angle},
            },
        }


def extract_region_image(
    *,
    project_path: str,
    image_id: int,
    x: int,
    y: int,
    width: int,
    height: int,
    output_name: str | None = None,
    include_captions: bool = True,
    caption_copy_mode: str = "all_candidates",
    add_source_reference_note: bool = True,
) -> dict[str, object]:
    if width <= 0 or height <= 0:
        raise ValueError("Extract width and height must be > 0")
    if x < 0 or y < 0:
        raise ValueError("Extract x/y must be >= 0")
    if caption_copy_mode not in {"active_only", "all_candidates", "none"}:
        raise ValueError(f"Unsupported caption copy mode: {caption_copy_mode}")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        source_image = _load_image_for_project(session, resolved_project_path, image_id)
        source_blob = _load_image_blob(source_image, image_id)

        with Image.open(io.BytesIO(source_blob)) as src:
            if x + width > src.width or y + height > src.height:
                raise ValueError("Extract rectangle must be within source image bounds")

            extracted = src.crop((x, y, x + width, y + height))
            out = io.BytesIO()
            extracted.save(out, format=_image_format_for_filename(source_image.filename))
            derived_bytes = out.getvalue()
            derived_width, derived_height = extracted.size

        existing_filenames = set(session.scalars(select(ImageRecord.filename)).all())
        new_filename = _build_output_filename(
            existing_filenames=existing_filenames,
            source_filename=source_image.filename,
            suggested_suffix="extract",
            output_name=output_name,
        )

        operation_params = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "add_source_reference_note": add_source_reference_note,
        }
        derived, _ = _create_derived_image(
            session=session,
            source_image=source_image,
            filename=new_filename,
            image_bytes=derived_bytes,
            width=derived_width,
            height=derived_height,
            operation_type="extract_region",
            operation_params=operation_params,
            include_captions=include_captions,
            caption_copy_mode=caption_copy_mode,
        )
        session.commit()

        return {
            "source_image_id": source_image.id,
            "new_image": {
                "id": derived.id,
                "filename": derived.filename,
                "width": derived.width,
                "height": derived.height,
                "included": derived.included,
                "source_image_id": derived.source_image_id,
                "derived_operation": derived.derived_operation,
                "derived_operation_params": derived.derived_operation_params,
            },
            "operation": {
                "type": "extract_region",
                "params": operation_params,
            },
        }


def delete_image(*, project_path: str, image_id: int, mode: str = "soft", confirm_hard_delete: bool = False) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        result = _delete_image_for_project(
            session=session,
            resolved_project_path=resolved_project_path,
            image_id=image_id,
            mode=mode,
            confirm_hard_delete=confirm_hard_delete,
        )
        session.commit()
        return result


def batch_delete_images(
    *,
    project_path: str,
    image_ids: list[int],
    mode: str = "soft",
    confirm_hard_delete: bool = False,
) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)
    normalized_image_ids = _normalize_image_ids(image_ids)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        deleted_ids: list[int] = []
        for image_id in normalized_image_ids:
            _delete_image_for_project(
                session=session,
                resolved_project_path=resolved_project_path,
                image_id=image_id,
                mode=mode,
                confirm_hard_delete=confirm_hard_delete,
            )
            deleted_ids.append(image_id)
        session.commit()

    return {
        "image_ids": deleted_ids,
        "deleted_count": len(deleted_ids),
        "mode": mode,
    }


def find_duplicate_images_by_hash(*, project_path: str) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        duplicate_groups = [
            _build_duplicate_group_summary(session, hash_value, images)
            for hash_value, images in _build_duplicate_groups(session)
        ]

    removable_image_count = sum(len(group.duplicate_images) for group in duplicate_groups)
    return {
        "duplicate_group_count": len(duplicate_groups),
        "removable_image_count": removable_image_count,
        "groups": [
            {
                "hash": group.hash_value,
                "hash_prefix": group.hash_value[:12],
                "kept_image": {
                    "id": group.kept_image_id,
                    "filename": group.kept_filename,
                    "caption_count": group.kept_caption_count,
                },
                "duplicate_images": group.duplicate_images,
            }
            for group in duplicate_groups
        ],
    }


def apply_duplicate_cleanup(
    *,
    project_path: str,
    mode: str = "soft",
    confirm_hard_delete: bool = False,
) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        groups = _build_duplicate_groups(session)
        captions_merged = 0
        captions_skipped = 0
        removed_image_ids: list[int] = []

        for _, images in groups:
            kept_image = images[0]
            kept_captions = session.scalars(
                select(CaptionRecord)
                .where(CaptionRecord.image_id == kept_image.id)
                .order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
            ).all()
            seen_caption_texts = {
                normalized_text
                for normalized_text in (_normalize_caption_text(caption.text) for caption in kept_captions)
                if normalized_text
            }
            has_active_caption = any(caption.is_active for caption in kept_captions)

            for duplicate_image in images[1:]:
                duplicate_captions = session.scalars(
                    select(CaptionRecord)
                    .where(CaptionRecord.image_id == duplicate_image.id)
                    .order_by(CaptionRecord.created_at.asc(), CaptionRecord.id.asc())
                ).all()

                for caption in duplicate_captions:
                    normalized_text = _normalize_caption_text(caption.text)
                    if not normalized_text:
                        continue
                    if normalized_text in seen_caption_texts:
                        captions_skipped += 1
                        continue

                    session.add(
                        CaptionRecord(
                            image_id=kept_image.id,
                            text=caption.text,
                            is_active=not has_active_caption,
                            source=caption.source,
                        )
                    )
                    seen_caption_texts.add(normalized_text)
                    captions_merged += 1
                    if not has_active_caption:
                        has_active_caption = True

                _delete_image_for_project(
                    session=session,
                    resolved_project_path=resolved_project_path,
                    image_id=duplicate_image.id,
                    mode=mode,
                    confirm_hard_delete=confirm_hard_delete,
                )
                removed_image_ids.append(duplicate_image.id)

        session.commit()

    return {
        "duplicate_group_count": len(groups),
        "removed_image_count": len(removed_image_ids),
        "removed_image_ids": removed_image_ids,
        "captions_merged": captions_merged,
        "captions_skipped": captions_skipped,
        "mode": mode,
    }


def restore_image(*, project_path: str, image_id: int) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

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
