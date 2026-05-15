from __future__ import annotations

import pytest

from backend.services.llm_generation_pipeline import (
    compose_injected_context_prompt,
    is_context_window_overflow_error,
    run_generation_with_context_retries,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("n_keep must be smaller than n_ctx", True),
        ("Maximum context length exceeded", True),
        ("context length is too large", True),
        ("connection timed out", False),
    ],
)
def test_is_context_window_overflow_error_detection(message: str, expected: bool) -> None:
    assert is_context_window_overflow_error(message) is expected


def test_compose_injected_context_prompt_joins_parts() -> None:
    result = compose_injected_context_prompt(["part-a", "part-b"], max_chars=None)
    assert result == "part-a\n\npart-b"


def test_compose_injected_context_prompt_truncates_and_marks() -> None:
    full = "abcdefghij\n\nklmnopqrst"
    result = compose_injected_context_prompt(["abcdefghij", "klmnopqrst"], max_chars=16)
    assert result.endswith("\n[truncated]")
    assert result == f"{full[:4]}\n[truncated]"


def test_compose_injected_context_prompt_returns_empty_when_budget_too_small() -> None:
    assert compose_injected_context_prompt(["content"], max_chars=5) == ""


def test_run_generation_with_context_retries_returns_first_success_and_extends_loop_log() -> None:
    tool_usage_log: list[str] = []
    seen_prompts: list[str] = []

    def generate_once(prompt: str) -> tuple[str, str, str, list[str]]:
        seen_prompts.append(prompt)
        return ("answer", "reasoning", "context_injection", ["tool-loop-step"])

    answer, reasoning, mode = run_generation_with_context_retries(
        injected_parts=["one", "two"],
        context_retry_char_budgets=(None, 10),
        tool_usage_log=tool_usage_log,
        generate_once=generate_once,
    )

    assert (answer, reasoning, mode) == ("answer", "reasoning", "context_injection")
    assert seen_prompts == ["one\n\ntwo"]
    assert tool_usage_log == ["tool-loop-step"]


def test_run_generation_with_context_retries_reduces_context_after_overflow() -> None:
    tool_usage_log: list[str] = []
    seen_prompts: list[str] = []

    def generate_once(prompt: str) -> tuple[str, str, str, list[str]]:
        seen_prompts.append(prompt)
        if len(seen_prompts) < 3:
            raise ValueError("maximum context length exceeded")
        return ("ok", "", "context_injection", [])

    answer, reasoning, mode = run_generation_with_context_retries(
        injected_parts=["abcdefghijklmnopqrstuvwxyz"],
        context_retry_char_budgets=(None, 16, 5),
        tool_usage_log=tool_usage_log,
        generate_once=generate_once,
    )

    assert (answer, reasoning, mode) == ("ok", "", "context_injection")
    assert len(seen_prompts) == 3
    assert seen_prompts[0] == "abcdefghijklmnopqrstuvwxyz"
    assert seen_prompts[1] == "abcd\n[truncated]"
    assert seen_prompts[2] == ""
    assert tool_usage_log == [
        "context window overflow detected; retrying with less injected context (next limit=16)",
        "context window overflow detected; retrying with less injected context (next limit=5)",
    ]


def test_run_generation_with_context_retries_raises_on_non_overflow_error() -> None:
    tool_usage_log: list[str] = []

    def generate_once(_prompt: str) -> tuple[str, str, str, list[str]]:
        raise ValueError("service unavailable")

    with pytest.raises(ValueError, match="service unavailable"):
        run_generation_with_context_retries(
            injected_parts=["ctx"],
            context_retry_char_budgets=(None, 8),
            tool_usage_log=tool_usage_log,
            generate_once=generate_once,
        )

    assert tool_usage_log == []


def test_run_generation_with_context_retries_does_not_retry_with_no_injected_parts() -> None:
    tool_usage_log: list[str] = []
    calls = 0

    def generate_once(_prompt: str) -> tuple[str, str, str, list[str]]:
        nonlocal calls
        calls += 1
        raise ValueError("maximum context length exceeded")

    with pytest.raises(ValueError, match="maximum context length exceeded"):
        run_generation_with_context_retries(
            injected_parts=[],
            context_retry_char_budgets=(None, 8),
            tool_usage_log=tool_usage_log,
            generate_once=generate_once,
        )

    assert calls == 1
    assert tool_usage_log == []


def test_run_generation_with_context_retries_raises_last_error_when_final_budget_exhausted() -> None:
    tool_usage_log: list[str] = []
    calls = 0

    def generate_once(_prompt: str) -> tuple[str, str, str, list[str]]:
        nonlocal calls
        calls += 1
        raise ValueError("n_keep must be smaller than n_ctx")

    with pytest.raises(ValueError, match="n_keep must be smaller than n_ctx"):
        run_generation_with_context_retries(
            injected_parts=["context"],
            context_retry_char_budgets=(8,),
            tool_usage_log=tool_usage_log,
            generate_once=generate_once,
        )

    assert calls == 1
    assert tool_usage_log == []