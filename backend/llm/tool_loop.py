"""Agentic multi-turn tool-calling loop.

Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint, which both
Ollama and LM Studio expose.  The loop:

1. Optionally pre-fetches context URLs and files, injecting their content
   into the system prompt (works with any model, not just tool-capable ones).
2. Sends the conversation with a ``tools`` array when ``tools_enabled`` is
   non-empty and the backend supports it.
3. If the model returns ``tool_calls``, executes each tool via
   ``tool_service.execute_tool`` and appends the results to the conversation.
4. Repeats up to ``max_tool_rounds``; breaks when no tool calls remain.
5. Returns the final caption text and a list of display summary strings for UI.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from backend.services.tool_service import (
    ToolResult,
    execute_tool,
    fetch_file_as_context,
    fetch_url_as_context,
    list_tool_schemas,
)

_MAX_TOOL_ROUNDS = 5


def _post_chat(
    base_url: str,
    payload: dict[str, object],
    timeout_seconds: int,
) -> dict[str, object]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = ""
        if error.fp is not None:
            body = error.fp.read().decode("utf-8", errors="replace")
        detail = body.strip() or error.reason
        raise ValueError(f"Chat completions request failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise ValueError(f"Chat completions request failed: {error.reason}") from error


def _extract_text(response: dict[str, object]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] if isinstance(choices[0], dict) else {}).get("message") or {}
    return (message.get("content") or "").strip()


def _extract_tool_calls(response: dict[str, object]) -> list[dict[str, object]]:
    choices = response.get("choices") or []
    if not choices:
        return []
    message = (choices[0] if isinstance(choices[0], dict) else {}).get("message") or {}
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    return [tc for tc in tool_calls if isinstance(tc, dict)]


def _build_context_block(results: list[ToolResult]) -> str:
    if not results:
        return ""
    parts = []
    for result in results:
        parts.append(f"### {result.tool_name}: {result.display_summary}\n{result.content}")
    return "\n\n".join(parts)


def generate_with_tools(
    *,
    base_url: str,
    model: str,
    prompt: str,
    image_bytes: bytes | None = None,
    image_media_type: str = "image/png",
    system_prompt: str = "",
    tools_enabled: list[str] | None = None,
    context_urls: list[str] | None = None,
    context_files: list[str] | None = None,
    timeout_seconds: int = 120,
    max_tool_rounds: int = _MAX_TOOL_ROUNDS,
    num_ctx: int | None = None,
) -> tuple[str, list[str]]:
    """Run tool-augmented caption generation.

    Returns ``(caption_text, tool_usage_log)`` where ``tool_usage_log`` is a
    list of human-readable ``display_summary`` strings from each tool call made
    during the loop (empty if no tools were called).
    """
    tools_enabled = [t for t in (tools_enabled or []) if t]
    context_urls = [u for u in (context_urls or []) if u]
    context_files = [f for f in (context_files or []) if f]

    tool_usage_log: list[str] = []

    # --- Pre-inject user-provided context (works with any model) ---
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

    effective_system = system_prompt.strip()
    if injected_parts:
        context_block = "\n\n".join(injected_parts)
        if effective_system:
            effective_system = f"{effective_system}\n\n{context_block}"
        else:
            effective_system = context_block

    if tools_enabled and effective_system:
        effective_system += (
            "\n\nYou have access to tools. Use them if you need additional context "
            "about what is depicted in the image before writing the caption."
        )
    elif tools_enabled:
        effective_system = (
            "You have access to tools. Use them if you need additional context "
            "about what is depicted in the image before writing the caption."
        )

    # --- Build initial messages ---
    messages: list[dict[str, object]] = []
    if effective_system:
        messages.append({"role": "system", "content": effective_system})

    user_content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        user_content.append(
            {"type": "image_url", "image_url": {"url": f"data:{image_media_type};base64,{b64}"}}
        )
    messages.append({"role": "user", "content": user_content})

    # --- Build payload ---
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if num_ctx is not None:
        payload["options"] = {"num_ctx": int(num_ctx)}
    tool_schemas = list_tool_schemas(tools_enabled)
    if tool_schemas:
        payload["tools"] = tool_schemas

    # --- Agentic loop ---
    last_text = ""
    for _round in range(max_tool_rounds):
        response = _post_chat(base_url, payload, timeout_seconds)
        last_text = _extract_text(response)
        tool_calls = _extract_tool_calls(response)

        if not tool_calls:
            # No more tool calls — final answer ready.
            break

        # Append assistant message (with tool_calls) to the conversation.
        choices = response.get("choices") or []
        assistant_message = (
            (choices[0] if isinstance(choices[0], dict) else {}).get("message") or {}
        )
        messages.append(dict(assistant_message))

        # Execute each tool call and append results.
        for tc in tool_calls:
            call_id = tc.get("id") or ""
            function = tc.get("function") or {}
            tool_name = str(function.get("name") or "")
            raw_args = function.get("arguments") or "{}"
            try:
                arguments: dict[str, object] = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                arguments = {}

            result: ToolResult = execute_tool(tool_name, arguments)
            tool_usage_log.append(result.display_summary)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result.content,
                }
            )

        # Update payload messages and remove tools for subsequent rounds
        # (model writes the final caption without further tool access).
        payload["messages"] = messages
        payload.pop("tools", None)

    if not last_text:
        raise ValueError("The model returned an empty response.")

    return last_text, tool_usage_log
