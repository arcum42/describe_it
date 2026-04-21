from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        app_name="describe_it",
        host=os.getenv("DESCRIBE_IT_HOST", "127.0.0.1"),
        port=int(os.getenv("DESCRIBE_IT_PORT", "7860")),
    )
