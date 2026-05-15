from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.caption_batch_service import (
    BatchOperationAlreadyUndoneError,
    BatchOperationNotFoundError,
    BatchPreviewExpiredError,
    BatchPreviewNotFoundError,
    apply_batch_replace,
    list_batch_operations,
    preview_batch_replace,
    undo_batch_replace,
)
from backend.services.caption_text_edit_service import caption_text_edit_service
from backend.services.caption_service import (
    create_caption_candidate,
    delete_caption,
    set_active_caption,
    update_active_caption_text,
    update_caption_text,
)
from backend.services.tag_service import (
    TagService,
    get_tags_for_caption,
    update_tags_for_caption,
    batch_tag_operation,
    get_tag_statistics_for_project,
)

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


class UpdateCaptionRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    caption_id: int
    text: str


class DeleteCaptionRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    caption_id: int


class CaptionBatchQuery(BaseModel):
    find_text: str = Field(min_length=1)
    replace_text: str = ""
    mode: str = Field(default="plain", pattern="^(plain|regex)$")
    case_sensitive: bool = False


class CaptionBatchScope(BaseModel):
    caption_scope: str = Field(default="active_only", pattern="^(active_only|all_candidates)$")
    image_scope: str = Field(default="all", pattern="^(all|included_only|selected_ids)$")
    image_ids: list[int] | None = None


class CaptionBatchPreviewRequest(BaseModel):
    project_path: str = Field(min_length=1)
    query: CaptionBatchQuery
    scope: CaptionBatchScope


class CaptionBatchApplyRequest(BaseModel):
    project_path: str = Field(min_length=1)
    preview_id: str = Field(min_length=1)
    confirm: bool = False
    create_undo_snapshot: bool = True


class CaptionBatchUndoRequest(BaseModel):
    project_path: str = Field(min_length=1)
    operation_id: str | None = None


class TagUpdateRequest(BaseModel):
    project_path: str = Field(min_length=1)
    caption_id: int
    tags: list[str]


class TagBatchOperationRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_ids: list[int] = Field(min_length=1)
    operation: str = Field(pattern="^(add|remove|clear|reorder)$")
    tags: list[str] | None = None
    tag_order: list[str] | None = None


class TagStatisticsRequest(BaseModel):
    project_path: str = Field(min_length=1)


class StartDeleteEmptyCaptionsJobRequest(BaseModel):
    project_path: str = Field(min_length=1)


class StartRemoveTagsJobRequest(BaseModel):
    project_path: str = Field(min_length=1)
    patterns: list[str] = Field(min_length=1)


class StartAddCommonCaptionJobRequest(BaseModel):
    project_path: str = Field(min_length=1)
    caption_text: str = Field(min_length=1)
    scope: str = Field(default="without_caption", pattern="^(all_images|without_caption)$")


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


@router.post("/update")
def update_caption(request: UpdateCaptionRequest) -> dict[str, object]:
    try:
        result = update_caption_text(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            caption_id=request.caption_id,
            text=request.text,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"caption": result}


@router.post("/delete")
def delete_caption_route(request: DeleteCaptionRequest) -> dict[str, object]:
    try:
        return delete_caption(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            caption_id=request.caption_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/batch/preview-replace")
def preview_replace(request: CaptionBatchPreviewRequest) -> dict[str, object]:
    try:
        return preview_batch_replace(
            project_path=request.project_path.strip(),
            query=request.query.model_dump(),
            scope=request.scope.model_dump(),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/batch/apply-replace")
def apply_replace(request: CaptionBatchApplyRequest) -> dict[str, object]:
    try:
        return apply_batch_replace(
            project_path=request.project_path.strip(),
            preview_id=request.preview_id.strip(),
            confirm=request.confirm,
            create_undo_snapshot=request.create_undo_snapshot,
        )
    except BatchPreviewNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except BatchPreviewExpiredError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/batch/undo")
def undo_replace(request: CaptionBatchUndoRequest) -> dict[str, object]:
    try:
        return undo_batch_replace(
            project_path=request.project_path.strip(),
            operation_id=request.operation_id.strip() if request.operation_id else None,
        )
    except BatchOperationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except BatchOperationAlreadyUndoneError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/batch/operations")
def get_batch_operations(project_path: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200)) -> dict[str, object]:
    try:
        operations = list_batch_operations(
            project_path=project_path.strip(),
            limit=limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"operations": operations}


# Tag management endpoints for tag-mode datasets

@router.get("/tags/statistics")
def get_tag_stats(project_path: str = Query(..., min_length=1)) -> dict[str, object]:
    """Get tag usage statistics for a project (top 50 tags, frequency distribution)."""
    try:
        return get_tag_statistics_for_project(project_path.strip())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/tags/{caption_id}")
def get_tags(project_path: str = Query(..., min_length=1), caption_id: int = 0) -> dict[str, object]:
    """Get parsed tags from a specific caption with categorization info."""
    try:
        return get_tags_for_caption(project_path.strip(), caption_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/tags/update")
def update_tags(request: TagUpdateRequest) -> dict[str, object]:
    """Update tags for a specific caption."""
    try:
        return update_tags_for_caption(request.project_path.strip(), request.caption_id, request.tags)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/tags/batch-operation")
def batch_tag_ops(request: TagBatchOperationRequest) -> dict[str, object]:
    """
    Perform batch tag operations on multiple images' active captions.
    Operations: add, remove, clear, reorder
    """
    try:
        return batch_tag_operation(
            project_path=request.project_path.strip(),
            image_ids=request.image_ids,
            operation=request.operation,
            tags=request.tags,
            tag_order=request.tag_order,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/text-edit-jobs/delete-empty/start")
def start_delete_empty_captions_job(request: StartDeleteEmptyCaptionsJobRequest) -> dict[str, object]:
    try:
        job = caption_text_edit_service.start_delete_empty_captions(project_path=request.project_path.strip())
        return {"job": job}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/text-edit-jobs/remove-tags/start")
def start_remove_tags_job(request: StartRemoveTagsJobRequest) -> dict[str, object]:
    try:
        job = caption_text_edit_service.start_remove_tags(
            project_path=request.project_path.strip(),
            patterns=request.patterns,
        )
        return {"job": job}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/text-edit-jobs/add-common/start")
def start_add_common_caption_job(request: StartAddCommonCaptionJobRequest) -> dict[str, object]:
    try:
        job = caption_text_edit_service.start_add_common_caption(
            project_path=request.project_path.strip(),
            caption_text=request.caption_text,
            scope=request.scope,
        )
        return {"job": job}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/text-edit-jobs/{job_id}")
def get_text_edit_job(job_id: str) -> dict[str, object]:
    try:
        return {"job": caption_text_edit_service.get_job(job_id=job_id.strip())}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


