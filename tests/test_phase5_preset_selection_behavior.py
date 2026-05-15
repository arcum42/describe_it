from __future__ import annotations

from pathlib import Path


def _read_frontend_file(*parts: str) -> str:
    return (Path(__file__).resolve().parent.parent / "frontend" / Path(*parts)).read_text(encoding="utf-8")


def _llm_feature_text() -> str:
    return _read_frontend_file("js", "features", "llm.js")


def _method_slice(source: str, start_marker: str, next_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"Missing method marker: {start_marker}"
    end = source.find(next_marker, start)
    assert end != -1, f"Missing next method marker: {next_marker}"
    return source[start:end]


def _assert_contains_all(block: str, snippets: list[str]) -> None:
    for snippet in snippets:
        assert snippet in block


def test_apply_preset_preference_keeps_default_apply_guards() -> None:
    app_js = _read_frontend_file("app.js")
    block = _method_slice(
        app_js,
        "    applyPresetPreference() {",
        "    async generateCaptionWithPreset() {",
    )

    # Keep invalid selected preset reconciliation before default-apply checks.
    assert "const selectedExists = this.llm.presets.some((item) => String(item.id) === String(this.llm.selectedPresetId));" in block
    assert "if (!selectedExists) {" in block
    assert "this.llm.selectedPresetId = '';" in block

    # Default-preset auto-apply should remain guarded behind explicit flags.
    assert "if (!this.settings.usePresetByDefault) {" in block
    assert "if (!this.settings.defaultPresetId) {" in block
    assert "const preset = this.llm.presets.find((item) => String(item.id) === String(this.settings.defaultPresetId));" in block
    assert "if (preset && !this.llm.selectedPresetId) {" in block
    assert "this.applyPresetToForm(preset);" in block


def test_on_preset_backend_changed_keeps_model_reselection_behavior() -> None:
    llm_js = _llm_feature_text()
    block = _method_slice(
        llm_js,
        "  function onPresetBackendChanged(app) {",
        "  function resetPresetForm(app) {",
    )

    # Prefer currently visible models first, then gracefully fallback to all backend models.
    _assert_contains_all(
        block,
        [
            "let models = availableModelsForBackend(app, app.llm.presetForm.backend);",
            "if (models.length === 0) {",
            "const backend = app.llm.backends.find((item) => item.name === app.llm.presetForm.backend);",
            "models = backend?.models ?? [];",
        ],
    )

    # If current preset model is no longer valid, reselect first available or clear.
    _assert_contains_all(
        block,
        [
            "if (!models.some((item) => item.name === app.llm.presetForm.modelName)) {",
            "app.llm.presetForm.modelName = models[0]?.name ?? '';",
        ],
    )


def test_load_llm_presets_reconciles_selection_then_applies_preference() -> None:
    llm_js = _llm_feature_text()
    block = _method_slice(
        llm_js,
        "  async function loadLLMPresets(app, isStartup = false) {",
        "  async function createPreset(app) {",
    )

    # Remove stale selected/default preset IDs before applying preference behavior.
    _assert_contains_all(
        block,
        [
            "if (app.llm.selectedPresetId && !app.llm.presets.some((preset) => String(preset.id) === app.llm.selectedPresetId)) {",
            "app.llm.selectedPresetId = '';",
            "if (app.settings.defaultPresetId && !app.llm.presets.some((preset) => String(preset.id) === app.settings.defaultPresetId)) {",
            "app.settings.defaultPresetId = '';",
        ],
    )

    # Re-run default selection behavior after reconciliation.
    assert "app.applyPresetPreference();" in block


def test_preset_lifecycle_flow_keeps_selection_reset_and_status_contracts() -> None:
    llm_js = _llm_feature_text()

    create_block = _method_slice(
        llm_js,
        "  async function createPreset(app) {",
        "  async function updatePreset(app) {",
    )
    update_block = _method_slice(
        llm_js,
        "  async function updatePreset(app) {",
        "  async function deletePreset(app) {",
    )
    delete_block = _method_slice(
        llm_js,
        "  async function deletePreset(app) {",
        "  function onSelectedPresetChanged(app) {",
    )

    # Create flow should reload presets, keep selected preset continuity, and emit status.
    _assert_contains_all(
        create_block,
        [
            "await loadLLMPresets(app);",
            "applyPresetToForm(app, payload.preset);",
            "app.statusMessage = `Created preset ${payload.preset.name}.`;",
        ],
    )

    # Update flow should mirror create continuity semantics with updated status wording.
    _assert_contains_all(
        update_block,
        [
            "await loadLLMPresets(app);",
            "applyPresetToForm(app, payload.preset);",
            "app.statusMessage = `Updated preset ${payload.preset.name}.`;",
        ],
    )

    # Delete flow should reload presets, reset form, clear selection, and emit delete status.
    _assert_contains_all(
        delete_block,
        [
            "await loadLLMPresets(app);",
            "resetPresetForm(app);",
            "app.llm.selectedPresetId = '';",
            "app.statusMessage = `Deleted preset ${payload.deleted_preset_id}.`;",
        ],
    )


def test_selection_helpers_handle_unavailable_backend_edge_cases() -> None:
    llm_js = _llm_feature_text()

    pick_default_block = _method_slice(
        llm_js,
        "  function pickDefaultLLMSelection(app) {",
        "  async function loadLLMBackends(app, isStartup = false) {",
    )
    available_models_block = _method_slice(
        llm_js,
        "  function availableModelsForBackend(app, backendName) {",
        "  function onModelVisibilityFilterChanged(app) {",
    )
    selected_backend_block = _method_slice(
        llm_js,
        "  function selectedLLMBackend(app) {",
        "  function selectedLLMModel(app) {",
    )
    selected_model_block = _method_slice(
        llm_js,
        "  function selectedLLMModel(app) {",
        "  function modelCapabilityLabel(app, backendName, modelName) {",
    )

    _assert_contains_all(
        pick_default_block,
        [
            "const available = app.llm.backends.filter((item) => item.available);",
            "if (available.length === 0) {",
            "app.llm.backend = '';",
            "app.llm.model = '';",
            "if (!available.some((item) => item.name === app.llm.backend)) {",
            "app.llm.backend = available[0].name;",
            "let models = availableModelsForBackend(app, app.llm.backend);",
            "if (models.length === 0) {",
            "const fallbackBackend = available.find((item) => availableModelsForBackend(app, item.name).length > 0);",
            "if (fallbackBackend) {",
            "app.llm.backend = fallbackBackend.name;",
            "models = availableModelsForBackend(app, app.llm.backend);",
            "if (!models.some((item) => item.name === app.llm.model)) {",
            "app.llm.model = models[0]?.name ?? '';",
        ],
    )

    _assert_contains_all(
        available_models_block,
        [
            "const models = backend?.models ?? [];",
            "if (app.llm.showAllModels) {",
            "return models;",
            "return models.filter((model) => model.vision_capable);",
        ],
    )

    _assert_contains_all(
        selected_backend_block,
        [
            "return app.llm.backends.find((item) => item.name === app.llm.backend) || null;",
        ],
    )
    _assert_contains_all(
        selected_model_block,
        [
            "const backend = selectedLLMBackend(app);",
            "if (!backend) {",
            "return null;",
            "return backend.models?.find((item) => item.name === app.llm.model) || null;",
        ],
    )
