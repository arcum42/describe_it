from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.note_service import create_note, delete_note, list_notes, update_note

router = APIRouter(prefix="/api/notes", tags=["notes"])


class CreateNoteRequest(BaseModel):
    project_path: str = Field(min_length=1)
    title: str = ""
    content: str = ""
    format: str = Field(default="markdown", pattern="^(text|markdown)$")
    tags: str = ""


class UpdateNoteRequest(BaseModel):
    project_path: str = Field(min_length=1)
    note_id: int
    title: str = ""
    content: str = ""
    format: str = Field(default="markdown", pattern="^(text|markdown)$")
    tags: str = ""
    is_archived: bool = False


class DeleteNoteRequest(BaseModel):
    project_path: str = Field(min_length=1)
    note_id: int


@router.get("")
def list_notes_route(
    project_path: str = Query(..., min_length=1),
    include_archived: bool = Query(default=True),
) -> dict[str, list[dict[str, object]]]:
    try:
        notes = list_notes(project_path=project_path.strip(), include_archived=include_archived)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"notes": [note.__dict__ for note in notes]}


@router.post("/create")
def create_note_route(request: CreateNoteRequest) -> dict[str, object]:
    try:
        note = create_note(
            project_path=request.project_path.strip(),
            title=request.title,
            content=request.content,
            format=request.format,
            tags=request.tags,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"note": note.__dict__}


@router.post("/update")
def update_note_route(request: UpdateNoteRequest) -> dict[str, object]:
    try:
        note = update_note(
            project_path=request.project_path.strip(),
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
def delete_note_route(request: DeleteNoteRequest) -> dict[str, int]:
    try:
        return delete_note(project_path=request.project_path.strip(), note_id=request.note_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
