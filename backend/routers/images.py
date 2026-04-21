from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/summary")
def image_summary() -> dict[str, int]:
    return {"count": 0}
