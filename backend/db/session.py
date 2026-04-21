from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def build_database_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path}"


def create_sqlite_session_factory(database_path: Path) -> sessionmaker:
    engine = create_engine(build_database_url(database_path), future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
