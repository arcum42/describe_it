from __future__ import annotations

import fnmatch
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.db.models import CaptionRecord, ImageRecord
from backend.db.session import create_sqlite_session_factory
from backend.services.project_db_utils import load_project_record, require_existing_project_path


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class CaptionTextEditJob:
    id: str
    project_path: str
    operation: str
    status: str = "queued"
    total: int = 0
    completed: int = 0
    affected: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    current_label: str = ""
    last_error: str = ""
    result: dict[str, Any] = field(default_factory=dict)


class CaptionTextEditService:
    def __init__(self) -> None:
        self._jobs: dict[str, CaptionTextEditJob] = {}
        self._lock = threading.Lock()

    def _serialize(self, job: CaptionTextEditJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "project_path": job.project_path,
            "operation": job.operation,
            "status": job.status,
            "total": job.total,
            "completed": job.completed,
            "affected": job.affected,
            "current_label": job.current_label,
            "last_error": job.last_error,
            "result": job.result,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def get_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Caption text-edit job not found: {job_id}")
            return self._serialize(job)

    def _create_job(self, *, project_path: str, operation: str) -> CaptionTextEditJob:
        job = CaptionTextEditJob(
            id=str(uuid.uuid4()),
            project_path=project_path,
            operation=operation,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def start_delete_empty_captions(self, *, project_path: str) -> dict[str, Any]:
        resolved = require_existing_project_path(project_path)

        job = self._create_job(project_path=str(resolved), operation="delete_empty")
        threading.Thread(target=self._run_delete_empty, args=(job.id,), daemon=True).start()
        return self._serialize(job)

    def start_remove_tags(self, *, project_path: str, patterns: list[str]) -> dict[str, Any]:
        resolved = require_existing_project_path(project_path)

        normalized_patterns = [str(item).strip() for item in patterns if str(item).strip()]
        if not normalized_patterns:
            raise ValueError("Provide at least one tag pattern.")

        job = self._create_job(project_path=str(resolved), operation="remove_tags")
        threading.Thread(target=self._run_remove_tags, args=(job.id, normalized_patterns), daemon=True).start()
        return self._serialize(job)

    def start_add_common_caption(self, *, project_path: str, caption_text: str, scope: str) -> dict[str, Any]:
        resolved = require_existing_project_path(project_path)

        normalized_scope = str(scope or "without_caption").strip().lower()
        if normalized_scope not in {"all_images", "without_caption"}:
            raise ValueError("scope must be all_images or without_caption")

        normalized_text = str(caption_text or "").strip()
        if not normalized_text:
            raise ValueError("caption_text must not be empty")

        job = self._create_job(project_path=str(resolved), operation="add_common_caption")
        threading.Thread(
            target=self._run_add_common_caption,
            args=(job.id, normalized_text, normalized_scope),
            daemon=True,
        ).start()
        return self._serialize(job)

    def _run_delete_empty(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.updated_at = time.time()

        session_factory = create_sqlite_session_factory(Path(job.project_path))
        try:
            with session_factory() as session:
                project = load_project_record(session, Path(job.project_path))

                images = session.scalars(
                    select(ImageRecord)
                    .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
                    .order_by(ImageRecord.id.asc())
                ).all()
                image_ids = [item.id for item in images]
                if not image_ids:
                    with self._lock:
                        job.status = "completed"
                        job.result = {"deleted_captions_count": 0, "processed_captions_count": 0}
                        job.updated_at = time.time()
                    return

                captions = session.scalars(
                    select(CaptionRecord)
                    .where(CaptionRecord.image_id.in_(image_ids))
                    .order_by(CaptionRecord.image_id.asc(), CaptionRecord.id.asc())
                ).all()
                by_image: dict[int, list[CaptionRecord]] = {}
                for caption in captions:
                    by_image.setdefault(caption.image_id, []).append(caption)

                delete_targets = [caption for caption in captions if not str(caption.text or "").strip()]
                with self._lock:
                    job.total = len(delete_targets)
                    job.updated_at = time.time()

                if not delete_targets:
                    with self._lock:
                        job.status = "completed"
                        job.result = {"deleted_captions_count": 0, "processed_captions_count": 0}
                        job.updated_at = time.time()
                    return

                deleted_count = 0
                for caption in delete_targets:
                    group = by_image.get(caption.image_id, [])
                    remaining_after_delete = [item for item in group if item.id != caption.id]

                    if caption.is_active and remaining_after_delete:
                        replacement = sorted(remaining_after_delete, key=lambda item: item.id, reverse=True)[0]
                        for item in group:
                            item.is_active = item.id == replacement.id

                    session.delete(caption)
                    deleted_count += 1
                    with self._lock:
                        job.completed += 1
                        job.current_label = f"caption {caption.id}"
                        job.updated_at = time.time()

                session.commit()
                with self._lock:
                    job.affected = deleted_count
                    job.status = "completed"
                    job.result = {
                        "deleted_captions_count": deleted_count,
                        "processed_captions_count": len(delete_targets),
                    }
                    job.updated_at = time.time()
        except Exception as error:  # noqa: BLE001
            with self._lock:
                job.status = "failed"
                job.last_error = str(error)
                job.updated_at = time.time()

    def _run_remove_tags(self, job_id: str, patterns: list[str]) -> None:
        patterns_lower = [item.lower() for item in patterns]
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.updated_at = time.time()

        session_factory = create_sqlite_session_factory(Path(job.project_path))
        try:
            with session_factory() as session:
                project = load_project_record(session, Path(job.project_path))

                captions = session.scalars(
                    select(CaptionRecord)
                    .join(ImageRecord, CaptionRecord.image_id == ImageRecord.id)
                    .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
                    .order_by(CaptionRecord.id.asc())
                ).all()

                with self._lock:
                    job.total = len(captions)
                    job.updated_at = time.time()

                changed = 0
                removed_tags_total = 0
                for caption in captions:
                    text_value = str(caption.text or "")
                    segments = [item.strip() for item in text_value.split(",")]
                    segments = [item for item in segments if item]

                    kept_segments: list[str] = []
                    removed_here = 0
                    for segment in segments:
                        segment_lower = segment.lower()
                        if any(fnmatch.fnmatch(segment_lower, pattern) for pattern in patterns_lower):
                            removed_here += 1
                        else:
                            kept_segments.append(segment)

                    new_text = ", ".join(kept_segments)
                    if new_text != text_value:
                        caption.text = new_text
                        changed += 1
                    removed_tags_total += removed_here

                    with self._lock:
                        job.completed += 1
                        job.current_label = f"caption {caption.id}"
                        job.updated_at = time.time()

                session.commit()
                with self._lock:
                    job.affected = changed
                    job.status = "completed"
                    job.result = {
                        "updated_captions_count": changed,
                        "removed_tags_count": removed_tags_total,
                        "patterns": patterns,
                    }
                    job.updated_at = time.time()
        except Exception as error:  # noqa: BLE001
            with self._lock:
                job.status = "failed"
                job.last_error = str(error)
                job.updated_at = time.time()

    def _run_add_common_caption(self, job_id: str, caption_text: str, scope: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.updated_at = time.time()

        session_factory = create_sqlite_session_factory(Path(job.project_path))
        try:
            with session_factory() as session:
                project = load_project_record(session, Path(job.project_path))

                images = session.scalars(
                    select(ImageRecord)
                    .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
                    .order_by(ImageRecord.id.asc())
                ).all()

                captions = session.scalars(
                    select(CaptionRecord)
                    .join(ImageRecord, CaptionRecord.image_id == ImageRecord.id)
                    .where(ImageRecord.project_id == project.id, ImageRecord.deleted_at.is_(None))
                    .order_by(CaptionRecord.image_id.asc(), CaptionRecord.id.asc())
                ).all()
                by_image: dict[int, list[CaptionRecord]] = {}
                for caption in captions:
                    by_image.setdefault(caption.image_id, []).append(caption)

                target_images: list[ImageRecord] = []
                for image in images:
                    image_captions = by_image.get(image.id, [])
                    active = next((item for item in image_captions if item.is_active), None)
                    active_text = str(active.text or "").strip() if active else ""
                    if scope == "all_images":
                        target_images.append(image)
                    elif not active_text:
                        target_images.append(image)

                with self._lock:
                    job.total = len(target_images)
                    job.updated_at = time.time()

                created = 0
                activated = 0
                for image in target_images:
                    image_captions = by_image.get(image.id, [])
                    active = next((item for item in image_captions if item.is_active), None)
                    should_activate = active is None or not str(active.text or "").strip()

                    if should_activate:
                        for item in image_captions:
                            item.is_active = False

                    new_caption = CaptionRecord(
                        image_id=image.id,
                        text=caption_text,
                        is_active=should_activate,
                        source="batch_text_edit:add_common",
                    )
                    session.add(new_caption)
                    created += 1
                    if should_activate:
                        activated += 1

                    with self._lock:
                        job.completed += 1
                        job.current_label = image.filename
                        job.updated_at = time.time()

                session.commit()
                with self._lock:
                    job.affected = created
                    job.status = "completed"
                    job.result = {
                        "created_captions_count": created,
                        "activated_captions_count": activated,
                        "scope": scope,
                    }
                    job.updated_at = time.time()
        except Exception as error:  # noqa: BLE001
            with self._lock:
                job.status = "failed"
                job.last_error = str(error)
                job.updated_at = time.time()


caption_text_edit_service = CaptionTextEditService()
