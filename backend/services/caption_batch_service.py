from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text

from backend.db.models import CaptionRecord, ImageRecord
from backend.db.session import create_sqlite_session_factory
from backend.services.project_db_utils import load_project_record, require_existing_project_path


class BatchPreviewNotFoundError(Exception):
    pass


class BatchPreviewExpiredError(Exception):
    pass


class BatchOperationNotFoundError(Exception):
    pass


class BatchOperationAlreadyUndoneError(Exception):
    pass


def _compile_pattern(*, find_text: str, mode: str, case_sensitive: bool) -> re.Pattern[str]:
    if not find_text:
        raise ValueError("find_text must not be empty")

    normalized_mode = (mode or "plain").strip().lower()
    if normalized_mode not in {"plain", "regex"}:
        raise ValueError(f"Unsupported query mode: {mode}")

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern_text = find_text if normalized_mode == "regex" else re.escape(find_text)
    try:
        return re.compile(pattern_text, flags)
    except re.error as error:
        raise ValueError(f"Invalid regex pattern: {error}") from error


def _load_candidate_captions(*, session, project_id: int, scope: dict[str, object]) -> list[tuple[CaptionRecord, ImageRecord]]:
    caption_scope = (scope.get("caption_scope") or "active_only").strip().lower()
    if caption_scope not in {"active_only", "all_candidates"}:
        raise ValueError(f"Unsupported caption_scope: {caption_scope}")

    image_scope = (scope.get("image_scope") or "all").strip().lower()
    if image_scope not in {"all", "included_only", "selected_ids"}:
        raise ValueError(f"Unsupported image_scope: {image_scope}")

    stmt = (
        select(CaptionRecord, ImageRecord)
        .join(ImageRecord, CaptionRecord.image_id == ImageRecord.id)
        .where(ImageRecord.project_id == project_id)
        .order_by(ImageRecord.id.asc(), CaptionRecord.id.asc())
    )

    if caption_scope == "active_only":
        stmt = stmt.where(CaptionRecord.is_active.is_(True))

    if image_scope == "included_only":
        stmt = stmt.where(ImageRecord.included.is_(True))
    elif image_scope == "selected_ids":
        image_ids = scope.get("image_ids")
        if not isinstance(image_ids, list) or not image_ids:
            raise ValueError("image_ids must be a non-empty array when image_scope is selected_ids")
        normalized_ids = []
        for value in image_ids:
            if not isinstance(value, int) or value <= 0:
                raise ValueError("image_ids must contain positive integers")
            normalized_ids.append(value)
        stmt = stmt.where(ImageRecord.id.in_(normalized_ids))

    return list(session.execute(stmt).all())


def preview_batch_replace(*, project_path: str, query: dict[str, object], scope: dict[str, object]) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    find_text = str(query.get("find_text") or "")
    replace_text = str(query.get("replace_text") or "")
    mode = str(query.get("mode") or "plain")
    case_sensitive = bool(query.get("case_sensitive", False))

    pattern = _compile_pattern(find_text=find_text, mode=mode, case_sensitive=case_sensitive)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = load_project_record(session, resolved_project_path)
        rows = _load_candidate_captions(session=session, project_id=project.id, scope=scope)

        changes: list[dict[str, object]] = []
        impacted_images: set[int] = set()
        for caption, image in rows:
            before = caption.text or ""
            after = pattern.sub(replace_text, before)
            if after == before:
                continue
            changes.append(
                {
                    "image_id": image.id,
                    "caption_id": caption.id,
                    "before_text": before,
                    "after_text": after,
                }
            )
            impacted_images.add(image.id)

        preview_id = str(uuid4())
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(minutes=15)

        request_payload = {
            "query": {
                "find_text": find_text,
                "replace_text": replace_text,
                "mode": mode,
                "case_sensitive": case_sensitive,
            },
            "scope": scope,
        }

        session.execute(
            text(
                """
                INSERT INTO caption_batch_previews (
                    id,
                    project_id,
                    request_json,
                    changes_json,
                    impacted_captions_count,
                    impacted_images_count,
                    created_at,
                    expires_at,
                    applied_at
                ) VALUES (
                    :id,
                    :project_id,
                    :request_json,
                    :changes_json,
                    :impacted_captions_count,
                    :impacted_images_count,
                    :created_at,
                    :expires_at,
                    NULL
                )
                """
            ),
            {
                "id": preview_id,
                "project_id": project.id,
                "request_json": json.dumps(request_payload),
                "changes_json": json.dumps(changes),
                "impacted_captions_count": len(changes),
                "impacted_images_count": len(impacted_images),
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            },
        )
        session.commit()

        return {
            "preview_id": preview_id,
            "impacted_captions_count": len(changes),
            "impacted_images_count": len(impacted_images),
            "sample_changes": [
                {
                    "image_id": item["image_id"],
                    "caption_id": item["caption_id"],
                    "before_preview": item["before_text"],
                    "after_preview": item["after_text"],
                }
                for item in changes[:25]
            ],
            "warnings": [] if changes else ["No captions matched the current query/scope."],
            "expires_at": expires_at.isoformat(),
        }


