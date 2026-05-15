from __future__ import annotations

from pathlib import Path


def _frontend_app_js() -> str:
    app_js = Path(__file__).resolve().parent.parent / "frontend" / "app.js"
    return app_js.read_text(encoding="utf-8")


def _method_slice(source: str, start_marker: str, next_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"Missing method marker: {start_marker}"
    end = source.find(next_marker, start)
    assert end != -1, f"Missing next method marker: {next_marker}"
    return source[start:end]


def _assert_llm_delegate_contract(method_block: str, method_name: str) -> None:
    assert "const llmFeature = window.DescribeItFeatures?.llm;" in method_block
    assert f"typeof llmFeature.{method_name} === 'function'" in method_block
    assert f"await llmFeature.{method_name}(this);" in method_block
    assert "this.errorMessage = 'LLM module unavailable. Refresh and try again.';" in method_block

    # Delegate contract: no inline API/fetch fallback logic should be reintroduced.
    forbidden_tokens = ["fetch(", "/api/", "this.api(", "XMLHttpRequest", "prompt_builder"]
    for token in forbidden_tokens:
        assert token not in method_block, (
            f"Delegate method '{method_name}' should not contain inline fallback token: {token}"
        )


def _assert_no_inline_api_fallback_tokens(method_block: str, method_name: str) -> None:
    forbidden_tokens = ["fetch(", "/api/", "this.api(", "XMLHttpRequest"]
    for token in forbidden_tokens:
        assert token not in method_block, (
            f"Delegate method '{method_name}' should not contain inline fallback token: {token}"
        )


def _assert_llm_event_delegate_contract(
    method_block: str,
    method_name: str,
    expected_call: str | None = None,
) -> None:
    if expected_call is None:
        expected_call = f"llmFeature.{method_name}(this);"

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in method_block
    assert f"typeof llmFeature.{method_name} === 'function'" in method_block
    assert expected_call in method_block
    assert method_block.count("this.errorMessage = 'LLM module unavailable. Refresh and try again.';") == 1
    _assert_no_inline_api_fallback_tokens(method_block, method_name)


def test_caption_generation_methods_remain_llm_module_delegates() -> None:
    app_js = _frontend_app_js()

    preset_block = _method_slice(
        app_js,
        "    async generateCaptionWithPreset() {",
        "    async generateCaptionWithLLM() {",
    )
    llm_block = _method_slice(
        app_js,
        "    async generateCaptionWithLLM() {",
        "    async generateCaptionWithTools() {",
    )
    tools_block = _method_slice(
        app_js,
        "    async generateCaptionWithTools() {",
        "    async loadImageSummary() {",
    )

    _assert_llm_delegate_contract(preset_block, "generateCaptionWithPreset")
    _assert_llm_delegate_contract(llm_block, "generateCaptionWithLLM")
    _assert_llm_delegate_contract(tools_block, "generateCaptionWithTools")


def test_backend_model_discovery_methods_remain_delegates_with_safe_defaults() -> None:
    app_js = _frontend_app_js()

    available_models_block = _method_slice(
        app_js,
        "    availableModelsForBackend(backendName) {",
        "    onModelVisibilityFilterChanged() {",
    )
    load_backends_block = _method_slice(
        app_js,
        "    async loadLLMBackends(isStartup = false) {",
        "    onLLMBackendChanged() {",
    )

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in available_models_block
    assert "typeof llmFeature.availableModelsForBackend === 'function'" in available_models_block
    assert "return llmFeature.availableModelsForBackend(this, backendName);" in available_models_block
    assert "return [];" in available_models_block
    _assert_no_inline_api_fallback_tokens(available_models_block, "availableModelsForBackend")

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in load_backends_block
    assert "typeof llmFeature.loadLLMBackends === 'function'" in load_backends_block
    assert "await llmFeature.loadLLMBackends(this, isStartup);" in load_backends_block
    assert "this.llm.backends = [];" in load_backends_block
    assert "this.errorMessage = 'LLM module unavailable. Refresh and try again.';" in load_backends_block
    _assert_no_inline_api_fallback_tokens(load_backends_block, "loadLLMBackends")


def test_preset_crud_methods_remain_llm_module_delegates() -> None:
    app_js = _frontend_app_js()

    create_block = _method_slice(
        app_js,
        "    async createPreset() {",
        "    async updatePreset() {",
    )
    update_block = _method_slice(
        app_js,
        "    async updatePreset() {",
        "    async deletePreset() {",
    )
    delete_block = _method_slice(
        app_js,
        "    async deletePreset() {",
        "    onSelectedPresetChanged() {",
    )

    _assert_llm_delegate_contract(create_block, "createPreset")
    _assert_llm_delegate_contract(update_block, "updatePreset")
    _assert_llm_delegate_contract(delete_block, "deletePreset")


def test_load_llm_presets_keeps_safe_default_delegate_contract() -> None:
    app_js = _frontend_app_js()

    load_presets_block = _method_slice(
        app_js,
        "    async loadLLMPresets(isStartup = false) {",
        "    async createPreset() {",
    )

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in load_presets_block
    assert "typeof llmFeature.loadLLMPresets === 'function'" in load_presets_block
    assert "await llmFeature.loadLLMPresets(this, isStartup);" in load_presets_block
    assert "this.llm.presets = [];" in load_presets_block
    assert "this.errorMessage = 'LLM module unavailable. Refresh and try again.';" in load_presets_block
    _assert_no_inline_api_fallback_tokens(load_presets_block, "loadLLMPresets")


def test_llm_helper_delegate_safe_return_contracts_remain_stable() -> None:
    app_js = _frontend_app_js()

    selected_backend_block = _method_slice(
        app_js,
        "    selectedLLMBackend() {",
        "    selectedLLMModel() {",
    )
    selected_model_block = _method_slice(
        app_js,
        "    selectedLLMModel() {",
        "    modelCapabilityLabel(backendName, modelName) {",
    )
    available_models_block = _method_slice(
        app_js,
        "    availableModelsForBackend(backendName) {",
        "    onModelVisibilityFilterChanged() {",
    )

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in selected_backend_block
    assert "typeof llmFeature.selectedLLMBackend === 'function'" in selected_backend_block
    assert "return llmFeature.selectedLLMBackend(this);" in selected_backend_block
    assert "return null;" in selected_backend_block
    _assert_no_inline_api_fallback_tokens(selected_backend_block, "selectedLLMBackend")

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in selected_model_block
    assert "typeof llmFeature.selectedLLMModel === 'function'" in selected_model_block
    assert "return llmFeature.selectedLLMModel(this);" in selected_model_block
    assert "return null;" in selected_model_block
    _assert_no_inline_api_fallback_tokens(selected_model_block, "selectedLLMModel")

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in available_models_block
    assert "typeof llmFeature.availableModelsForBackend === 'function'" in available_models_block
    assert "return llmFeature.availableModelsForBackend(this, backendName);" in available_models_block
    assert "return [];" in available_models_block
    _assert_no_inline_api_fallback_tokens(available_models_block, "availableModelsForBackend")


def test_llm_label_helpers_keep_safe_fallback_contracts() -> None:
    app_js = _frontend_app_js()

    model_capability_block = _method_slice(
        app_js,
        "    modelCapabilityLabel(backendName, modelName) {",
        "    modelOptionLabel(modelInfo) {",
    )
    model_option_block = _method_slice(
        app_js,
        "    modelOptionLabel(modelInfo) {",
        "    availableModelsForBackend(backendName) {",
    )

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in model_capability_block
    assert "typeof llmFeature.modelCapabilityLabel === 'function'" in model_capability_block
    assert "return llmFeature.modelCapabilityLabel(this, backendName, modelName);" in model_capability_block
    assert "return '';" in model_capability_block
    _assert_no_inline_api_fallback_tokens(model_capability_block, "modelCapabilityLabel")

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in model_option_block
    assert "typeof llmFeature.modelOptionLabel === 'function'" in model_option_block
    assert "return llmFeature.modelOptionLabel(this, modelInfo);" in model_option_block
    assert "return modelInfo?.name || '';" in model_option_block
    _assert_no_inline_api_fallback_tokens(model_option_block, "modelOptionLabel")


def test_load_llm_backends_startup_fallback_contract_has_single_branch() -> None:
    app_js = _frontend_app_js()

    load_backends_block = _method_slice(
        app_js,
        "    async loadLLMBackends(isStartup = false) {",
        "    onLLMBackendChanged() {",
    )

    assert "const llmFeature = window.DescribeItFeatures?.llm;" in load_backends_block
    assert "typeof llmFeature.loadLLMBackends === 'function'" in load_backends_block
    assert "await llmFeature.loadLLMBackends(this, isStartup);" in load_backends_block

    # Guard against duplicate fallback branches drifting into this method.
    assert load_backends_block.count("this.llm.backends = [];") == 1
    assert load_backends_block.count("this.errorMessage = 'LLM module unavailable. Refresh and try again.';") == 1

    _assert_no_inline_api_fallback_tokens(load_backends_block, "loadLLMBackends")


def test_llm_event_delegates_keep_single_module_unavailable_error_path() -> None:
    app_js = _frontend_app_js()

    on_backend_changed_block = _method_slice(
        app_js,
        "    onLLMBackendChanged() {",
        "    onPresetBackendChanged() {",
    )
    on_preset_backend_changed_block = _method_slice(
        app_js,
        "    onPresetBackendChanged() {",
        "    resetPresetForm() {",
    )
    on_selected_preset_changed_block = _method_slice(
        app_js,
        "    onSelectedPresetChanged() {",
        "    batchIsActive() {",
    )

    checks = [
        (on_backend_changed_block, "onLLMBackendChanged"),
        (on_preset_backend_changed_block, "onPresetBackendChanged"),
        (on_selected_preset_changed_block, "onSelectedPresetChanged"),
    ]

    for method_block, method_name in checks:
        _assert_llm_event_delegate_contract(method_block, method_name)


def test_llm_visibility_and_default_selection_helpers_keep_single_error_path() -> None:
    app_js = _frontend_app_js()

    visibility_filter_block = _method_slice(
        app_js,
        "    onModelVisibilityFilterChanged() {",
        "    pickDefaultLLMSelection() {",
    )
    default_selection_block = _method_slice(
        app_js,
        "    pickDefaultLLMSelection() {",
        "    async loadLLMBackends(isStartup = false) {",
    )

    checks = [
        (visibility_filter_block, "onModelVisibilityFilterChanged"),
        (default_selection_block, "pickDefaultLLMSelection"),
    ]

    for method_block, method_name in checks:
        _assert_llm_event_delegate_contract(method_block, method_name)


def test_preset_helper_delegates_keep_single_error_path_and_passthrough() -> None:
    app_js = _frontend_app_js()

    reset_preset_block = _method_slice(
        app_js,
        "    resetPresetForm() {",
        "    applyPresetToForm(preset) {",
    )
    apply_preset_block = _method_slice(
        app_js,
        "    applyPresetToForm(preset) {",
        "    async loadLLMPresets(isStartup = false) {",
    )

    _assert_llm_event_delegate_contract(reset_preset_block, "resetPresetForm")
    assert "applyPresetToForm(preset)" in apply_preset_block
    _assert_llm_event_delegate_contract(
        apply_preset_block,
        "applyPresetToForm",
        "llmFeature.applyPresetToForm(this, preset);",
    )
