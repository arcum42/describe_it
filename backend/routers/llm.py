from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/backends")
def available_backends() -> dict[str, list[dict[str, object]]]:
    return {
        "backends": [
            {"name": "ollama", "available": False},
            {"name": "lmstudio", "available": False},
        ]
    }
