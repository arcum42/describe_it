from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.global_note_service import (
    create_global_note,
    delete_global_note,
    list_global_notes,
    update_global_note,
)

router = APIRouter(prefix="/api/global-notes", tags=["global-notes"])


class CreateGlobalNoteRequest(BaseModel):
    title: str = ""
    content: str = ""
    format: str = Field(default="markdown", pattern="^(text|markdown)$")
    tags: str = ""


class UpdateGlobalNoteRequest(BaseModel):
    note_id: int
    title: str = ""
    content: str = ""
    format: str = Field(default="markdown", pattern="^(text|markdown)$")
    tags: str = ""
    is_archived: bool = False


class DeleteGlobalNoteRequest(BaseModel):
    note_id: int


@router.get("")
def list_global_notes_route(include_archived: bool = Query(default=True)) -> dict[str, list[dict[str, object]]]:
    try:
        notes = list_global_notes(include_archived=include_archived)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"notes": [note.__dict__ for note in notes]}


@router.post("/create")
def create_global_note_route(request: CreateGlobalNoteRequest) -> dict[str, object]:
    try:
        note = create_global_note(
            title=request.title,
            content=request.content,
            format=request.format,
            tags=request.tags,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"note": note.__dict__}


@router.post("/update")
def update_global_note_route(request: UpdateGlobalNoteRequest) -> dict[str, object]:
    try:
        note = update_global_note(
            note_id=request.note_id,
            title=request.title,
            content=request.content,
            format=request.format,
            tags=request.tags,
            is_archived=request.is_archived,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"note": note.__dict__}


@router.post("/delete")
def delete_global_note_route(request: DeleteGlobalNoteRequest) -> dict[str, int]:
    try:
        return delete_global_note(note_id=request.note_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
