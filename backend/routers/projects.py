from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.app_state_service import get_project_session_state, update_project_session_state
from backend.services.export_service import export_project_dataset, preview_project_export
from backend.services.import_service import import_folder_into_project
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
    context_url: str = ""
    context_file_path: str = ""


class ImportFolderRequest(BaseModel):
    project_path: str = Field(min_length=1)
    source_folder: str = Field(min_length=1)
    replace_existing: bool = False


class UpdateSessionStateRequest(BaseModel):
    last_project_path: str = ""
    last_project_directory: str = ""
    reopen_last_project: bool = True


class ExportProjectRequest(BaseModel):
    project_path: str = Field(min_length=1)
    output_folder: str = Field(min_length=1)
    included_only: bool = True
    apply_trigger_word: bool = False
    include_metadata: bool = False
    overwrite_existing: bool = False
    clean_output_folder: bool = False
    create_new_folder: bool = False
    new_folder_name: str = ""
    include_project_notes: bool = True


class ExportPreviewRequest(BaseModel):
    project_path: str = Field(min_length=1)
    output_folder: str = Field(min_length=1)
    included_only: bool = True
    apply_trigger_word: bool = False
    create_new_folder: bool = False
    new_folder_name: str = ""


@router.get("/recent")
def recent_projects() -> dict[str, list[dict[str, str]]]:
    return {"projects": [entry.__dict__ for entry in list_recent_projects()]}


@router.get("/session-state")
def get_session_state() -> dict[str, object]:
    return get_project_session_state()


@router.post("/session-state")
def update_session_state(request: UpdateSessionStateRequest) -> dict[str, object]:
    return update_project_session_state(
        last_project_path=request.last_project_path,
        last_project_directory=request.last_project_directory,
        reopen_last_project=request.reopen_last_project,
    )


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
            context_url=request.context_url.strip(),
            context_file_path=request.context_file_path.strip(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project.__dict__}


@router.post("/import-folder")
def import_folder_route(request: ImportFolderRequest) -> dict[str, object]:
    try:
        result = import_folder_into_project(
            project_path=request.project_path.strip(),
            source_folder=request.source_folder.strip(),
            replace_existing=request.replace_existing,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"result": result.__dict__}


@router.post("/export")
def export_project_route(request: ExportProjectRequest) -> dict[str, object]:
    try:
        result = export_project_dataset(
            project_path=request.project_path.strip(),
            output_folder=request.output_folder.strip(),
            included_only=request.included_only,
            apply_trigger_word=request.apply_trigger_word,
            include_metadata=request.include_metadata,
            overwrite_existing=request.overwrite_existing,
            clean_output_folder=request.clean_output_folder,
            create_new_folder=request.create_new_folder,
            new_folder_name=request.new_folder_name,
            include_project_notes=request.include_project_notes,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"result": result.__dict__}


@router.post("/export-preview")
def export_project_preview_route(request: ExportPreviewRequest) -> dict[str, object]:
    try:
        result = preview_project_export(
            project_path=request.project_path.strip(),
            output_folder=request.output_folder.strip(),
            included_only=request.included_only,
            apply_trigger_word=request.apply_trigger_word,
            create_new_folder=request.create_new_folder,
            new_folder_name=request.new_folder_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"result": result.__dict__}
