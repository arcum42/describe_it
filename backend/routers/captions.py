from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.caption_service import create_caption_candidate, set_active_caption, update_active_caption_text

router = APIRouter(prefix="/api/captions", tags=["captions"])


class UpdateActiveCaptionRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    text: str


class CreateCaptionCandidateRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    text: str
    make_active: bool = True


class SetActiveCaptionRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    caption_id: int


@router.post("/update-active")
def update_active_caption(request: UpdateActiveCaptionRequest) -> dict[str, object]:
    try:
        result = update_active_caption_text(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            text=request.text,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"caption": result}


@router.post("/create")
def create_caption(request: CreateCaptionCandidateRequest) -> dict[str, object]:
    try:
        result = create_caption_candidate(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            text=request.text,
            make_active=request.make_active,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"caption": result}


@router.post("/set-active")
def set_active(request: SetActiveCaptionRequest) -> dict[str, int]:
    try:
        return set_active_caption(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            caption_id=request.caption_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
