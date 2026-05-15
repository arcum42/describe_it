from __future__ import annotations

from collections.abc import Callable


def is_context_window_overflow_error(message: str) -> bool:
    lowered = message.lower()
    if "n_keep" in lowered and "n_ctx" in lowered:
        return True
    return "context length" in lowered or "maximum context length" in lowered


def compose_injected_context_prompt(parts: list[str], *, max_chars: int | None) -> str:
    if not parts:
        return ""

    full = "\n\n".join(parts)
    if max_chars is None or len(full) <= max_chars:
        return full

    truncated = full[: max(0, max_chars - len("\n[truncated]"))].rstrip()
    if not truncated:
        return ""
    return f"{truncated}\n[truncated]"


def run_generation_with_context_retries(
    *,
    injected_parts: list[str],
    context_retry_char_budgets: tuple[int | None, ...],
    tool_usage_log: list[str],
    generate_once: Callable[[str], tuple[str, str, str, list[str]]],
) -> tuple[str, str, str]:
    """Run model generation with context-window overflow retries.

    generate_once receives the injected context prompt and returns:
    (answer_text, reasoning_text, generation_mode, loop_log)
    """
    last_error: ValueError | None = None

    for attempt_index, max_chars in enumerate(context_retry_char_budgets):
        injected_prompt = compose_injected_context_prompt(injected_parts, max_chars=max_chars)
        try:
            answer_text, reasoning_text, generation_mode, loop_log = generate_once(injected_prompt)
            if loop_log:
                tool_usage_log.extend(loop_log)
            return answer_text, reasoning_text, generation_mode
        except ValueError as error:
            last_error = error
            if not injected_parts or not is_context_window_overflow_error(str(error)):
                raise

            next_budget = (
                context_retry_char_budgets[attempt_index + 1]
                if attempt_index + 1 < len(context_retry_char_budgets)
                else None
            )
            if next_budget is None:
                continue

            tool_usage_log.append(
                f"context window overflow detected; retrying with less injected context (next limit={next_budget})"
            )

    if last_error is not None:
        raise last_error

    # Defensive fallback: if no retries ran for any reason.
    raise ValueError("Generation failed without a reported error.")
