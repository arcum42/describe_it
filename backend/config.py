from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    host: str
    port: int
    base_dir: Path
    state_dir: Path
    recent_projects_path: Path


def get_settings() -> Settings:
    base_dir = Path(__file__).resolve().parent.parent
    state_dir = base_dir / ".describe_it"
    return Settings(
        app_name="describe_it",
        host=os.getenv("DESCRIBE_IT_HOST", "127.0.0.1"),
        port=int(os.getenv("DESCRIBE_IT_PORT", "7860")),
        base_dir=base_dir,
        state_dir=state_dir,
        recent_projects_path=state_dir / "recent_projects.json",
    )
