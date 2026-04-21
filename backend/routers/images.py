from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.services.image_service import get_image_content, get_image_detail, list_project_images, update_image_included
from backend.services.import_service import project_image_summary

router = APIRouter(prefix="/api/images", tags=["images"])


class UpdateIncludedRequest(BaseModel):
    project_path: str = Field(min_length=1)
    included: bool


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
