from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/captions", tags=["captions"])


@router.get("/summary")
def caption_summary() -> dict[str, int]:
    return {"count": 0}
