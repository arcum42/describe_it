"""Settings router for managing application settings including imageboard credentials."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.imageboard_credentials_service import get_imageboard_credentials_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ImageboardCredentialRequest(BaseModel):
    """Request body for updating imageboard credentials."""

    board_id: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    username: str | None = Field(default=None)


@router.get("/imageboard-boards")
async def get_imageboard_boards() -> dict:
    """Get list of available imageboard sources with metadata."""
    service = get_imageboard_credentials_service()
    boards = service.get_available_boards()
    return {"boards": boards}


@router.get("/imageboard-credentials")
async def get_imageboard_credentials() -> dict:
    """Get masked summary of all stored imageboard credentials."""
    service = get_imageboard_credentials_service()
    credentials = service.get_all_credentials_summary()
    return {"credentials": credentials}


@router.post("/imageboard-credentials/update")
async def update_imageboard_credentials(req: ImageboardCredentialRequest) -> dict:
    """Save or update credentials for an imageboard."""
    service = get_imageboard_credentials_service()
    try:
        result = service.save_credentials(req.board_id, req.api_key, req.username)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/imageboard-credentials/{board_id}")
async def delete_imageboard_credentials(board_id: str) -> dict:
    """Remove credentials for an imageboard."""
    service = get_imageboard_credentials_service()
    try:
        result = service.delete_credentials(board_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
