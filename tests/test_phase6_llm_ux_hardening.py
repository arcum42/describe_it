from __future__ import annotations

from pathlib import Path


def _llm_feature_text() -> str:
    return (Path(__file__).resolve().parent.parent / "frontend" / "js" / "features" / "llm.js").read_text(encoding="utf-8")


def _method_slice(source: str, start_marker: str, next_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"Missing method marker: {start_marker}"
    end = source.find(next_marker, start)
    assert end != -1, f"Missing next method marker: {next_marker}"
    return source[start:end]


def test_llm_ux_error_normalizer_covers_timeout_and_connectivity() -> None:
    llm_js = _llm_feature_text()

    helper_block = _method_slice(
        llm_js,
        "  function normalizeLlmUxErrorMessage(error, fallbackMessage) {",
        "  function setLlmUxError(app, error, fallbackMessage) {",
    )

    assert "if (/timeout|timed out/i.test(message)) {" in helper_block
    assert "LLM request timed out. Try again or increase the timeout setting." in helper_block
    assert "if (/network|failed to fetch|connection|unreachable|refused|offline/i.test(message)) {" in helper_block
    assert "LLM backend is unreachable. Verify backend availability and try again." in helper_block


def test_core_load_paths_use_shared_llm_ux_error_helper() -> None:
    llm_js = _llm_feature_text()

    load_backends_block = _method_slice(
        llm_js,
        "  async function loadLLMBackends(app, isStartup = false) {",
        "  function onLLMBackendChanged(app) {",
    )
    load_presets_block = _method_slice(
        llm_js,
        "  async function loadLLMPresets(app, isStartup = false) {",
        "  async function createPreset(app) {",
    )

    assert "setLlmUxError(app, error, 'Failed to load LLM backends');" in load_backends_block
    assert "setLlmUxError(app, error, 'Failed to load presets');" in load_presets_block
