from __future__ import annotations

import re

from sqlalchemy import select

from backend.db.models import ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.llm.base import BackendInfo
from backend.llm.lmstudio_client import LMStudioClient
from backend.llm.ollama_client import OllamaClient
from backend.llm.prompt_builder import build_caption_prompt
from backend.services.app_state_service import (
    create_global_preset,
    delete_global_preset,
    get_global_preset,
    list_global_presets,
    update_global_preset,
)
from backend.services.caption_service import create_caption_candidate
from backend.services.image_service import get_image_content, get_image_detail


def list_backends() -> list[BackendInfo]:
    return [
        OllamaClient().get_backend_info(),
        LMStudioClient().get_backend_info(),
    ]


def _normalize_backend_name(name: str) -> str:
    normalized = name.strip().lower()
    if normalized not in {"ollama", "lmstudio"}:
        raise ValueError(f"Unsupported backend: {name}")
    return normalized


def _resolve_project_path(raw_path: str):
    from pathlib import Path
    from backend.config import get_settings

    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = get_settings().base_dir / candidate
    return candidate.resolve()


def _load_project_record(project_path: str) -> tuple[ProjectRecord, object]:
    resolved_path = _resolve_project_path(project_path)
    if not resolved_path.exists():
        raise ValueError(f"Project file does not exist: {resolved_path}")

    session_factory = create_sqlite_session_factory(resolved_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        if project is None:
            raise ValueError(f"Project database has no project metadata: {resolved_path}")
        return project, resolved_path


def list_presets() -> list[dict[str, object]]:
    return list_global_presets()


def create_preset(*, name: str, backend: str, model_name: str, system_prompt: str) -> dict[str, object]:
    normalized_backend = _normalize_backend_name(backend)
    return create_global_preset(
        name=name,
        backend=normalized_backend,
        model_name=model_name,
        system_prompt=system_prompt,
    )


def update_preset(*, preset_id: int, name: str, backend: str, model_name: str, system_prompt: str) -> dict[str, object]:
    normalized_backend = _normalize_backend_name(backend)
    return update_global_preset(
        preset_id=preset_id,
        name=name,
        backend=normalized_backend,
        model_name=model_name,
        system_prompt=system_prompt,
    )


def delete_preset(*, preset_id: int) -> dict[str, int]:
    return delete_global_preset(preset_id=preset_id)


def _render_system_prompt(template: str, context: dict[str, object]) -> str:
    if not template.strip():
        return ""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key)
        return "" if value is None else str(value)

    return re.sub(r"\{([a-zA-Z0-9_]+)\}", replace, template)


def _build_preset_context(*, project: ProjectRecord, image_detail) -> dict[str, object]:
    captions = image_detail.captions or []
    active_caption = next((caption for caption in captions if caption.is_active), None)

    context: dict[str, object] = {
        "project_name": project.name,
        "project_description": project.description,
        "project_trigger_word": project.trigger_word,
        "project_caption_mode": project.caption_mode,
        "filename": image_detail.filename,
        "active_caption": active_caption.text if active_caption else "",
    }

    ordered = sorted(captions, key=lambda item: item.created_at)
    for index, caption in enumerate(ordered, start=1):
        context[f"caption_{index}"] = caption.text

    return context


def generate_caption_for_image(
    *,
    project_path: str,
    image_id: int,
    backend: str,
    model: str,
    extra_instructions: str = "",
    make_active: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, object]:
    generated = generate_text_for_image_manual(
        project_path=project_path,
        image_id=image_id,
        backend=backend,
        model=model,
        extra_instructions=extra_instructions,
        timeout_seconds=timeout_seconds,
    )

    selected_backend = str(generated.get("backend") or "")
    selected_model = str(generated.get("model") or "")
    generated_text = str(generated.get("text") or "")
    source = f"llm:{selected_backend}:{selected_model}"
    caption = create_caption_candidate(
        project_path=project_path,
        image_id=image_id,
        text=generated_text,
        make_active=make_active,
        source=source,
    )
    return {
        "caption": caption,
        "backend": selected_backend,
        "model": selected_model,
    }


def generate_text_for_image_manual(
    *,
    project_path: str,
    image_id: int,
    backend: str,
    model: str,
    extra_instructions: str = "",
    timeout_seconds: int = 120,
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = model.strip()
    if not selected_model:
        raise ValueError("Model is required.")
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    active_caption = next((caption for caption in image_detail.captions if caption.is_active), None)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description="",
        current_caption=active_caption.text if active_caption else "",
        extra_instructions=extra_instructions,
    )

    if selected_backend == "ollama":
        generated_text = OllamaClient().generate_caption(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            timeout_seconds=timeout_seconds,
        )
    else:
        generated_text = LMStudioClient().generate_caption(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            media_type=media_type,
            timeout_seconds=timeout_seconds,
        )
    return {
        "text": generated_text,
        "backend": selected_backend,
        "model": selected_model,
    }


def generate_caption_with_preset(
    *,
    project_path: str,
    image_id: int,
    preset_id: int,
    make_active: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, object]:
    generated = generate_text_for_image_with_preset(
        project_path=project_path,
        image_id=image_id,
        preset_id=preset_id,
        timeout_seconds=timeout_seconds,
    )

    backend = str(generated.get("backend") or "")
    preset_model_name = str(generated.get("model") or "")
    preset_name = str(generated.get("preset", {}).get("name") or f"Preset {preset_id}")
    generated_text = str(generated.get("text") or "")
    source = f"llm:preset:{preset_id}:{backend}:{preset_model_name}"
    caption = create_caption_candidate(
        project_path=project_path,
        image_id=image_id,
        text=generated_text,
        make_active=make_active,
        source=source,
    )
    return {
        "caption": caption,
        "backend": backend,
        "model": preset_model_name,
        "preset": {
            "id": preset_id,
            "name": preset_name,
        },
    }


def generate_text_for_image_with_preset(
    *,
    project_path: str,
    image_id: int,
    preset_id: int,
    timeout_seconds: int = 120,
) -> dict[str, object]:
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")

    project, resolved_path = _load_project_record(project_path)
    session_factory = create_sqlite_session_factory(resolved_path)
    preset = get_global_preset(preset_id=preset_id)
    system_template = str(preset.get("system_prompt") or "")

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)
    active_caption = next((caption for caption in image_detail.captions if caption.is_active), None)

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description=project.description,
        current_caption=active_caption.text if active_caption else "",
        caption_mode=project.caption_mode,
        extra_instructions="",
    )

    context = _build_preset_context(project=project, image_detail=image_detail)
    system_prompt = _render_system_prompt(system_template, context)
    preset_backend = str(preset.get("backend") or "")
    preset_model_name = str(preset.get("model_name") or "")
    preset_name = str(preset.get("name") or f"Preset {preset_id}")
    backend = _normalize_backend_name(preset_backend)
    if not preset_model_name:
        raise ValueError(f"Preset has no model configured: {preset_id}")

    if backend == "ollama":
        generated_text = OllamaClient().generate_caption(
            model=preset_model_name,
            prompt=prompt,
            image_bytes=image_bytes,
            system_prompt=system_prompt,
            timeout_seconds=timeout_seconds,
        )
    else:
        generated_text = LMStudioClient().generate_caption(
            model=preset_model_name,
            prompt=prompt,
            image_bytes=image_bytes,
            system_prompt=system_prompt,
            media_type=media_type,
            timeout_seconds=timeout_seconds,
        )
    return {
        "text": generated_text,
        "backend": backend,
        "model": preset_model_name,
        "preset": {
            "id": preset_id,
            "name": preset_name,
        },
    }
