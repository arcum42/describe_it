from __future__ import annotations

import re

from sqlalchemy import select

from backend.db.models import ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.llm.base import BackendInfo
from backend.llm.lmstudio_client import LMStudioClient
from backend.llm.ollama_client import OllamaClient
from backend.llm.prompt_builder import build_caption_prompt
from backend.llm.tool_loop import generate_with_tools
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


def _lookup_model_info(*, backend: str, model_name: str):
    for backend_info in list_backends():
        if backend_info.name != backend:
            continue
        for model in backend_info.models or []:
            if model.name == model_name:
                return model
    return None


def _is_context_window_overflow_error(message: str) -> bool:
    lowered = message.lower()
    if "n_keep" in lowered and "n_ctx" in lowered:
        return True
    return "context length" in lowered or "maximum context length" in lowered


def _compose_injected_context_prompt(parts: list[str], *, max_chars: int | None) -> str:
    if not parts:
        return ""

    full = "\n\n".join(parts)
    if max_chars is None or len(full) <= max_chars:
        return full

    truncated = full[: max(0, max_chars - len("\n[truncated]"))].rstrip()
    if not truncated:
        return ""
    return f"{truncated}\n[truncated]"


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
        generated_text = OllamaClient(base_url=ollama_base_url).generate_caption(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            timeout_seconds=effective_timeout,
        )
    else:
        generated_text = LMStudioClient(base_url=lmstudio_base_url).generate_caption(
            model=selected_model,
            prompt=prompt,
            image_bytes=image_bytes,
            media_type=media_type,
            timeout_seconds=effective_timeout,
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

    project, _ = _load_project_record(project_path)
    preset = get_global_preset(preset_id=preset_id)
    system_template = str(preset.get("system_prompt") or "")
    context_url_template = str(preset.get("context_url_template") or "")
    context_file_template = str(preset.get("context_file_template") or "")
    preset_tool_web_search = bool(preset.get("tool_web_search") is True)
    preset_tool_web_fetch = bool(preset.get("tool_web_fetch") is True)

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)
    active_caption = next((caption for caption in image_detail.captions if caption.is_active), None)

    preset_caption_mode_strategy = str(preset.get("caption_mode_strategy") or "auto").strip().lower()
    effective_caption_mode = project.caption_mode if preset_caption_mode_strategy == "auto" else preset_caption_mode_strategy

    prompt = build_caption_prompt(
        filename=image_detail.filename,
        dataset_description=project.description,
        current_caption=active_caption.text if active_caption else "",
        caption_mode=effective_caption_mode,
        extra_instructions="",
    )

    context = _build_preset_context(project=project, image_detail=image_detail)
    system_prompt = _render_template_value(system_template, context)
    rendered_context_url = _render_template_value(context_url_template, context).strip()
    rendered_context_file = _render_template_value(context_file_template, context).strip()
    preset_include_project_notes = bool(preset.get("include_project_notes") is True)
    preset_include_global_notes = bool(preset.get("include_global_notes") is True)

    if rag_service.is_enabled():
        system_prompt = rag_service.build_augmented_system_prompt(
            base_system_prompt=system_prompt,
            project_path=project_path,
            current_caption=active_caption.text if active_caption else "",
            include_few_shot=True,
        )

    preset_backend = str(preset.get("backend") or "")
    preset_model_name = str(preset.get("model_name") or "")
    preset_name = str(preset.get("name") or f"Preset {preset_id}")
    backend = _normalize_backend_name(preset_backend)
    if not preset_model_name:
        raise ValueError(f"Preset has no model configured: {preset_id}")

    settings = get_global_settings()
    ollama_base_url = str(settings.get("ollama_base_url") or "http://127.0.0.1:11434")
    lmstudio_base_url = str(settings.get("lmstudio_base_url") or "http://127.0.0.1:1234")
    backend_timeout_key = "ollama_timeout_seconds" if backend == "ollama" else "lmstudio_timeout_seconds"
    backend_timeout = settings.get(backend_timeout_key)
    effective_timeout = int(backend_timeout) if isinstance(backend_timeout, int) else int(timeout_seconds)
    backend_num_ctx_key = "ollama_num_ctx" if backend == "ollama" else "lmstudio_num_ctx"
    backend_num_ctx = settings.get(backend_num_ctx_key)
    effective_num_ctx = int(backend_num_ctx) if isinstance(backend_num_ctx, int) else None

    base_url = ollama_base_url if backend == "ollama" else lmstudio_base_url
    tools_enabled: list[str] = []
    if preset_tool_web_search:
        tools_enabled.append("web_search")
    if preset_tool_web_fetch:
        tools_enabled.append("web_fetch")

    context_urls = [rendered_context_url] if rendered_context_url else []
    context_files = [rendered_context_file] if rendered_context_file else []

    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    # Notes context (prepended before URL/file context)
    if preset_include_project_notes or preset_include_global_notes:
        note_parts, note_log = build_notes_context_parts(
            project_path=project_path,
            include_project_notes=preset_include_project_notes,
            include_global_notes=preset_include_global_notes,
        )
        injected_parts.extend(note_parts)
        tool_usage_log.extend(note_log)

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

    selected_model_info = _lookup_model_info(backend=backend, model_name=preset_model_name)
    if tools_enabled and selected_model_info is not None and not selected_model_info.tool_capable:
        tools_enabled = []
        tool_usage_log.append(
            f"model {preset_model_name!r} is not tool-capable; using context injection only"
        )

    generated_text = ""
    generation_mode = "context_injection"
    last_error: ValueError | None = None

    for attempt_index, max_chars in enumerate(_CONTEXT_RETRY_CHAR_BUDGETS):
        injected_prompt = _compose_injected_context_prompt(injected_parts, max_chars=max_chars)
        effective_system_prompt = system_prompt.strip()
        if effective_system_prompt and injected_prompt:
            effective_system_prompt = f"{effective_system_prompt}\n\n{injected_prompt}"
        elif injected_prompt:
            effective_system_prompt = injected_prompt

        try:
            if tools_enabled:
                generation_mode = "tool_calls"
                generated_text, loop_log = generate_with_tools(
                    base_url=base_url,
                    model=preset_model_name,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    image_media_type=media_type,
                    system_prompt=effective_system_prompt,
                    tools_enabled=tools_enabled,
                    context_urls=[],
                    context_files=[],
                    timeout_seconds=effective_timeout,
                    num_ctx=effective_num_ctx if backend == "ollama" else None,
                )
                tool_usage_log.extend(loop_log)
            elif backend == "ollama":
                generation_mode = "context_injection"
                generated_text = OllamaClient(base_url=base_url).generate_caption(
                    model=preset_model_name,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    system_prompt=effective_system_prompt,
                    timeout_seconds=effective_timeout,
                    num_ctx=effective_num_ctx,
                )
            else:
                generation_mode = "context_injection"
                generated_text = LMStudioClient(base_url=base_url).generate_caption(
                    model=preset_model_name,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    system_prompt=effective_system_prompt,
                    media_type=media_type,
                    timeout_seconds=effective_timeout,
                )
            break
        except ValueError as error:
            last_error = error
            if not injected_parts or not _is_context_window_overflow_error(str(error)):
                raise
            next_budget = (
                _CONTEXT_RETRY_CHAR_BUDGETS[attempt_index + 1]
                if attempt_index + 1 < len(_CONTEXT_RETRY_CHAR_BUDGETS)
                else None
            )
            if next_budget is None:
                continue
            tool_usage_log.append(
                f"context window overflow detected; retrying with less injected context (next limit={next_budget})"
            )
            continue

    if not generated_text and last_error is not None:
        raise last_error

    return {
        "text": generated_text,
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
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = model.strip()
    if not selected_model:
        raise ValueError("Model is required.")
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")

    requested_tools = [t for t in (tools_enabled or []) if t]
    tools_enabled = list(requested_tools)
    context_urls = [u for u in (context_urls or []) if u]
    context_files = [f for f in (context_files or []) if f]

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

    image_detail = get_image_detail(project_path=project_path, image_id=image_id)
    project, _ = _load_project_record(project_path)
    active_caption = next((c for c in image_detail.captions if c.is_active), None)
    image_bytes, media_type = get_image_content(project_path=project_path, image_id=image_id)

    template_context = _build_preset_context(project=project, image_detail=image_detail)
    context_urls = [
        _render_template_value(url, template_context).strip()
        for url in context_urls
        if _render_template_value(url, template_context).strip()
    ]
    context_files = [
        _render_template_value(file_path, template_context).strip()
        for file_path in context_files
        if _render_template_value(file_path, template_context).strip()
    ]

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

    # Notes context (prepended before URL/file context)
    if include_project_notes or project_note_ids or include_global_notes or global_note_ids:
        note_parts, note_log = build_notes_context_parts(
            project_path=project_path,
            include_project_notes=include_project_notes,
            project_note_ids=project_note_ids or [],
            include_global_notes=include_global_notes,
            global_note_ids=global_note_ids or [],
        )
        injected_parts.extend(note_parts)
        tool_usage_log.extend(note_log)

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

    # If the selected model is known and not tool-capable, gracefully downgrade
    # to context-injection mode instead of forcing a /v1/chat/completions tool run.
    generation_mode = "context_injection"

    if requested_tools:
        selected_model_info = _lookup_model_info(backend=selected_backend, model_name=selected_model)
        if selected_model_info is not None and not selected_model_info.tool_capable:
            tools_enabled = []
            tool_usage_log.append(
                f"model {selected_model!r} is not tool-capable; using context injection only"
            )

    generated_text = ""
    last_error: ValueError | None = None

    for attempt_index, max_chars in enumerate(_CONTEXT_RETRY_CHAR_BUDGETS):
        system_prompt = _compose_injected_context_prompt(injected_parts, max_chars=max_chars)
        try:
            if tools_enabled:
                generation_mode = "tool_calls"
                # Actual tool calling requires /v1/chat/completions. The tool_loop
                # already has context_urls/files support, but we pass the pre-built
                # system_prompt and empty lists so it doesn't re-fetch.
                generated_text, loop_log = generate_with_tools(
                    base_url=base_url,
                    model=selected_model,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    image_media_type=media_type,
                    system_prompt=system_prompt,
                    tools_enabled=tools_enabled,
                    context_urls=[],
                    context_files=[],
                    timeout_seconds=effective_timeout,
                    num_ctx=effective_num_ctx if selected_backend == "ollama" else None,
                )
                tool_usage_log.extend(loop_log)
            else:
                generation_mode = "context_injection"
                # Context-injection only — use the native client APIs so any model
                # works (e.g. fine-tuned Ollama models that crash on /v1/chat/completions).
                if selected_backend == "ollama":
                    generated_text = OllamaClient(base_url=base_url).generate_caption(
                        model=selected_model,
                        prompt=prompt,
                        image_bytes=image_bytes,
                        system_prompt=system_prompt,
                        timeout_seconds=effective_timeout,
                        num_ctx=effective_num_ctx,
                    )
                else:
                    generated_text = LMStudioClient(base_url=base_url).generate_caption(
                        model=selected_model,
                        prompt=prompt,
                        image_bytes=image_bytes,
                        system_prompt=system_prompt,
                        media_type=media_type,
                        timeout_seconds=effective_timeout,
                    )
            break
        except ValueError as error:
            last_error = error
            if not injected_parts or not _is_context_window_overflow_error(str(error)):
                raise
            next_budget = (
                _CONTEXT_RETRY_CHAR_BUDGETS[attempt_index + 1]
                if attempt_index + 1 < len(_CONTEXT_RETRY_CHAR_BUDGETS)
                else None
            )
            if next_budget is None:
                continue
            tool_usage_log.append(
                f"context window overflow detected; retrying with less injected context (next limit={next_budget})"
            )
            continue

    if not generated_text and last_error is not None:
        raise last_error

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
) -> dict[str, object]:
    selected_backend = _normalize_backend_name(backend)
    selected_model = model.strip()
    prompt_text = prompt.strip()
    if not selected_model:
        raise ValueError("Model is required.")
    if not prompt_text:
        raise ValueError("Prompt is required.")
    if timeout_seconds < 10:
        raise ValueError("Timeout must be at least 10 seconds.")

    normalized_project_path = (project_path or "").strip() or None
    if image_id is not None and not normalized_project_path:
        raise ValueError("project_path is required when image_id is provided.")

    requested_tools = [t for t in (tools_enabled or []) if t]
    tools_enabled = list(requested_tools)
    context_urls = [u for u in (context_urls or []) if u]
    context_files = [f for f in (context_files or []) if f]

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

    image_bytes: bytes | None = None
    media_type = "image/png"
    if image_id is not None and normalized_project_path:
        image_bytes, media_type = get_image_content(project_path=normalized_project_path, image_id=image_id)

    tool_usage_log: list[str] = []
    injected_parts: list[str] = []

    if (
        (include_project_notes or project_note_ids)
        and not normalized_project_path
    ):
        raise ValueError("project_path is required when including project notes context.")

    if include_project_notes or project_note_ids or include_global_notes or global_note_ids:
        note_parts, note_log = build_notes_context_parts(
            project_path=normalized_project_path,
            include_project_notes=include_project_notes,
            project_note_ids=project_note_ids or [],
            include_global_notes=include_global_notes,
            global_note_ids=global_note_ids or [],
        )
        injected_parts.extend(note_parts)
        tool_usage_log.extend(note_log)

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

    generation_mode = "context_injection"

    if requested_tools:
        selected_model_info = _lookup_model_info(backend=selected_backend, model_name=selected_model)
        if selected_model_info is not None and not selected_model_info.tool_capable:
            tools_enabled = []
            tool_usage_log.append(
                f"model {selected_model!r} is not tool-capable; using context injection only"
            )

    generated_text = ""
    last_error: ValueError | None = None

    for attempt_index, max_chars in enumerate(_CONTEXT_RETRY_CHAR_BUDGETS):
        system_prompt = _compose_injected_context_prompt(injected_parts, max_chars=max_chars)
        try:
            if tools_enabled:
                generation_mode = "tool_calls"
                generated_text, loop_log = generate_with_tools(
                    base_url=base_url,
                    model=selected_model,
                    prompt=prompt_text,
                    image_bytes=image_bytes,
                    image_media_type=media_type,
                    system_prompt=system_prompt,
                    tools_enabled=tools_enabled,
                    context_urls=[],
                    context_files=[],
                    timeout_seconds=effective_timeout,
                    num_ctx=effective_num_ctx if selected_backend == "ollama" else None,
                )
                tool_usage_log.extend(loop_log)
            else:
                generation_mode = "context_injection"
                if selected_backend == "ollama":
                    generated_text = OllamaClient(base_url=base_url).generate_caption(
                        model=selected_model,
                        prompt=prompt_text,
                        image_bytes=image_bytes,
                        system_prompt=system_prompt,
                        timeout_seconds=effective_timeout,
                        num_ctx=effective_num_ctx,
                    )
                else:
                    generated_text = LMStudioClient(base_url=base_url).generate_caption(
                        model=selected_model,
                        prompt=prompt_text,
                        image_bytes=image_bytes,
                        system_prompt=system_prompt,
                        media_type=media_type,
                        timeout_seconds=effective_timeout,
                    )
            break
        except ValueError as error:
            last_error = error
            if not injected_parts or not _is_context_window_overflow_error(str(error)):
                raise
            next_budget = (
                _CONTEXT_RETRY_CHAR_BUDGETS[attempt_index + 1]
                if attempt_index + 1 < len(_CONTEXT_RETRY_CHAR_BUDGETS)
                else None
            )
            if next_budget is None:
                continue
            tool_usage_log.append(
                f"context window overflow detected; retrying with less injected context (next limit={next_budget})"
            )
            continue

    if not generated_text and last_error is not None:
        raise last_error

    return {
        "text": generated_text,
        "backend": selected_backend,
        "model": selected_model,
        "tool_usage_log": tool_usage_log,
        "generation_mode": generation_mode,
    }
