from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.app_state_service import get_global_settings, update_global_settings
from backend.services.llm_service import (
    create_preset,
    delete_preset,
    generate_caption_for_image,
    generate_caption_with_preset,
    list_backends,
    list_presets,
    update_preset,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])


class GenerateCaptionRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    backend: str = Field(min_length=1)
    model: str = Field(min_length=1)
    extra_instructions: str = ""
    make_active: bool = True
    timeout_seconds: int = Field(default=120, ge=10, le=900)


class CreatePresetRequest(BaseModel):
    name: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    system_prompt: str = ""


class UpdatePresetRequest(CreatePresetRequest):
    preset_id: int


class DeletePresetRequest(BaseModel):
    preset_id: int


class UpdateSettingsRequest(BaseModel):
    llm_timeout_seconds: int = Field(ge=10, le=900)
    llm_use_preset_by_default: bool = False
    llm_default_preset_id: int | None = Field(default=None, ge=1)


class GenerateWithPresetRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    preset_id: int
    make_active: bool = True
    timeout_seconds: int = Field(default=120, ge=10, le=900)


@router.get("/backends")
def available_backends() -> dict[str, list[dict[str, object]]]:
    backends = list_backends()
    return {
        "backends": [
            {
                "name": backend.name,
                "available": backend.available,
                "models": backend.models or [],
                "error": backend.error,
            }
            for backend in backends
        ]
    }


@router.post("/generate-caption")
def generate_caption(request: GenerateCaptionRequest) -> dict[str, object]:
    try:
        return generate_caption_for_image(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            backend=request.backend.strip(),
            model=request.model.strip(),
            extra_instructions=request.extra_instructions,
            make_active=request.make_active,
            timeout_seconds=request.timeout_seconds,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/settings")
def get_settings() -> dict[str, object]:
    return get_global_settings()


@router.post("/settings")
def update_settings(request: UpdateSettingsRequest) -> dict[str, object]:
    return update_global_settings(
        llm_timeout_seconds=request.llm_timeout_seconds,
        llm_use_preset_by_default=request.llm_use_preset_by_default,
        llm_default_preset_id=request.llm_default_preset_id,
    )


@router.get("/presets")
def get_presets() -> dict[str, list[dict[str, object]]]:
    try:
        return {"presets": list_presets()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/presets/create")
def create_preset_route(request: CreatePresetRequest) -> dict[str, object]:
    try:
        preset = create_preset(
            name=request.name,
            backend=request.backend,
            model_name=request.model_name,
            system_prompt=request.system_prompt,
        )
        return {"preset": preset}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/presets/update")
def update_preset_route(request: UpdatePresetRequest) -> dict[str, object]:
    try:
        preset = update_preset(
            preset_id=request.preset_id,
            name=request.name,
            backend=request.backend,
            model_name=request.model_name,
            system_prompt=request.system_prompt,
        )
        return {"preset": preset}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/presets/delete")
def delete_preset_route(request: DeletePresetRequest) -> dict[str, int]:
    try:
        return delete_preset(preset_id=request.preset_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/generate-with-preset")
def generate_with_preset(request: GenerateWithPresetRequest) -> dict[str, object]:
    try:
        return generate_caption_with_preset(
            project_path=request.project_path.strip(),
            image_id=request.image_id,
            preset_id=request.preset_id,
            make_active=request.make_active,
            timeout_seconds=request.timeout_seconds,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
