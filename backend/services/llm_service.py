from __future__ import annotations

import re

from backend.db.models import ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.llm.base import (
    BackendInfo,
    format_reasoning_output,
    normalize_reasoning_mode,
    normalize_reasoning_visibility,
)
from backend.llm.lmstudio_client import LMStudioClient
from backend.llm.ollama_client import OllamaClient
from backend.llm.prompt_builder import build_caption_prompt
from backend.llm.tool_loop import generate_with_tools
from backend.services.llm_generation_pipeline import run_generation_with_context_retries
from backend.services.project_db_utils import (
    load_project_record as load_project_record_from_session,
    require_existing_project_path,
)
from backend.services.tool_service import fetch_file_as_context, fetch_url_as_context
from backend.services.note_context_service import build_notes_context_parts
from backend.services.app_state_service import (
    create_global_preset,
    get_global_settings,
    delete_global_preset,
    get_global_preset,
    list_global_presets,
    update_global_preset,
)
from backend.services.caption_service import create_caption_candidate
from backend.services.image_service import get_image_content, get_image_detail
from backend.services.rag_service import rag_service


_CONTEXT_RETRY_CHAR_BUDGETS: tuple[int | None, ...] = (None, 12_000, 8_000, 5_000, 3_000)


def _finalize_generation_text(*, answer_text: str, reasoning_text: str, reasoning_visibility: str) -> str:
    return format_reasoning_output(
        answer=(answer_text or ""),
        reasoning=(reasoning_text or ""),
        visibility=normalize_reasoning_visibility(reasoning_visibility),
    )


def _lookup_model_info(*, backend: str, model_name: str):
    for backend_info in list_backends():
        if backend_info.name != backend:
            continue
        for model in backend_info.models or []:
            if model.name == model_name:
                return model
    return None


def list_backends() -> list[BackendInfo]:
    settings = get_global_settings()
    ollama_base_url = str(settings.get("ollama_base_url") or "http://127.0.0.1:11434")
    lmstudio_base_url = str(settings.get("lmstudio_base_url") or "http://127.0.0.1:1234")
    return [
        OllamaClient(base_url=ollama_base_url).get_backend_info(),
        LMStudioClient(base_url=lmstudio_base_url).get_backend_info(),
    ]


def _normalize_backend_name(name: str) -> str:
    normalized = name.strip().lower()
    if normalized not in {"ollama", "lmstudio"}:
        raise ValueError(f"Unsupported backend: {name}")
    return normalized


def _load_project_record(project_path: str) -> tuple[ProjectRecord, object]:
    resolved_path = require_existing_project_path(project_path)

    session_factory = create_sqlite_session_factory(resolved_path)
    with session_factory() as session:
        project = load_project_record_from_session(session, resolved_path)
        return project, resolved_path


def list_presets() -> list[dict[str, object]]:
    return list_global_presets()


