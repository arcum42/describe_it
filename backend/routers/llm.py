from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.services.batch_service import batch_service
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
from backend.services.rag_service import rag_service
from backend.db.session import create_sqlite_session_factory
from backend.db.models import CaptionRecord
from sqlalchemy import select

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
    caption_mode_strategy: str = Field(default="auto", pattern="^(auto|description|tags)$")
    system_prompt: str = ""


class UpdatePresetRequest(CreatePresetRequest):
    preset_id: int


class DeletePresetRequest(BaseModel):
    preset_id: int


class UpdateSettingsRequest(BaseModel):
    llm_timeout_seconds: int = Field(ge=10, le=900)
    llm_use_preset_by_default: bool = False
    llm_default_preset_id: int | None = Field(default=None, ge=1)
    ui_show_debug_section: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    lmstudio_base_url: str = "http://127.0.0.1:1234"
    ollama_timeout_seconds: int | None = Field(default=None, ge=10, le=900)
    lmstudio_timeout_seconds: int | None = Field(default=None, ge=10, le=900)


class GenerateWithPresetRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    preset_id: int
    make_active: bool = True
    timeout_seconds: int = Field(default=120, ge=10, le=900)


class CreateBatchJobRequest(BaseModel):
    project_path: str = Field(min_length=1)
    target: str = Field(default="included", pattern="^(included|uncaptioned|all)$")
    use_preset: bool = True
    preset_id: int | None = Field(default=None, ge=1)
    backend: str = ""
    model: str = ""
    extra_instructions: str = ""
    timeout_seconds: int = Field(default=120, ge=10, le=900)
    make_active: bool = True
    output_mode: str = Field(default="new_candidate", pattern="^(new_candidate|replace_active|append_active)$")
    skip_on_failure: bool = True
    retry_count: int = Field(default=0, ge=0, le=5)


class BatchJobCommandRequest(BaseModel):
    job_id: str = Field(min_length=1)


class TestConnectionRequest(BaseModel):
    backend: str = Field(pattern="^(ollama|lmstudio)$")
    url: str = Field(min_length=1, max_length=2048)


class RebuildEmbeddingsRequest(BaseModel):
    project_path: str = Field(min_length=1)


class SearchCaptionsRequest(BaseModel):
    project_path: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


@router.post("/test-connection")
def test_connection(request: TestConnectionRequest) -> dict[str, object]:
    from backend.llm.ollama_client import OllamaClient
    from backend.llm.lmstudio_client import LMStudioClient

    url = request.url.strip()
    try:
        if request.backend == "ollama":
            info = OllamaClient(base_url=url).get_backend_info()
        else:
            info = LMStudioClient(base_url=url).get_backend_info()
        if not info.available:
            return {"ok": False, "message": info.error or "Backend unreachable.", "model_count": 0}
        model_count = len(info.models or [])
        return {"ok": True, "message": f"Connected \u2014 {model_count} model(s) found.", "model_count": model_count}
    except ValueError as error:
        return {"ok": False, "message": str(error), "model_count": 0}


@router.get("/backends")
def available_backends() -> dict[str, list[dict[str, object]]]:
    backends = list_backends()
    return {
        "backends": [
            {
                "name": backend.name,
                "available": backend.available,
                "models": [
                    {
                        "name": model.name,
                        "vision_capable": model.vision_capable,
                        "tool_capable": model.tool_capable,
                        "capabilities": model.capabilities or [],
                    }
                    for model in (backend.models or [])
                ],
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
        ui_show_debug_section=request.ui_show_debug_section,
        ollama_base_url=request.ollama_base_url,
        lmstudio_base_url=request.lmstudio_base_url,
        ollama_timeout_seconds=request.ollama_timeout_seconds,
        lmstudio_timeout_seconds=request.lmstudio_timeout_seconds,
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
            caption_mode_strategy=request.caption_mode_strategy,
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
            caption_mode_strategy=request.caption_mode_strategy,
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


@router.get("/batch-jobs")
def list_batch_jobs(project_path: str) -> dict[str, list[dict[str, object]]]:
    try:
        jobs = batch_service.list_jobs_for_project(project_path=project_path.strip())
        return {"jobs": jobs}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/batch-jobs/{job_id}")
def get_batch_job(job_id: str) -> dict[str, object]:
    try:
        return {"job": batch_service.get_job(job_id=job_id)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/batch-jobs/create")
def create_batch_job(request: CreateBatchJobRequest) -> dict[str, object]:
    try:
        job = batch_service.create_job(
            project_path=request.project_path.strip(),
            target=request.target,
            use_preset=request.use_preset,
            preset_id=request.preset_id,
            backend=request.backend,
            model=request.model,
            extra_instructions=request.extra_instructions,
            timeout_seconds=request.timeout_seconds,
            make_active=request.make_active,
            output_mode=request.output_mode,
            skip_on_failure=request.skip_on_failure,
            retry_count=request.retry_count,
        )
        return {"job": job}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/batch-jobs/pause")
def pause_batch_job(request: BatchJobCommandRequest) -> dict[str, object]:
    try:
        return {"job": batch_service.pause_job(job_id=request.job_id.strip())}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/batch-jobs/resume")
def resume_batch_job(request: BatchJobCommandRequest) -> dict[str, object]:
    try:
        return {"job": batch_service.resume_job(job_id=request.job_id.strip())}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/batch-jobs/cancel")
def cancel_batch_job(request: BatchJobCommandRequest) -> dict[str, object]:
    try:
        return {"job": batch_service.cancel_job(job_id=request.job_id.strip())}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/batch-jobs/{job_id}/results")
def batch_job_results(job_id: str, limit: int = 500) -> dict[str, object]:
    try:
        return {"results": batch_service.get_job_results(job_id=job_id, limit=limit)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/batch-jobs/{job_id}/results/export")
def batch_job_results_export(job_id: str) -> Response:
    try:
        csv_text = batch_service.export_job_results_csv(job_id=job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="batch-job-{job_id}-results.csv"'},
    )


@router.get("/rag/status")
def rag_status() -> dict[str, object]:
    return {"rag_enabled": rag_service.is_enabled()}


@router.post("/rag/rebuild-embeddings")
def rebuild_embeddings(request: RebuildEmbeddingsRequest) -> dict[str, object]:
    try:
        project_path = request.project_path.strip()
        session_factory = create_sqlite_session_factory(__import__("pathlib").Path(project_path))
        with session_factory() as session:
            captions_rows = session.scalars(
                select(CaptionRecord).order_by(CaptionRecord.id.asc())
            ).all()
        captions = [{"id": c.id, "text": c.text} for c in captions_rows]
        return {"result": rag_service.rebuild_embeddings_for_project(project_path=project_path, captions=captions)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/rag/search")
def search_captions(request: SearchCaptionsRequest) -> dict[str, object]:
    try:
        similar = rag_service.get_similar_captions(
            project_path=request.project_path.strip(),
            query_text=request.query_text.strip(),
            top_k=request.top_k,
        )
        return {"similar_captions": similar, "rag_enabled": rag_service.is_enabled()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
