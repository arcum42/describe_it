from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectSummary:
    name: str
    path: str
