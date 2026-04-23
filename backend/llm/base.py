from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelInfo:
    name: str
    vision_capable: bool = False
    tool_capable: bool = False
    capabilities: list[str] | None = None


@dataclass
class BackendInfo:
    name: str
    available: bool = False
    models: list[ModelInfo] | None = None
    error: str | None = None
