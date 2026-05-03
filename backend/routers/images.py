from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.services.image_service import (
    crop_image,
    delete_image,
    duplicate_image,
    extract_region_image,
    flip_image,
    get_image_content,
    get_image_detail,
    list_project_images,
    rotate_image,
    restore_image,
    scale_image,
    update_image_included,
)
from backend.services.import_service import project_image_summary

router = APIRouter(prefix="/api/images", tags=["images"])


class UpdateIncludedRequest(BaseModel):
    project_path: str = Field(min_length=1)
    included: bool


class DuplicateImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    include_captions: bool = True
    copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")


class DeleteImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    mode: str = Field(default="soft", pattern="^(soft|hard)$")
    confirm_hard_delete: bool = False


class RestoreImageRequest(BaseModel):
    project_path: str = Field(min_length=1)


class CropRect(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class CropImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    rect: CropRect
    output_name: str | None = None
    include_captions: bool = True
    caption_copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")


class ScaleImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    mode: str = Field(default="percent", pattern="^(percent|dimensions)$")
    percent: float | None = Field(default=None, gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    keep_aspect_ratio: bool = True
    upscale: bool = False
    output_name: str | None = None
    include_captions: bool = True
    caption_copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")


class FlipImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    mode: str = Field(pattern="^(horizontal|vertical|both)$")
    output_name: str | None = None
    include_captions: bool = True
    caption_copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")


class RotateImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    angle: int = Field(description="Rotation angle in degrees; supported values: 90, 180, 270")
    output_name: str | None = None
    include_captions: bool = True
    caption_copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")


class ExtractRegionImageRequest(BaseModel):
    project_path: str = Field(min_length=1)
    rect: CropRect
    output_name: str | None = None
    include_captions: bool = True
    caption_copy_mode: str = Field(default="all_candidates", pattern="^(active_only|all_candidates|none)$")
    add_source_reference_note: bool = True


@router.get("/summary")
def image_summary(project_path: str = Query(..., min_length=1)) -> dict[str, object]:
    try:
        return project_image_summary(project_path=project_path)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/list")
def list_images(project_path: str = Query(..., min_length=1)) -> dict[str, list[dict[str, object]]]:
    try:
        items = list_project_images(project_path=project_path)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"images": [item.__dict__ for item in items]}


@router.get("/{image_id}")
def image_detail(image_id: int, project_path: str = Query(..., min_length=1)) -> dict[str, object]:
    try:
        detail = get_image_detail(project_path=project_path, image_id=image_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "image": {
            "id": detail.id,
            "filename": detail.filename,
            "width": detail.width,
            "height": detail.height,
            "included": detail.included,
            "source_image_id": detail.source_image_id,
            "derived_operation": detail.derived_operation,
            "derived_operation_params": detail.derived_operation_params,
            "captions": [candidate.__dict__ for candidate in detail.captions],
        }
    }


@router.get("/{image_id}/content")
def image_content(image_id: int, project_path: str = Query(..., min_length=1)) -> Response:
    try:
        content, media_type = get_image_content(project_path=project_path, image_id=image_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(content=content, media_type=media_type)


@router.post("/{image_id}/included")
def set_included(image_id: int, request: UpdateIncludedRequest) -> dict[str, object]:
    try:
        result = update_image_included(project_path=request.project_path.strip(), image_id=image_id, included=request.included)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/duplicate")
def duplicate_image_route(image_id: int, request: DuplicateImageRequest) -> dict[str, object]:
    try:
        result = duplicate_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            include_captions=request.include_captions,
            copy_mode=request.copy_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/delete")
def delete_image_route(image_id: int, request: DeleteImageRequest) -> dict[str, object]:
    try:
        result = delete_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            mode=request.mode,
            confirm_hard_delete=request.confirm_hard_delete,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/restore")
def restore_image_route(image_id: int, request: RestoreImageRequest) -> dict[str, object]:
    try:
        result = restore_image(project_path=request.project_path.strip(), image_id=image_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/crop")
def crop_image_route(image_id: int, request: CropImageRequest) -> dict[str, object]:
    try:
        result = crop_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            x=request.rect.x,
            y=request.rect.y,
            width=request.rect.width,
            height=request.rect.height,
            output_name=request.output_name,
            include_captions=request.include_captions,
            caption_copy_mode=request.caption_copy_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/scale")
def scale_image_route(image_id: int, request: ScaleImageRequest) -> dict[str, object]:
    try:
        result = scale_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            mode=request.mode,
            percent=request.percent,
            width=request.width,
            height=request.height,
            keep_aspect_ratio=request.keep_aspect_ratio,
            upscale=request.upscale,
            output_name=request.output_name,
            include_captions=request.include_captions,
            caption_copy_mode=request.caption_copy_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/flip")
def flip_image_route(image_id: int, request: FlipImageRequest) -> dict[str, object]:
    try:
        result = flip_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            mode=request.mode,
            output_name=request.output_name,
            include_captions=request.include_captions,
            caption_copy_mode=request.caption_copy_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/rotate")
def rotate_image_route(image_id: int, request: RotateImageRequest) -> dict[str, object]:
    try:
        result = rotate_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            angle=request.angle,
            output_name=request.output_name,
            include_captions=request.include_captions,
            caption_copy_mode=request.caption_copy_mode,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result


@router.post("/{image_id}/extract-region")
def extract_region_image_route(image_id: int, request: ExtractRegionImageRequest) -> dict[str, object]:
    try:
        result = extract_region_image(
            project_path=request.project_path.strip(),
            image_id=image_id,
            x=request.rect.x,
            y=request.rect.y,
            width=request.rect.width,
            height=request.rect.height,
            output_name=request.output_name,
            include_captions=request.include_captions,
            caption_copy_mode=request.caption_copy_mode,
            add_source_reference_note=request.add_source_reference_note,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result