def create_preset(
    *,
    name: str,
    backend: str,
    model_name: str,
    caption_mode_strategy: str,
    system_prompt: str,
    tool_web_search: bool,
    tool_web_fetch: bool,
    context_url_template: str,
    context_file_template: str,
    include_project_notes: bool = False,
    include_global_notes: bool = False,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    normalized_backend = _normalize_backend_name(backend)
    return create_global_preset(
        name=name,
        backend=normalized_backend,
        model_name=model_name,
        caption_mode_strategy=caption_mode_strategy,
        system_prompt=system_prompt,
        tool_web_search=tool_web_search,
        tool_web_fetch=tool_web_fetch,
        context_url_template=context_url_template,
        context_file_template=context_file_template,
        include_project_notes=include_project_notes,
        include_global_notes=include_global_notes,
        reasoning_mode=reasoning_mode,
        reasoning_visibility=reasoning_visibility,
    )


def update_preset(
    *,
    preset_id: int,
    name: str,
    backend: str,
    model_name: str,
    caption_mode_strategy: str,
    system_prompt: str,
    tool_web_search: bool,
    tool_web_fetch: bool,
    context_url_template: str,
    context_file_template: str,
    include_project_notes: bool = False,
    include_global_notes: bool = False,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    normalized_backend = _normalize_backend_name(backend)
    return update_global_preset(
        preset_id=preset_id,
        name=name,
        backend=normalized_backend,
        model_name=model_name,
        caption_mode_strategy=caption_mode_strategy,
        system_prompt=system_prompt,
        tool_web_search=tool_web_search,
        tool_web_fetch=tool_web_fetch,
        context_url_template=context_url_template,
        context_file_template=context_file_template,
        include_project_notes=include_project_notes,
        include_global_notes=include_global_notes,
        reasoning_mode=reasoning_mode,
        reasoning_visibility=reasoning_visibility,
    )


def delete_preset(*, preset_id: int) -> dict[str, int]:
    return delete_global_preset(preset_id=preset_id)


def _render_template_value(template: str, context: dict[str, object]) -> str:
    template = template or ""
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
        "project_context_url": project.context_url,
        "project_context_file_path": project.context_file_path,
        "filename": image_detail.filename,
        "active_caption": active_caption.text if active_caption else "",
    }

    ordered = sorted(captions, key=lambda item: item.created_at)
    for index, caption in enumerate(ordered, start=1):
        context[f"caption_{index}"] = caption.text

    return context


def _collect_injected_context_parts(*, context_urls: list[str], context_files: list[str]) -> tuple[list[str], list[str]]:
    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    for url in context_urls:
        result = fetch_url_as_context(url)
        tool_usage_log.append(result.display_summary)
        if result.content:
            injected_parts.append(f"--- Context from {url} ---\n{result.content}")

    for file_path in context_files:
        result = fetch_file_as_context(file_path)
        tool_usage_log.append(result.display_summary)
        if result.content:
            injected_parts.append(f"--- Context from file: {file_path} ---\n{result.content}")

    return injected_parts, tool_usage_log


def _resolve_model_tools(*, backend: str, model_name: str, requested_tools: list[str], tool_usage_log: list[str]) -> list[str]:
    tools_enabled = list(requested_tools)
    if not requested_tools:
        return tools_enabled

    selected_model_info = _lookup_model_info(backend=backend, model_name=model_name)
    if selected_model_info is not None and not selected_model_info.tool_capable:
        tool_usage_log.append(f"model {model_name!r} is not tool-capable; using context injection only")
        return []
    return tools_enabled


def _validate_generation_inputs(*, model: str, timeout_seconds: int, prompt: str | None = None) -> str:
    selected_model = model.strip()
    if not selected_model:
        raise ValueError("Model is required.")
    if prompt is not None and not prompt.strip():
        raise ValueError("Prompt is required.")
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")
    return selected_model


def _resolve_backend_runtime(*, selected_backend: str, timeout_seconds: int) -> tuple[str, int, int | None]:
    settings = get_global_settings()
    ollama_base_url = str(settings.get("ollama_base_url") or "http://127.0.0.1:11434")
    lmstudio_base_url = str(settings.get("lmstudio_base_url") or "http://127.0.0.1:1234")
    base_url = ollama_base_url if selected_backend == "ollama" else lmstudio_base_url

    backend_timeout_key = "ollama_timeout_seconds" if selected_backend == "ollama" else "lmstudio_timeout_seconds"
    backend_timeout = settings.get(backend_timeout_key)
    effective_timeout = int(backend_timeout) if isinstance(backend_timeout, int) else int(timeout_seconds)

    backend_num_ctx_key = "ollama_num_ctx" if selected_backend == "ollama" else "lmstudio_num_ctx"
    backend_num_ctx = settings.get(backend_num_ctx_key)
    effective_num_ctx = int(backend_num_ctx) if isinstance(backend_num_ctx, int) else None
    return base_url, effective_timeout, effective_num_ctx


def _render_template_list(items: list[str], template_context: dict[str, object]) -> list[str]:
    rendered: list[str] = []
    for item in items:
        value = _render_template_value(item, template_context).strip()
        if value:
            rendered.append(value)
    return rendered


def _collect_optional_note_context(
    *,
    project_path: str | None,
    include_project_notes: bool,
    project_note_ids: list[int] | None,
    include_global_notes: bool,
    global_note_ids: list[int] | None,
    require_project_path_for_project_notes: bool,
) -> tuple[list[str], list[str]]:
    uses_project_notes = include_project_notes or bool(project_note_ids)
    uses_any_notes = uses_project_notes or include_global_notes or bool(global_note_ids)
    if not uses_any_notes:
        return [], []

    normalized_path = (project_path or "").strip() or None
    if require_project_path_for_project_notes and uses_project_notes and not normalized_path:
        raise ValueError("project_path is required when including project notes context.")

    return build_notes_context_parts(
        project_path=normalized_path,
        include_project_notes=include_project_notes,
        project_note_ids=project_note_ids or [],
        include_global_notes=include_global_notes,
        global_note_ids=global_note_ids or [],
    )


def _generate_with_optional_tools(
    *,
    backend: str,
    model_name: str,
    prompt: str,
    image_bytes: bytes | None,
    media_type: str,
    system_prompt: str,
    tools_enabled: list[str],
    base_url: str,
    timeout_seconds: int,
    effective_num_ctx: int | None,
    reasoning_mode: str,
) -> tuple[str, str, str, list[str]]:
    if tools_enabled:
        answer_text, reasoning_text, loop_log = generate_with_tools(
            base_url=base_url,
            model=model_name,
            prompt=prompt,
            image_bytes=image_bytes,
            image_media_type=media_type,
            system_prompt=system_prompt,
            tools_enabled=tools_enabled,
            context_urls=[],
            context_files=[],
            timeout_seconds=timeout_seconds,
            num_ctx=effective_num_ctx if backend == "ollama" else None,
            reasoning_mode=reasoning_mode,
        )
        return answer_text, reasoning_text, "tool_calls", loop_log

    if backend == "ollama":
        generated_result = OllamaClient(base_url=base_url).generate_caption_result(
            model=model_name,
            prompt=prompt,
            image_bytes=image_bytes,
            system_prompt=system_prompt,
            timeout_seconds=timeout_seconds,
            num_ctx=effective_num_ctx,
            reasoning_mode=reasoning_mode,
        )
        return generated_result.text, generated_result.reasoning, "context_injection", []

    generated_result = LMStudioClient(base_url=base_url).generate_caption_result(
        model=model_name,
        prompt=prompt,
        image_bytes=image_bytes,
        system_prompt=system_prompt,
        media_type=media_type,
        timeout_seconds=timeout_seconds,
        reasoning_mode=reasoning_mode,
    )
    return generated_result.text, generated_result.reasoning, "context_injection", []


def _build_requested_tools(*, tool_web_search: bool, tool_web_fetch: bool) -> list[str]:
    tools: list[str] = []
    if tool_web_search:
        tools.append("web_search")
    if tool_web_fetch:
        tools.append("web_fetch")
    return tools


def _resolve_preset_generation_config(
    *,
    preset: dict[str, object],
    preset_id: int,
    timeout_seconds: int,
) -> dict[str, object]:
    preset_backend = str(preset.get("backend") or "")
    preset_model_name = str(preset.get("model_name") or "")
    if not preset_model_name:
        raise ValueError(f"Preset has no model configured: {preset_id}")

    backend = _normalize_backend_name(preset_backend)
    validated_model_name = _validate_generation_inputs(model=preset_model_name, timeout_seconds=timeout_seconds)
    base_url, effective_timeout, effective_num_ctx = _resolve_backend_runtime(
        selected_backend=backend,
        timeout_seconds=timeout_seconds,
    )

    return {
        "backend": backend,
        "model_name": validated_model_name,
        "name": str(preset.get("name") or f"Preset {preset_id}"),
        "caption_mode_strategy": str(preset.get("caption_mode_strategy") or "auto").strip().lower(),
        "system_template": str(preset.get("system_prompt") or ""),
        "context_url_template": str(preset.get("context_url_template") or ""),
        "context_file_template": str(preset.get("context_file_template") or ""),
        "tool_web_search": bool(preset.get("tool_web_search") is True),
        "tool_web_fetch": bool(preset.get("tool_web_fetch") is True),
        "include_project_notes": bool(preset.get("include_project_notes") is True),
        "include_global_notes": bool(preset.get("include_global_notes") is True),
        "reasoning_mode": normalize_reasoning_mode(str(preset.get("reasoning_mode") or "off")),
        "reasoning_visibility": normalize_reasoning_visibility(str(preset.get("reasoning_visibility") or "hidden")),
        "base_url": base_url,
        "effective_timeout": effective_timeout,
        "effective_num_ctx": effective_num_ctx,
    }


def _compose_preset_system_prompt(
    *,
    system_template: str,
    context: dict[str, object],
    preset_prompt_suffix: str,
    project_path: str,
    active_caption_text: str,
) -> str:
    system_prompt = _render_template_value(system_template, context)
    extra_suffix = str(preset_prompt_suffix or "").strip()
    if extra_suffix:
        system_prompt = f"{system_prompt.rstrip()}\n\n{extra_suffix}" if system_prompt.strip() else extra_suffix

    if rag_service.is_enabled():
        system_prompt = rag_service.build_augmented_system_prompt(
            base_system_prompt=system_prompt,
            project_path=project_path,
            current_caption=active_caption_text,
            include_few_shot=True,
        )

    return system_prompt


def generate_caption_for_image(
    *,
    project_path: str,
    image_id: int,
    backend: str,
    model: str,
    extra_instructions: str = "",
    make_active: bool = True,
    timeout_seconds: int = 120,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    generated = generate_text_for_image_manual(
        project_path=project_path,
        image_id=image_id,
        backend=backend,
        model=model,
        extra_instructions=extra_instructions,
        timeout_seconds=timeout_seconds,
        reasoning_mode=reasoning_mode,
        reasoning_visibility=reasoning_visibility,
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
        "reasoning_mode": str(generated.get("reasoning_mode") or "off"),
        "reasoning_visibility": str(generated.get("reasoning_visibility") or "hidden"),
        "reasoning_text": str(generated.get("reasoning_text") or ""),
        "answer_text": str(generated.get("answer_text") or ""),
    }


def generate_text_for_image_manual(
    *,
    project_path: str,
    image_id: int,
    backend: str,
    model: str,
    extra_instructions: str = "",
    timeout_seconds: int = 120,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = model.strip()
    if not selected_model:
        raise ValueError("Model is required.")
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")

    normalized_reasoning_mode = normalize_reasoning_mode(reasoning_mode)
    normalized_reasoning_visibility = normalize_reasoning_visibility(reasoning_visibility)

    settings = get_global_settings()
    ollama_base_url = str(settings.get("ollama_base_url") or "http://127.0.0.1:11434")
    lmstudio_base_url = str(settings.get("lmstudio_base_url") or "http://127.0.0.1:1234")
    backend_timeout_key = "ollama_timeout_seconds" if selected_backend == "ollama" else "lmstudio_timeout_seconds"
    backend_timeout = settings.get(backend_timeout_key)
    effective_timeout = int(backend_timeout) if isinstance(backend_timeout, int) else int(timeout_seconds)

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    active_caption = next((caption for caption in image_detail.captions if caption.is_active), None)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)
    project, _ = _load_project_record(project_path)

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description="",
        current_caption=active_caption.text if active_caption else "",
        extra_instructions=extra_instructions,
    )

    if selected_backend == "ollama":
        generated_result = OllamaClient(base_url=ollama_base_url).generate_caption_result(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            timeout_seconds=effective_timeout,
            reasoning_mode=normalized_reasoning_mode,
        )
    else:
        generated_result = LMStudioClient(base_url=lmstudio_base_url).generate_caption_result(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            media_type=media_type,
            timeout_seconds=effective_timeout,
            reasoning_mode=normalized_reasoning_mode,
        )
    generated_text = _finalize_generation_text(
        answer_text=generated_result.text,
        reasoning_text=generated_result.reasoning,
        reasoning_visibility=normalized_reasoning_visibility,
    )
    return {
        "text": generated_text,
        "answer_text": generated_result.text,
        "reasoning_text": generated_result.reasoning,
        "reasoning_mode": normalized_reasoning_mode,
        "reasoning_visibility": normalized_reasoning_visibility,
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
        "reasoning_mode": str(generated.get("reasoning_mode") or "off"),
        "reasoning_visibility": str(generated.get("reasoning_visibility") or "hidden"),
        "reasoning_text": str(generated.get("reasoning_text") or ""),
        "answer_text": str(generated.get("answer_text") or ""),
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
    preset_prompt_suffix: str = "",
    timeout_seconds: int = 120,
) -> dict[str, object]:
    _validate_generation_inputs(model="configured-by-preset", timeout_seconds=timeout_seconds)

    project, _ = _load_project_record(project_path)
    preset = get_global_preset(preset_id=preset_id)
    preset_config = _resolve_preset_generation_config(
        preset=preset,
        preset_id=preset_id,
        timeout_seconds=timeout_seconds,
    )

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)
    active_caption = next((caption for caption in image_detail.captions if caption.is_active), None)
    active_caption_text = active_caption.text if active_caption else ""

    preset_caption_mode_strategy = str(preset_config["caption_mode_strategy"])
    effective_caption_mode = project.caption_mode if preset_caption_mode_strategy == "auto" else preset_caption_mode_strategy

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description=project.description,
        current_caption=active_caption_text,
        caption_mode=effective_caption_mode,
        extra_instructions="",
    )

    context = _build_preset_context(project=project, image_detail=image_detail)
    system_prompt = _compose_preset_system_prompt(
        system_template=str(preset_config["system_template"]),
        context=context,
        preset_prompt_suffix=preset_prompt_suffix,
        project_path=project_path,
        active_caption_text=active_caption_text,
    )
    rendered_context_url = _render_template_value(str(preset_config["context_url_template"]), context).strip()
    rendered_context_file = _render_template_value(str(preset_config["context_file_template"]), context).strip()

    backend = str(preset_config["backend"])
    preset_model_name = str(preset_config["model_name"])
    preset_name = str(preset_config["name"])
    preset_reasoning_mode = str(preset_config["reasoning_mode"])
    preset_reasoning_visibility = str(preset_config["reasoning_visibility"])
    base_url = str(preset_config["base_url"])
    effective_timeout = int(preset_config["effective_timeout"])
    effective_num_ctx = preset_config["effective_num_ctx"]
    tools_enabled = _build_requested_tools(
        tool_web_search=bool(preset_config["tool_web_search"]),
        tool_web_fetch=bool(preset_config["tool_web_fetch"]),
    )

    context_urls = [rendered_context_url] if rendered_context_url else []
    context_files = [rendered_context_file] if rendered_context_file else []

    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    note_parts, note_log = _collect_optional_note_context(
        project_path=project_path,
        include_project_notes=bool(preset_config["include_project_notes"]),
        project_note_ids=None,
        include_global_notes=bool(preset_config["include_global_notes"]),
        global_note_ids=None,
        require_project_path_for_project_notes=True,
    )
    injected_parts.extend(note_parts)
    tool_usage_log.extend(note_log)

    context_parts, context_log = _collect_injected_context_parts(
        context_urls=context_urls,
        context_files=context_files,
    )
    injected_parts.extend(context_parts)
    tool_usage_log.extend(context_log)

    tools_enabled = _resolve_model_tools(
        backend=backend,
        model_name=preset_model_name,
        requested_tools=tools_enabled,
        tool_usage_log=tool_usage_log,
    )

    def _generate_with_injected_prompt(injected_prompt: str) -> tuple[str, str, str, list[str]]:
        effective_system_prompt = system_prompt.strip()
        if effective_system_prompt and injected_prompt:
            effective_system_prompt = f"{effective_system_prompt}\n\n{injected_prompt}"
        elif injected_prompt:
            effective_system_prompt = injected_prompt
        return _generate_with_optional_tools(
            backend=backend,
            model_name=preset_model_name,
            prompt=prompt,
            image_bytes=image_bytes,
            media_type=media_type,
            system_prompt=effective_system_prompt,
            tools_enabled=tools_enabled,
            base_url=base_url,
            timeout_seconds=effective_timeout,
            effective_num_ctx=effective_num_ctx,
            reasoning_mode=preset_reasoning_mode,
        )

    generated_answer_text, generated_reasoning_text, generation_mode = run_generation_with_context_retries(
        injected_parts=injected_parts,
        context_retry_char_budgets=_CONTEXT_RETRY_CHAR_BUDGETS,
        tool_usage_log=tool_usage_log,
        generate_once=_generate_with_injected_prompt,
    )

    generated_text = _finalize_generation_text(
        answer_text=generated_answer_text,
        reasoning_text=generated_reasoning_text,
        reasoning_visibility=preset_reasoning_visibility,
    )

    return {
        "text": generated_text,
        "answer_text": generated_answer_text,
        "reasoning_text": generated_reasoning_text,
        "reasoning_mode": preset_reasoning_mode,
        "reasoning_visibility": preset_reasoning_visibility,
        "backend": backend,
        "model": preset_model_name,
        "preset": {
            "id": preset_id,
            "name": preset_name,
            "caption_mode_strategy": preset_caption_mode_strategy,
            "effective_caption_mode": effective_caption_mode,
            "generation_mode": generation_mode,
            "tool_usage_log": tool_usage_log,
        },
    }


