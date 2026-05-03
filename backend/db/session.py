from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.base import Base


def _ensure_project_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                format TEXT NOT NULL DEFAULT 'markdown',
                tags TEXT NOT NULL DEFAULT '',
                is_archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS caption_batch_previews (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                request_json TEXT NOT NULL,
                changes_json TEXT NOT NULL,
                impacted_captions_count INTEGER NOT NULL DEFAULT 0,
                impacted_images_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                applied_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS caption_batch_operations (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                preview_id TEXT,
                action TEXT NOT NULL,
                request_json TEXT NOT NULL,
                before_snapshot_json TEXT NOT NULL,
                after_snapshot_json TEXT NOT NULL,
                updated_captions_count INTEGER NOT NULL DEFAULT 0,
                updated_images_count INTEGER NOT NULL DEFAULT 0,
                can_undo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                undone_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(preview_id) REFERENCES caption_batch_previews(id)
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(projects)").fetchall()
        }
        if not columns:
            return
        if "context_url" not in columns:
            connection.execute(
                "ALTER TABLE projects ADD COLUMN context_url TEXT NOT NULL DEFAULT ''"
            )
        if "context_file_path" not in columns:
            connection.execute(
                "ALTER TABLE projects ADD COLUMN context_file_path TEXT NOT NULL DEFAULT ''"
            )

        image_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(images)").fetchall()
        }
        if image_columns:
            if "source_image_id" not in image_columns:
                connection.execute("ALTER TABLE images ADD COLUMN source_image_id INTEGER")
            if "derived_operation" not in image_columns:
                connection.execute("ALTER TABLE images ADD COLUMN derived_operation TEXT")
            if "derived_operation_params" not in image_columns:
                connection.execute("ALTER TABLE images ADD COLUMN derived_operation_params TEXT")
            if "deleted_at" not in image_columns:
                connection.execute("ALTER TABLE images ADD COLUMN deleted_at DATETIME")
        connection.commit()
    finally:
        connection.close()


def build_database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path}"


def create_sqlite_session_factory(database_path: Path) -> sessionmaker:
    _ensure_project_schema(database_path)
    engine = create_engine(build_database_url(database_path), future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_database(database_path: Path) -> None:
    engine = create_engine(build_database_url(database_path), future=True)
    Base.metadata.create_all(engine)
    _ensure_project_schema(database_path)
