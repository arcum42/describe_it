from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.project_service import browse_project_paths, create_project, list_recent_projects, open_project, update_project_metadata

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    path: str = Field(min_length=1)
    description: str = ""


class OpenProjectRequest(BaseModel):
    path: str = Field(min_length=1)


class UpdateProjectRequest(BaseModel):
    path: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    trigger_word: str = ""
    caption_mode: str = Field(pattern="^(description|tags)$")


@router.get("/recent")
def recent_projects() -> dict[str, list[dict[str, str]]]:
    return {"projects": [entry.__dict__ for entry in list_recent_projects()]}


@router.get("/browser")
def browse_projects(path: str | None = Query(default=None)) -> dict[str, object]:
    try:
        listing = browse_project_paths(path=path)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "current_path": listing.current_path,
        "parent_path": listing.parent_path,
        "directories": [entry.__dict__ for entry in listing.directories],
        "db_files": [entry.__dict__ for entry in listing.db_files],
        "roots": listing.roots,
    }


@router.post("/create")
def create_project_route(request: CreateProjectRequest) -> dict[str, dict[str, str]]:
    try:
        project = create_project(name=request.name.strip(), path=request.path.strip(), description=request.description.strip())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project.__dict__}


@router.post("/open")
def open_project_route(request: OpenProjectRequest) -> dict[str, dict[str, str]]:
    try:
        project = open_project(path=request.path.strip())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project.__dict__}


@router.post("/update")
def update_project_route(request: UpdateProjectRequest) -> dict[str, dict[str, str]]:
    try:
        project = update_project_metadata(
            path=request.path.strip(),
            name=request.name.strip(),
            description=request.description.strip(),
            trigger_word=request.trigger_word.strip(),
            caption_mode=request.caption_mode.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project.__dict__}
