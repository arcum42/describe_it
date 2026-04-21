from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/recent")
def list_recent_projects() -> dict[str, list[dict[str, str]]]:
    return {"projects": []}
