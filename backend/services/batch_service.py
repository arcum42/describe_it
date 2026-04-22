from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.services.caption_service import apply_generated_caption
from backend.services.image_service import list_project_images
from backend.services.llm_service import generate_text_for_image_manual, generate_text_for_image_with_preset


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class BatchJob:
    id: str
    project_path: str
    target: str
    use_preset: bool
    preset_id: int | None
    backend: str
    model: str
    extra_instructions: str
    timeout_seconds: int
    make_active: bool
    output_mode: str
    skip_on_failure: bool
    retry_count: int
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "queued"
    total: int = 0
    completed: int = 0
    succeeded: int = 0
    failed: int = 0
    current_index: int = 0
    current_image_id: int | None = None
    current_filename: str = ""
    current_generated_text: str = ""
    last_error: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)
    pause_requested: bool = False
    cancel_requested: bool = False
    image_ids: list[int] = field(default_factory=list)
    image_filenames: dict[int, str] = field(default_factory=dict)


@dataclass
class BatchJobResult:
    job_id: str
    image_id: int
    filename: str
    status: str
    attempts: int
    generated_text: str
    error: str
    started_at: float
    finished_at: float


class BatchService:
    def __init__(self) -> None:
        self._jobs: dict[str, BatchJob] = {}
        self._lock = threading.Lock()
        self._ensure_schema()
        self._load_jobs()

    def _db_path(self) -> Path:
        settings = get_settings()
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        return settings.state_dir / "app_state.db"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path())
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    target TEXT NOT NULL,
                    use_preset INTEGER NOT NULL,
                    preset_id INTEGER,
                    backend TEXT NOT NULL,
                    model TEXT NOT NULL,
                    extra_instructions TEXT NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    make_active INTEGER NOT NULL,
                    output_mode TEXT NOT NULL,
                    skip_on_failure INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    completed INTEGER NOT NULL,
                    succeeded INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    current_index INTEGER NOT NULL,
                    current_image_id INTEGER,
                    current_filename TEXT NOT NULL,
                    current_generated_text TEXT NOT NULL,
                    last_error TEXT NOT NULL,
                    pause_requested INTEGER NOT NULL,
                    cancel_requested INTEGER NOT NULL,
                    image_ids_json TEXT NOT NULL,
                    image_filenames_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS batch_job_results (
                    job_id TEXT NOT NULL,
                    image_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    generated_text TEXT NOT NULL,
                    error TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    finished_at REAL NOT NULL,
                    PRIMARY KEY (job_id, image_id),
                    FOREIGN KEY (job_id) REFERENCES batch_jobs(id)
                );
                """
            )
            connection.commit()

    def _save_job(self, job: BatchJob) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO batch_jobs (
                    id, project_path, target, use_preset, preset_id, backend, model,
                    extra_instructions, timeout_seconds, make_active, output_mode,
                    skip_on_failure, retry_count, created_at, updated_at, status,
                    total, completed, succeeded, failed, current_index, current_image_id,
                    current_filename, current_generated_text, last_error,
                    pause_requested, cancel_requested, image_ids_json,
                    image_filenames_json, errors_json
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(id) DO UPDATE SET
                    project_path=excluded.project_path,
                    target=excluded.target,
                    use_preset=excluded.use_preset,
                    preset_id=excluded.preset_id,
                    backend=excluded.backend,
                    model=excluded.model,
                    extra_instructions=excluded.extra_instructions,
                    timeout_seconds=excluded.timeout_seconds,
                    make_active=excluded.make_active,
                    output_mode=excluded.output_mode,
                    skip_on_failure=excluded.skip_on_failure,
                    retry_count=excluded.retry_count,
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    total=excluded.total,
                    completed=excluded.completed,
                    succeeded=excluded.succeeded,
                    failed=excluded.failed,
                    current_index=excluded.current_index,
                    current_image_id=excluded.current_image_id,
                    current_filename=excluded.current_filename,
                    current_generated_text=excluded.current_generated_text,
                    last_error=excluded.last_error,
                    pause_requested=excluded.pause_requested,
                    cancel_requested=excluded.cancel_requested,
                    image_ids_json=excluded.image_ids_json,
                    image_filenames_json=excluded.image_filenames_json,
                    errors_json=excluded.errors_json
                """,
                (
                    job.id,
                    job.project_path,
                    job.target,
                    1 if job.use_preset else 0,
                    job.preset_id,
                    job.backend,
                    job.model,
                    job.extra_instructions,
                    job.timeout_seconds,
                    1 if job.make_active else 0,
                    job.output_mode,
                    1 if job.skip_on_failure else 0,
                    job.retry_count,
                    job.created_at,
                    job.updated_at,
                    job.status,
                    job.total,
                    job.completed,
                    job.succeeded,
                    job.failed,
                    job.current_index,
                    job.current_image_id,
                    job.current_filename,
                    job.current_generated_text,
                    job.last_error,
                    1 if job.pause_requested else 0,
                    1 if job.cancel_requested else 0,
                    json.dumps(job.image_ids),
                    json.dumps(job.image_filenames),
                    json.dumps(job.errors[-500:]),
                ),
            )
            connection.commit()

    def _save_result(self, result: BatchJobResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO batch_job_results (
                    job_id, image_id, filename, status, attempts, generated_text, error, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, image_id) DO UPDATE SET
                    filename=excluded.filename,
                    status=excluded.status,
                    attempts=excluded.attempts,
                    generated_text=excluded.generated_text,
                    error=excluded.error,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at
                """,
                (
                    result.job_id,
                    result.image_id,
                    result.filename,
                    result.status,
                    result.attempts,
                    result.generated_text,
                    result.error,
                    result.started_at,
                    result.finished_at,
                ),
            )
            connection.commit()

    def _load_jobs(self) -> None:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM batch_jobs ORDER BY created_at DESC").fetchall()

        for row in rows:
            status = row["status"]
            pause_requested = bool(row["pause_requested"])
            if status in {"queued", "running"}:
                status = "paused"
                pause_requested = True

            try:
                image_ids = json.loads(row["image_ids_json"] or "[]")
            except json.JSONDecodeError:
                image_ids = []
            try:
                image_filenames = json.loads(row["image_filenames_json"] or "{}")
            except json.JSONDecodeError:
                image_filenames = {}
            image_filenames = {int(key): str(value) for key, value in image_filenames.items()}
            try:
                errors = json.loads(row["errors_json"] or "[]")
            except json.JSONDecodeError:
                errors = []

            job = BatchJob(
                id=row["id"],
                project_path=row["project_path"],
                target=row["target"],
                use_preset=bool(row["use_preset"]),
                preset_id=row["preset_id"],
                backend=row["backend"],
                model=row["model"],
                extra_instructions=row["extra_instructions"],
                timeout_seconds=int(row["timeout_seconds"]),
                make_active=bool(row["make_active"]),
                output_mode=row["output_mode"],
                skip_on_failure=bool(row["skip_on_failure"]),
                retry_count=int(row["retry_count"]),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
                status=status,
                total=int(row["total"]),
                completed=int(row["completed"]),
                succeeded=int(row["succeeded"]),
                failed=int(row["failed"]),
                current_index=int(row["current_index"]),
                current_image_id=row["current_image_id"],
                current_filename=row["current_filename"],
                current_generated_text=row["current_generated_text"],
                last_error=row["last_error"],
                pause_requested=pause_requested,
                cancel_requested=bool(row["cancel_requested"]),
                image_ids=image_ids,
                image_filenames=image_filenames,
                errors=errors,
            )
            self._jobs[job.id] = job
            self._save_job(job)

    def _now(self) -> float:
        return time.time()

    def _serialize(self, job: BatchJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "project_path": job.project_path,
            "status": job.status,
            "target": job.target,
            "use_preset": job.use_preset,
            "preset_id": job.preset_id,
            "backend": job.backend,
            "model": job.model,
            "timeout_seconds": job.timeout_seconds,
            "make_active": job.make_active,
            "output_mode": job.output_mode,
            "skip_on_failure": job.skip_on_failure,
            "retry_count": job.retry_count,
            "total": job.total,
            "completed": job.completed,
            "succeeded": job.succeeded,
            "failed": job.failed,
            "current_image_id": job.current_image_id,
            "current_filename": job.current_filename,
            "current_generated_text": job.current_generated_text,
            "last_error": job.last_error,
            "errors": job.errors[-20:],
            "result_count": job.succeeded + job.failed,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    def _collect_images(self, *, project_path: str, target: str) -> tuple[list[int], dict[int, str]]:
        images = list_project_images(project_path=project_path)
        if target == "all":
            filtered = images
        elif target == "included":
            filtered = [item for item in images if item.included]
        elif target == "uncaptioned":
            filtered = [item for item in images if item.included and not (item.active_caption_preview or "").strip()]
        else:
            raise ValueError(f"Unsupported batch target: {target}")

        image_ids = [item.id for item in filtered]
        image_filenames = {item.id: item.filename for item in filtered}
        return image_ids, image_filenames

    def _generate_for_image(self, job: BatchJob, image_id: int) -> tuple[str, str, str]:
        if job.use_preset:
            if job.preset_id is None:
                raise ValueError("Preset is required when use_preset is enabled.")
            result = generate_text_for_image_with_preset(
                project_path=job.project_path,
                image_id=image_id,
                preset_id=job.preset_id,
                timeout_seconds=job.timeout_seconds,
            )
            backend = str(result.get("backend") or "")
            model = str(result.get("model") or "")
            generated_text = str(result.get("text") or "")
            return generated_text, backend, model

        result = generate_text_for_image_manual(
            project_path=job.project_path,
            image_id=image_id,
            backend=job.backend,
            model=job.model,
            extra_instructions=job.extra_instructions,
            timeout_seconds=job.timeout_seconds,
        )
        backend = str(result.get("backend") or "")
        model = str(result.get("model") or "")
        generated_text = str(result.get("text") or "")
        return generated_text, backend, model

    def _process_image(self, job: BatchJob, image_id: int) -> None:
        attempt = 0
        max_attempts = max(1, job.retry_count + 1)
        started_at = self._now()
        while attempt < max_attempts:
            attempt += 1
            try:
                generated_text, backend, model = self._generate_for_image(job, image_id)
                source = f"llm:{backend}:{model}" if not job.use_preset else f"llm:preset:{job.preset_id}:{backend}:{model}"
                apply_generated_caption(
                    project_path=job.project_path,
                    image_id=image_id,
                    generated_text=generated_text,
                    mode=job.output_mode,
                    source=source,
                    make_active=job.make_active,
                )
                with self._lock:
                    job.current_generated_text = generated_text
                    job.succeeded += 1
                    job.updated_at = self._now()
                    self._save_job(job)
                self._save_result(
                    BatchJobResult(
                        job_id=job.id,
                        image_id=image_id,
                        filename=job.current_filename,
                        status="succeeded",
                        attempts=attempt,
                        generated_text=generated_text,
                        error="",
                        started_at=started_at,
                        finished_at=self._now(),
                    )
                )
                return
            except Exception as error:  # noqa: BLE001
                with self._lock:
                    job.last_error = str(error)
                    job.errors.append({"image_id": image_id, "attempt": attempt, "error": str(error)})
                    job.updated_at = self._now()
                    self._save_job(job)
                if attempt >= max_attempts:
                    self._save_result(
                        BatchJobResult(
                            job_id=job.id,
                            image_id=image_id,
                            filename=job.current_filename,
                            status="failed",
                            attempts=attempt,
                            generated_text="",
                            error=str(error),
                            started_at=started_at,
                            finished_at=self._now(),
                        )
                    )
                    raise

    def _run_job(self, job_id: str) -> None:
        while True:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return

                if job.cancel_requested:
                    job.status = "cancelled"
                    job.updated_at = self._now()
                    self._save_job(job)
                    return

                if job.pause_requested:
                    job.status = "paused"
                    job.updated_at = self._now()
                    self._save_job(job)
                    return

                if job.current_index >= len(job.image_ids):
                    job.status = "completed"
                    job.updated_at = self._now()
                    self._save_job(job)
                    return

                image_id = job.image_ids[job.current_index]
                job.current_image_id = image_id
                job.current_filename = job.image_filenames.get(image_id, f"image-{image_id}")
                job.status = "running"
                job.updated_at = self._now()
                self._save_job(job)

            try:
                self._process_image(job, image_id)
            except Exception:  # noqa: BLE001
                with self._lock:
                    job.failed += 1
                    job.completed += 1
                    if job.skip_on_failure:
                        job.current_index += 1
                        job.updated_at = self._now()
                        self._save_job(job)
                        continue
                    job.status = "failed"
                    job.updated_at = self._now()
                    self._save_job(job)
                    return

            with self._lock:
                job.completed += 1
                job.current_index += 1
                job.updated_at = self._now()
                self._save_job(job)

    def create_job(
        self,
        *,
        project_path: str,
        target: str,
        use_preset: bool,
        preset_id: int | None,
        backend: str,
        model: str,
        extra_instructions: str,
        timeout_seconds: int,
        make_active: bool,
        output_mode: str,
        skip_on_failure: bool,
        retry_count: int,
    ) -> dict[str, Any]:
        image_ids, image_filenames = self._collect_images(project_path=project_path, target=target)
        if not image_ids:
            raise ValueError("No images matched the selected batch target.")

        job = BatchJob(
            id=str(uuid.uuid4()),
            project_path=project_path,
            target=target,
            use_preset=use_preset,
            preset_id=preset_id,
            backend=backend,
            model=model,
            extra_instructions=extra_instructions,
            timeout_seconds=timeout_seconds,
            make_active=make_active,
            output_mode=output_mode,
            skip_on_failure=skip_on_failure,
            retry_count=max(0, int(retry_count)),
            image_ids=image_ids,
            image_filenames=image_filenames,
            total=len(image_ids),
        )

        with self._lock:
            self._jobs[job.id] = job
            self._save_job(job)

        threading.Thread(target=self._run_job, args=(job.id,), daemon=True).start()
        return self._serialize(job)

    def get_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Batch job not found: {job_id}")
            return self._serialize(job)

    def get_job_results(self, *, job_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with self._lock:
            if job_id not in self._jobs:
                raise ValueError(f"Batch job not found: {job_id}")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT job_id, image_id, filename, status, attempts, generated_text, error, started_at, finished_at
                FROM batch_job_results
                WHERE job_id = ?
                ORDER BY image_id ASC
                LIMIT ?
                """,
                (job_id, max(1, min(2000, int(limit)))),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_job_results_csv(self, *, job_id: str) -> str:
        rows = self.get_job_results(job_id=job_id, limit=5000)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["job_id", "image_id", "filename", "status", "attempts", "error", "generated_text", "started_at", "finished_at"])
        for row in rows:
            writer.writerow(
                [
                    row.get("job_id", ""),
                    row.get("image_id", ""),
                    row.get("filename", ""),
                    row.get("status", ""),
                    row.get("attempts", ""),
                    row.get("error", ""),
                    row.get("generated_text", ""),
                    row.get("started_at", ""),
                    row.get("finished_at", ""),
                ]
            )
        return buffer.getvalue()

    def list_jobs_for_project(self, *, project_path: str) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [job for job in self._jobs.values() if job.project_path == project_path]
        jobs.sort(key=lambda item: item.created_at, reverse=True)
        return [self._serialize(job) for job in jobs]

    def pause_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Batch job not found: {job_id}")
            if job.status in TERMINAL_STATUSES:
                return self._serialize(job)
            job.pause_requested = True
            if job.status == "queued":
                job.status = "paused"
            job.updated_at = self._now()
            self._save_job(job)
            return self._serialize(job)

    def cancel_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Batch job not found: {job_id}")
            if job.status in TERMINAL_STATUSES:
                return self._serialize(job)
            job.cancel_requested = True
            job.updated_at = self._now()
            self._save_job(job)
            return self._serialize(job)

    def resume_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError(f"Batch job not found: {job_id}")
            if job.status == "completed" or job.status == "cancelled":
                return self._serialize(job)
            job.pause_requested = False
            job.cancel_requested = False
            if job.status == "failed" and not job.skip_on_failure:
                # Resume from the failed image by rewinding one step.
                job.current_index = max(0, job.completed - 1)
                job.completed = max(0, job.completed - 1)
                job.failed = max(0, job.failed - 1)
            job.status = "queued"
            job.updated_at = self._now()
            self._save_job(job)

        threading.Thread(target=self._run_job, args=(job.id,), daemon=True).start()
        return self.get_job(job_id=job_id)


batch_service = BatchService()
