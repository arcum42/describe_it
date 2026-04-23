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
