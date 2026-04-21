from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackendInfo:
    name: str
    available: bool = False
