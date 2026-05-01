from __future__ import annotations

from dataclasses import dataclass
import re


_THINK_TAG_PATTERN = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)

REASONING_MODE_VALUES = {"off", "on", "low", "medium", "high"}
REASONING_VISIBILITY_VALUES = {"hidden", "blockquote", "code"}


def normalize_reasoning_mode(value: str | None) -> str:
    raw = (value or "off").strip().lower()
    return raw if raw in REASONING_MODE_VALUES else "off"


def normalize_reasoning_visibility(value: str | None) -> str:
    raw = (value or "hidden").strip().lower()
    return raw if raw in REASONING_VISIBILITY_VALUES else "hidden"


def split_reasoning_content(*, text: str, explicit_reasoning: str = "") -> tuple[str, str]:
    answer = (text or "").strip()
    reasoning = (explicit_reasoning or "").strip()

    if not reasoning:
        matches = _THINK_TAG_PATTERN.findall(answer)
        if matches:
            reasoning = "\n\n".join(part.strip() for part in matches if part and part.strip())
            answer = _THINK_TAG_PATTERN.sub("", answer).strip()

    return answer, reasoning


def format_reasoning_output(*, answer: str, reasoning: str, visibility: str) -> str:
    clean_answer = (answer or "").strip()
    clean_reasoning = (reasoning or "").strip()
    mode = normalize_reasoning_visibility(visibility)

    if not clean_reasoning or mode == "hidden":
        return clean_answer

    if mode == "code":
        return f"Reasoning:\n```text\n{clean_reasoning}\n```\n\nAnswer:\n{clean_answer}".strip()

    quoted_reasoning = "\n".join(f"> {line}" if line.strip() else ">" for line in clean_reasoning.splitlines())
    return f"Reasoning:\n{quoted_reasoning}\n\nAnswer:\n{clean_answer}".strip()


@dataclass
class ModelInfo:
    name: str
    vision_capable: bool = False
    tool_capable: bool = False
    reasoning_capable: bool = False
    capabilities: list[str] | None = None


@dataclass
class BackendInfo:
    name: str
    available: bool = False
    models: list[ModelInfo] | None = None
    error: str | None = None


@dataclass
class GenerationResult:
    text: str
    reasoning: str = ""