def apply_batch_replace(
    *,
    project_path: str,
    preview_id: str,
    confirm: bool,
    create_undo_snapshot: bool = True,
) -> dict[str, object]:
    if not confirm:
        raise ValueError("confirm must be true to apply a batch replace")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = load_project_record(session, resolved_project_path)
        preview_row = session.execute(
            text(
                """
                SELECT id, request_json, changes_json, expires_at, applied_at
                FROM caption_batch_previews
                WHERE id = :preview_id AND project_id = :project_id
                LIMIT 1
                """
            ),
            {"preview_id": preview_id, "project_id": project.id},
        ).mappings().first()

        if preview_row is None:
            raise BatchPreviewNotFoundError(f"Preview not found: {preview_id}")
        if preview_row["applied_at"] is not None:
            raise BatchPreviewExpiredError("Preview already applied")

        expires_at = datetime.fromisoformat(preview_row["expires_at"])
        if datetime.now(UTC) > expires_at:
            raise BatchPreviewExpiredError("Preview has expired")

        changes = json.loads(preview_row["changes_json"])
        if not isinstance(changes, list):
            raise ValueError("Preview changes payload is invalid")

        before_snapshot: list[dict[str, object]] = []
        after_snapshot: list[dict[str, object]] = []
        updated_images: set[int] = set()

        for change in changes:
            caption_id = int(change["caption_id"])
            image_id = int(change["image_id"])
            target_after = str(change["after_text"])

            row = session.execute(
                text(
                    """
                    SELECT c.id AS caption_id, c.text AS caption_text, i.id AS image_id
                    FROM captions c
                    JOIN images i ON i.id = c.image_id
                    WHERE c.id = :caption_id AND i.id = :image_id AND i.project_id = :project_id
                    LIMIT 1
                    """
                ),
                {"caption_id": caption_id, "image_id": image_id, "project_id": project.id},
            ).mappings().first()
            if row is None:
                continue

            before_snapshot.append(
                {
                    "caption_id": caption_id,
                    "image_id": image_id,
                    "text": row["caption_text"] or "",
                }
            )
            after_snapshot.append(
                {
                    "caption_id": caption_id,
                    "image_id": image_id,
                    "text": target_after,
                }
            )
            updated_images.add(image_id)

            session.execute(
                text("UPDATE captions SET text = :text WHERE id = :caption_id"),
                {"text": target_after, "caption_id": caption_id},
            )

        operation_id = str(uuid4())
        session.execute(
            text(
                """
                INSERT INTO caption_batch_operations (
                    id,
                    project_id,
                    preview_id,
                    action,
                    request_json,
                    before_snapshot_json,
                    after_snapshot_json,
                    updated_captions_count,
                    updated_images_count,
                    can_undo,
                    created_at,
                    undone_at
                ) VALUES (
                    :id,
                    :project_id,
                    :preview_id,
                    :action,
                    :request_json,
                    :before_snapshot_json,
                    :after_snapshot_json,
                    :updated_captions_count,
                    :updated_images_count,
                    :can_undo,
                    :created_at,
                    NULL
                )
                """
            ),
            {
                "id": operation_id,
                "project_id": project.id,
                "preview_id": preview_id,
                "action": "replace",
                "request_json": preview_row["request_json"],
                "before_snapshot_json": json.dumps(before_snapshot),
                "after_snapshot_json": json.dumps(after_snapshot),
                "updated_captions_count": len(before_snapshot),
                "updated_images_count": len(updated_images),
                "can_undo": 1 if create_undo_snapshot else 0,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        session.execute(
            text("UPDATE caption_batch_previews SET applied_at = :applied_at WHERE id = :preview_id"),
            {"applied_at": datetime.now(UTC).isoformat(), "preview_id": preview_id},
        )

        session.commit()
        return {
            "operation_id": operation_id,
            "updated_captions_count": len(before_snapshot),
            "updated_images_count": len(updated_images),
            "undo_available": bool(create_undo_snapshot),
        }


def undo_batch_replace(*, project_path: str, operation_id: str | None = None) -> dict[str, object]:
    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = load_project_record(session, resolved_project_path)

        if operation_id:
            operation_row = session.execute(
                text(
                    """
                    SELECT id, before_snapshot_json, can_undo, undone_at
                    FROM caption_batch_operations
                    WHERE id = :operation_id AND project_id = :project_id
                    LIMIT 1
                    """
                ),
                {"operation_id": operation_id, "project_id": project.id},
            ).mappings().first()
        else:
            operation_row = session.execute(
                text(
                    """
                    SELECT id, before_snapshot_json, can_undo, undone_at
                    FROM caption_batch_operations
                    WHERE project_id = :project_id AND can_undo = 1 AND undone_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"project_id": project.id},
            ).mappings().first()

        if operation_row is None:
            raise BatchOperationNotFoundError("No undoable caption batch operation found")
        if int(operation_row["can_undo"]) != 1:
            raise BatchOperationNotFoundError("Operation is not undoable")
        if operation_row["undone_at"] is not None:
            raise BatchOperationAlreadyUndoneError(f"Operation already undone: {operation_row['id']}")

        before_snapshot = json.loads(operation_row["before_snapshot_json"])
        restored = 0
        for item in before_snapshot:
            caption_id = int(item["caption_id"])
            image_id = int(item["image_id"])
            original_text = str(item["text"])

            row = session.execute(
                text(
                    """
                    SELECT c.id AS caption_id
                    FROM captions c
                    JOIN images i ON i.id = c.image_id
                    WHERE c.id = :caption_id AND i.id = :image_id AND i.project_id = :project_id
                    LIMIT 1
                    """
                ),
                {"caption_id": caption_id, "image_id": image_id, "project_id": project.id},
            ).mappings().first()
            if row is None:
                continue

            session.execute(
                text("UPDATE captions SET text = :text WHERE id = :caption_id"),
                {"text": original_text, "caption_id": caption_id},
            )
            restored += 1

        session.execute(
            text("UPDATE caption_batch_operations SET undone_at = :undone_at WHERE id = :operation_id"),
            {"undone_at": datetime.now(UTC).isoformat(), "operation_id": operation_row["id"]},
        )
        session.commit()

        return {
            "undone_operation_id": operation_row["id"],
            "restored_captions_count": restored,
        }


def list_batch_operations(*, project_path: str, limit: int = 50) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 200:
        raise ValueError("limit must be <= 200")

    resolved_project_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_project_path)
    with session_factory() as session:
        project = load_project_record(session, resolved_project_path)
        rows = session.execute(
            text(
                """
                SELECT id, action, created_at, updated_captions_count, updated_images_count, undone_at
                FROM caption_batch_operations
                WHERE project_id = :project_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"project_id": project.id, "limit": limit},
        ).mappings().all()

        return [
            {
                "operation_id": row["id"],
                "type": row["action"],
                "created_at": row["created_at"],
                "impacted_captions_count": int(row["updated_captions_count"] or 0),
                "impacted_images_count": int(row["updated_images_count"] or 0),
                "undone_at": row["undone_at"],
            }
            for row in rows
        ]