def generate_caption_with_tools(
    *,
    project_path: str,
    image_id: int,
    backend: str,
    model: str,
    extra_instructions: str = "",
    make_active: bool = True,
    timeout_seconds: int = 120,
    tools_enabled: list[str] | None = None,
    context_urls: list[str] | None = None,
    context_files: list[str] | None = None,
    include_project_notes: bool = False,
    project_note_ids: list[int] | None = None,
    include_global_notes: bool = False,
    global_note_ids: list[int] | None = None,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = _validate_generation_inputs(model=model, timeout_seconds=timeout_seconds)

    normalized_reasoning_mode = normalize_reasoning_mode(reasoning_mode)
    normalized_reasoning_visibility = normalize_reasoning_visibility(reasoning_visibility)

    requested_tools = [t for t in (tools_enabled or []) if t]
    tools_enabled = list(requested_tools)
    context_urls = [u for u in (context_urls or []) if u]
    context_files = [f for f in (context_files or []) if f]

    base_url, effective_timeout, effective_num_ctx = _resolve_backend_runtime(
        selected_backend=selected_backend,
        timeout_seconds=timeout_seconds,
    )

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    project, _ = _load_project_record(project_path)
    active_caption = next((c for c in image_detail.captions if c.is_active), None)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)

    template_context = _build_preset_context(project=project, image_detail=image_detail)
    context_urls = _render_template_list(context_urls, template_context)
    context_files = _render_template_list(context_files, template_context)

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description="",
        current_caption=active_caption.text if active_caption else "",
        extra_instructions=extra_instructions,
    )

    # Pre-fetch context URLs and files. This always uses native urllib so it
    # works regardless of whether the model supports /v1/chat/completions.
    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    note_parts, note_log = _collect_optional_note_context(
        project_path=project_path,
        include_project_notes=include_project_notes,
        project_note_ids=project_note_ids,
        include_global_notes=include_global_notes,
        global_note_ids=global_note_ids,
        require_project_path_for_project_notes=True,
    )
    injected_parts.extend(note_parts)
    tool_usage_log.extend(note_log)

    context_parts, context_log = _collect_injected_context_parts(
        context_urls=context_urls,
        context_files=context_files,
    )
    injected_parts.extend(context_parts)
    tool_usage_log.extend(context_log)

    generation_mode = "context_injection"
    tools_enabled = _resolve_model_tools(
        backend=selected_backend,
        model_name=selected_model,
        requested_tools=requested_tools,
        tool_usage_log=tool_usage_log,
    )

    def _generate_with_injected_prompt(system_prompt: str) -> tuple[str, str, str, list[str]]:
        return _generate_with_optional_tools(
            backend=selected_backend,
            model_name=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            media_type=media_type,
            system_prompt=system_prompt,
            tools_enabled=tools_enabled,
            base_url=base_url,
            timeout_seconds=effective_timeout,
            effective_num_ctx=effective_num_ctx,
            reasoning_mode=normalized_reasoning_mode,
        )

    generated_answer_text, generated_reasoning_text, generation_mode = run_generation_with_context_retries(
        injected_parts=injected_parts,
        context_retry_char_budgets=_CONTEXT_RETRY_CHAR_BUDGETS,
        tool_usage_log=tool_usage_log,
        generate_once=_generate_with_injected_prompt,
    )

    generated_text = _finalize_generation_text(
        answer_text=generated_answer_text,
        reasoning_text=generated_reasoning_text,
        reasoning_visibility=normalized_reasoning_visibility,
    )

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
        "reasoning_mode": normalized_reasoning_mode,
        "reasoning_visibility": normalized_reasoning_visibility,
        "reasoning_text": generated_reasoning_text,
        "answer_text": generated_answer_text,
        "tool_usage_log": tool_usage_log,
        "generation_mode": generation_mode,
    }


