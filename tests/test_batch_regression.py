from __future__ import annotations

import csv
import io
import json
import sqlite3
import time
import uuid
from pathlib import Path

import pytest

from backend.services.batch_service import BatchJob, BatchService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connect(db_path: Path):
    """Return a _connect method that sets row_factory so dict-style column access works."""
    def _connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    return _connect


def _make_job(job_id: str, project_path: str, status: str) -> BatchJob:
    return BatchJob(
        id=job_id,
        project_path=project_path,
        target="all",
        use_preset=False,
        preset_id=None,
        backend="ollama",
        model="test-model",
        extra_instructions="",
        timeout_seconds=30,
        make_active=True,
        output_mode="append",
        skip_on_failure=False,
        retry_count=0,
        status=status,
        total=3,
        completed=1,
        succeeded=1,
        failed=0,
        current_index=1,
        current_image_id=10,
        current_filename="img1.png",
        current_generated_text="a test caption",
        last_error="",
        image_ids=[10, 11, 12],
        image_filenames={10: "img1.png", 11: "img2.png", 12: "img3.png"},
    )


def _write_job_to_db(db_path: Path, job: BatchJob) -> None:
    """Directly insert a batch job into app_state.db to simulate a persisted state."""
    connection = sqlite3.connect(db_path)
    try:
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
        now = time.time()
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                now,
                now,
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
                0,  # pause_requested
                0,  # cancel_requested
                json.dumps(job.image_ids),
                json.dumps({str(k): v for k, v in job.image_filenames.items()}),
                json.dumps(job.errors),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _write_result_to_db(
    db_path: Path,
    *,
    job_id: str,
    image_id: int,
    filename: str,
    status: str,
    generated_text: str,
    error: str = "",
    attempts: int = 1,
) -> None:
    connection = sqlite3.connect(db_path)
    try:
        now = time.time()
        connection.execute(
            """
            INSERT OR REPLACE INTO batch_job_results
                (job_id, image_id, filename, status, attempts, generated_text, error, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, image_id, filename, status, attempts, generated_text, error, now, now),
        )
        connection.commit()
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_restart_converts_running_jobs_to_paused(tmp_path: Path, monkeypatch) -> None:
    """On service startup, jobs with status 'queued' or 'running' must be converted to 'paused'."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    job_id = str(uuid.uuid4())
    job = _make_job(job_id, str(tmp_path / "project.db"), status="running")
    _write_job_to_db(db_path, job)

    service = BatchService.__new__(BatchService)
    service._jobs = {}
    service._lock = __import__("threading").Lock()
    # Patch _save_job to use our tmp db
    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415
    service._db_path = lambda: db_path
    service._connect = _make_connect(db_path)
    _BS._ensure_schema(service)
    _BS._load_jobs(service)

    loaded = service._jobs.get(job_id)
    assert loaded is not None, "Job was not loaded from the database"
    assert loaded.status == "paused", f"Expected 'paused', got '{loaded.status}'"
    assert loaded.pause_requested is True


def test_restart_converts_queued_jobs_to_paused(tmp_path: Path, monkeypatch) -> None:
    """On service startup, a queued job (never started) is also converted to paused."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    job_id = str(uuid.uuid4())
    job = _make_job(job_id, str(tmp_path / "project.db"), status="queued")
    _write_job_to_db(db_path, job)

    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415
    service = BatchService.__new__(BatchService)
    service._jobs = {}
    service._lock = __import__("threading").Lock()
    service._db_path = lambda: db_path
    service._connect = _make_connect(db_path)
    _BS._ensure_schema(service)
    _BS._load_jobs(service)

    loaded = service._jobs.get(job_id)
    assert loaded is not None
    assert loaded.status == "paused"
    assert loaded.pause_requested is True


def test_restart_preserves_terminal_job_status(tmp_path: Path, monkeypatch) -> None:
    """On service startup, jobs with terminal status ('completed', 'failed', 'cancelled') are left unchanged."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415

    for terminal_status in ("completed", "failed", "cancelled"):
        job_id = str(uuid.uuid4())
        job = _make_job(job_id, str(tmp_path / "project.db"), status=terminal_status)
        _write_job_to_db(db_path, job)

        service = BatchService.__new__(BatchService)
        service._jobs = {}
        service._lock = __import__("threading").Lock()
        service._db_path = lambda: db_path
        service._connect = _make_connect(db_path)
        _BS._ensure_schema(service)
        _BS._load_jobs(service)

        loaded = service._jobs.get(job_id)
        assert loaded is not None, f"Job with status '{terminal_status}' was not loaded"
        assert loaded.status == terminal_status, (
            f"Terminal status '{terminal_status}' was mutated to '{loaded.status}'"
        )


def test_get_job_results_returns_all_rows(tmp_path: Path, monkeypatch) -> None:
    """get_job_results must return one entry per stored result with expected columns."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    job_id = str(uuid.uuid4())
    job = _make_job(job_id, str(tmp_path / "project.db"), status="completed")
    _write_job_to_db(db_path, job)
    _write_result_to_db(db_path, job_id=job_id, image_id=10, filename="img1.png", status="succeeded", generated_text="caption A")
    _write_result_to_db(db_path, job_id=job_id, image_id=11, filename="img2.png", status="succeeded", generated_text="caption B")
    _write_result_to_db(db_path, job_id=job_id, image_id=12, filename="img3.png", status="failed", generated_text="", error="timeout")

    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415
    service = BatchService.__new__(BatchService)
    service._jobs = {}
    service._lock = __import__("threading").Lock()
    service._db_path = lambda: db_path
    service._connect = _make_connect(db_path)
    _BS._ensure_schema(service)
    _BS._load_jobs(service)

    results = _BS.get_job_results(service, job_id=job_id)
    assert len(results) == 3

    statuses = {row["image_id"]: row["status"] for row in results}
    assert statuses[10] == "succeeded"
    assert statuses[11] == "succeeded"
    assert statuses[12] == "failed"

    expected_columns = {"job_id", "image_id", "filename", "status", "attempts", "generated_text", "error", "started_at", "finished_at"}
    for row in results:
        assert expected_columns.issubset(row.keys()), f"Row missing columns: {expected_columns - row.keys()}"


def test_export_csv_columns_and_row_count(tmp_path: Path, monkeypatch) -> None:
    """export_job_results_csv must produce a valid CSV with correct headers and one data row per result."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    job_id = str(uuid.uuid4())
    job = _make_job(job_id, str(tmp_path / "project.db"), status="completed")
    _write_job_to_db(db_path, job)
    _write_result_to_db(db_path, job_id=job_id, image_id=10, filename="img1.png", status="succeeded", generated_text="caption A")
    _write_result_to_db(db_path, job_id=job_id, image_id=11, filename="img2.png", status="failed", generated_text="", error="timeout")

    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415
    service = BatchService.__new__(BatchService)
    service._jobs = {}
    service._lock = __import__("threading").Lock()
    service._db_path = lambda: db_path
    service._connect = _make_connect(db_path)
    _BS._ensure_schema(service)
    _BS._load_jobs(service)

    csv_text = _BS.export_job_results_csv(service, job_id=job_id)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    expected_headers = {"job_id", "image_id", "filename", "status", "attempts", "error", "generated_text", "started_at", "finished_at"}
    assert expected_headers == set(reader.fieldnames or []), f"Unexpected CSV headers: {reader.fieldnames}"
    assert len(rows) == 2

    succeeded_rows = [r for r in rows if r["status"] == "succeeded"]
    failed_rows = [r for r in rows if r["status"] == "failed"]
    assert len(succeeded_rows) == 1
    assert succeeded_rows[0]["generated_text"] == "caption A"
    assert len(failed_rows) == 1
    assert failed_rows[0]["error"] == "timeout"


def test_export_csv_is_empty_when_no_results(tmp_path: Path, monkeypatch) -> None:
    """export_job_results_csv for a job with no results should produce header-only CSV."""
    db_path = tmp_path / "app_state.db"
    monkeypatch.setattr(
        "backend.services.batch_service.get_settings",
        lambda: type("S", (), {"state_dir": tmp_path})(),
    )

    job_id = str(uuid.uuid4())
    job = _make_job(job_id, str(tmp_path / "project.db"), status="queued")
    _write_job_to_db(db_path, job)

    from backend.services.batch_service import BatchService as _BS  # noqa: PLC0415
    service = BatchService.__new__(BatchService)
    service._jobs = {}
    service._lock = __import__("threading").Lock()
    service._db_path = lambda: db_path
    service._connect = _make_connect(db_path)
    _BS._ensure_schema(service)
    _BS._load_jobs(service)

    csv_text = _BS.export_job_results_csv(service, job_id=job_id)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows == [], f"Expected no data rows, got {rows}"