def generate_note_text_with_tools(
    *,
    backend: str,
    model: str,
    prompt: str,
    project_path: str | None = None,
    image_id: int | None = None,
    timeout_seconds: int = 120,
    tools_enabled: list[str] | None = None,
    context_urls: list[str] | None = None,
    context_files: list[str] | None = None,
    include_project_notes: bool = False,
    project_note_ids: list[int] | None = None,
    include_global_notes: bool = False,
    global_note_ids: list[int] | None = None,
    reasoning_mode: str = "off",
    reasoning_visibility: str = "hidden",
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = _validate_generation_inputs(model=model, timeout_seconds=timeout_seconds, prompt=prompt)
    prompt_text = prompt.strip()

    normalized_reasoning_mode = normalize_reasoning_mode(reasoning_mode)
    normalized_reasoning_visibility = normalize_reasoning_visibility(reasoning_visibility)

    normalized_project_path = (project_path or "").strip() or None
    if image_id is not None and not normalized_project_path:
        raise ValueError("project_path is required when image_id is provided.")

    requested_tools = [t for t in (tools_enabled or []) if t]
    tools_enabled = list(requested_tools)
    context_urls = [u for u in (context_urls or []) if u]
    context_files = [f for f in (context_files or []) if f]

    base_url, effective_timeout, effective_num_ctx = _resolve_backend_runtime(
        selected_backend=selected_backend,
        timeout_seconds=timeout_seconds,
    )

    image_bytes: bytes | None = None
    media_type = "image/png"
    if image_id is not None and normalized_project_path:
        image_bytes, media_type = get_image_content(project_path=normalized_project_path, image_id=image_id)

    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    note_parts, note_log = _collect_optional_note_context(
        project_path=normalized_project_path,
        include_project_notes=include_project_notes,
        project_note_ids=project_note_ids,
        include_global_notes=include_global_notes,
        global_note_ids=global_note_ids,
        require_project_path_for_project_notes=True,
    )
    injected_parts.extend(note_parts)
    tool_usage_log.extend(note_log)

    context_parts, context_log = _collect_injected_context_parts(
        context_urls=context_urls,
        context_files=context_files,
    )
    injected_parts.extend(context_parts)
    tool_usage_log.extend(context_log)

    generation_mode = "context_injection"

    tools_enabled = _resolve_model_tools(
        backend=selected_backend,
        model_name=selected_model,
        requested_tools=requested_tools,
        tool_usage_log=tool_usage_log,
    )

    def _generate_with_injected_prompt(system_prompt: str) -> tuple[str, str, str, list[str]]:
        return _generate_with_optional_tools(
            backend=selected_backend,
            model_name=selected_model,
            prompt=prompt_text,
            image_bytes=image_bytes,
            media_type=media_type,
            system_prompt=system_prompt,
            tools_enabled=tools_enabled,
            base_url=base_url,
            timeout_seconds=effective_timeout,
            effective_num_ctx=effective_num_ctx,
            reasoning_mode=normalized_reasoning_mode,
        )

    generated_answer_text, generated_reasoning_text, generation_mode = run_generation_with_context_retries(
        injected_parts=injected_parts,
        context_retry_char_budgets=_CONTEXT_RETRY_CHAR_BUDGETS,
        tool_usage_log=tool_usage_log,
        generate_once=_generate_with_injected_prompt,
    )

    generated_text = _finalize_generation_text(
        answer_text=generated_answer_text,
        reasoning_text=generated_reasoning_text,
        reasoning_visibility=normalized_reasoning_visibility,
    )

    return {
        "text": generated_text,
        "answer_text": generated_answer_text,
        "reasoning_text": generated_reasoning_text,
        "reasoning_mode": normalized_reasoning_mode,
        "reasoning_visibility": normalized_reasoning_visibility,
        "backend": selected_backend,
        "model": selected_model,
        "tool_usage_log": tool_usage_log,
        "generation_mode": generation_mode,
    }
