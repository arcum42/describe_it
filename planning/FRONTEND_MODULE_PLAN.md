# Frontend Module Plan (No Required Node Setup)

This plan keeps runtime Python-only while making the frontend easier to maintain as features expand.

## Constraints

- Runtime startup must remain:
  1. `python -m venv .venv`
  2. `pip install -r requirements.txt`
  3. `python run.py`
- No required Node.js/npm for baseline use.
- Frontend remains static assets served by FastAPI.

## Current Pain Point

`frontend/app.js` currently mixes state, API calls, feature logic, and UI helpers in one large object, which increases merge conflicts and makes new features harder to add safely.

## Target Structure

Use browser-loaded feature modules attached to `window.DescribeItFeatures`, included before `frontend/app.js`.

Suggested layout:

- `frontend/app.js` (thin composition root)
- `frontend/js/core/http.js`
- `frontend/js/core/errors.js`
- `frontend/js/core/ops.js`
- `frontend/js/features/projects.js`
- `frontend/js/features/editor.js`
- `frontend/js/features/llm.js`
- `frontend/js/features/batch.js`
- `frontend/js/features/notes.js`
- `frontend/js/features/settings.js`
- `frontend/js/features/rag.js`
- `frontend/js/features/browser.js`
- `frontend/js/features/export.js`
- `frontend/js/features/import.js`

## Module Responsibilities

- `core/http.js`
  - `fetchWithRetry`, JSON helpers, and shared request wrappers.
- `core/errors.js`
  - API error shaping (`formatApiError`) and user-facing fallback messages.
- `core/ops.js`
  - Submission/operation tracking (`withSubmitting`, active operation keys).
- `features/projects.js`
  - Create/open/close project, metadata save, recents, project session reopen.
- `features/editor.js`
  - Image summary/list/select, include toggles, caption CRUD, and editor sync.
- `features/llm.js`
  - Backend/model load, presets CRUD, single-image generation.
- `features/batch.js`
  - Batch start/poll/history/results controls.
- `features/notes.js`
  - Project/global notes CRUD and note generation with LLM.
- `features/settings.js`
  - App settings load/save and connection tests.
- `features/rag.js`
  - RAG status/rebuild actions.
- `features/browser.js`
  - Filesystem browser state/actions.
- `features/export.js`
  - Export preview/options normalization and export execution.
- `features/import.js`
  - Import workflows.

## Incremental Migration Steps

1. Extract shared utilities first.
- Move `fetchWithRetry`, `formatApiError`, timeout normalizers, and operation tracker into `core/*`.
- Keep existing behavior unchanged.

2. Extract one stable feature at a time.
- Start with `settings`, then `projects`, then `browser`.
- Wire modules back into the existing root object to avoid big-bang rewrites.

3. Extract high-churn features next.
- Move `editor`, `llm`, `batch`, `notes` in separate passes.
- After each pass, run pytest and basic UI smoke checks.

4. Keep static include order explicit.
- Include each feature script before `frontend/app.js`.
- Preserve cache-busting query strings.

5. Optional quality pass.
- Add optional lint/format tooling for contributors only (not required for runtime).
- If tooling is added, document it as optional in README.

## Progress Snapshot

Completed extractions:

- `core/http.js`
- `core/errors.js`
- `core/ops.js`
- `features/settings.js`
- `features/projects.js`
- `features/browser.js`
- `features/rag.js`
- `features/llm.js`
- `features/notes.js`
- `features/batch.js`
- `features/editor.js`
- `features/export.js`
- `features/import.js`

Current pattern:

- Keep method bodies in feature files.
- In `frontend/app.js`, delegate to `window.DescribeItFeatures.<feature>` first.
- For extracted areas, `frontend/app.js` now uses module-required delegation with clear "module unavailable" errors and safe helper defaults.

Cleanup progress:

- Removed inline fallback bodies for import/export methods in `frontend/app.js` (module-required paths).
- Removed inline fallback bodies for editor methods in `frontend/app.js` (image/caption module-required paths).
- Removed inline fallback bodies for batch methods in `frontend/app.js` (batch module-required paths).
- Removed inline fallback bodies for browser/projects action methods in `frontend/app.js` (module-required paths).
- Removed inline fallback bodies for settings/rag methods in `frontend/app.js` (module-required paths; safe defaults for utility getters).
- Removed inline fallback bodies for notes methods in `frontend/app.js` (module-required paths; safe defaults for note-LLM helper getters).
- Removed inline fallback bodies for LLM delegated methods in `frontend/app.js` (module-required paths; safe defaults for helper getters).
- Moved caption generation workflows (`generateCaptionWithPreset`, `generateCaptionWithLLM`, `generateCaptionWithTools`) into `frontend/js/features/llm.js` and made `frontend/app.js` pure delegation.
- Removed unused compatibility module `frontend/js/features/io.js` and its script include.

Likely next slices:

- Optional polish only (for example small UX copy tweaks around module-unavailable errors).

## Phase 4 Spike: Fragment Boundaries + Loader Lifecycle (2026-05-15)

Goal:

- Decompose `frontend/index.html` without breaking Alpine initialization order or the Python-only static runtime.

Proposed fragment boundaries (first-pass extraction targets):

- `fragments/shell/sidebar.html`
  - project cards, filesystem browser, sidebar status/recent project blocks.
- `fragments/workspace/home.html`
  - create/open project workspace panels.
- `fragments/workspace/grid.html`
  - image grid section used when project is open.
- `fragments/workspace/editor.html`
  - single-image editor section used when project is open.
- `fragments/workspace/notes.html`
- `fragments/workspace/io.html`
- `fragments/workspace/batch.html`
- `fragments/settings/general.html`
- `fragments/settings/presets.html`
- `fragments/settings/imageboards.html`
- `fragments/modals/keyboard_shortcuts.html`
- `fragments/modals/imageboard_import.html`

Loader lifecycle constraints (must hold):

- Keep a single Alpine root: `<div x-data="describeItApp()" x-init="init()">` remains in `frontend/index.html`.
- Load and inject fragment HTML before Alpine boots; Alpine remains the final script include.
- Keep JavaScript includes in `frontend/index.html`; fragment files must not contain `<script>` tags.
- Preserve deterministic script order:
  1. core/state/feature scripts
  2. `frontend/app.js`
  3. Alpine CDN script
- Keep existing `x-if`/`x-show` condition boundaries in the same owning fragment to avoid cross-fragment template coupling.
- Keep modal markup inside the Alpine root so `@keydown.window` and modal booleans continue to work unchanged.
- Treat fragment loading as best-effort but visible on failure (set `errorMessage` and continue with any already-loaded content).
- Preserve idempotent startup side effects (for example, keyboard shortcut registration already guards against duplicate listener setup).

Implementation constraints for first loader pass:

- Add a tiny static loader (`frontend/js/core/fragments.js`) that fetches `/static/fragments/*.html` and injects into `[data-fragment]` placeholders.
- Use static, explicit fragment map in `frontend/index.html` (no dynamic discovery).
- Defer structural movement of high-risk editor internals until sidebar + one workspace section prove stable.

Recommended first implementation slice:

- Extract only `sidebar` + `workspace/home` + `keyboard shortcuts modal` into fragments.
- Validate with focused regressions:
  - `tests/test_startup_selection_regression.py`
  - `tests/test_smoke_e2e.py`
  - `tests/test_native_picker_api.py`
  - `tests/test_batch_regression.py`

Implementation progress:

- Completed first Phase 4 slice (2026-05-15):
  - added `frontend/js/core/fragments.js` to load static fragments before Alpine boot.
  - extracted `sidebar`, `workspace/home`, and `keyboard shortcuts` modal into `frontend/fragments/*`.
  - focused regressions passed (`35` tests across startup/smoke/native-picker/batch suites).
- Completed second Phase 4 slice (2026-05-15):
  - extracted settings tab sections (`general`, `presets`, `imageboards`) into `frontend/fragments/settings/*`.
  - replaced inline settings tab markup in `frontend/index.html` with `data-fragment` placeholders while keeping existing `x-if` boundaries.
  - focused regressions passed (`109` tests across startup/smoke/native-picker/batch/imageboard suites).
- Completed third Phase 4 slice (2026-05-15):
  - extracted workspace `notes` and `data I/O` sections into `frontend/fragments/workspace/*`.
  - replaced inline workspace notes/I/O markup in `frontend/index.html` with `data-fragment` placeholders while preserving existing `x-if` guards.
  - focused regressions passed (`107` tests across startup/smoke/native-picker/imageboard/notes/export suites).
- Completed fourth Phase 4 slice (2026-05-15):
  - extracted the imageboard import modal into `frontend/fragments/modals/imageboard_import.html`.
  - replaced inline modal markup in `frontend/index.html` with `data-fragment="modals/imageboard_import"` under the existing `x-if="imageboardImport.show"` guard.
  - focused regressions passed (`99` tests, `6` skipped, across startup/smoke/native-picker/imageboard suites).
- Completed fifth Phase 4 slice (2026-05-15):
  - extracted workspace batch tools section into `frontend/fragments/workspace/batch.html`.
  - replaced inline batch markup in `frontend/index.html` with `data-fragment="workspace/batch"` under the existing `x-if="uiSection === 'workspace' && currentProject && mainView === 'batch'"` guard.
  - focused regressions passed (`115` tests across startup/smoke/native-picker/imageboard/batch suites).
- Completed sixth Phase 4 slice (2026-05-15):
  - extracted workspace project settings section into `frontend/fragments/workspace/project.html`.
  - replaced inline project-settings markup in `frontend/index.html` with `data-fragment="workspace/project"` under the existing `x-if="mainView === 'project'"` guard.
  - repaired malformed `frontend/index.html` structure encountered during extraction and restored the fragment-loader script bootstrap path.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed seventh Phase 4 slice (2026-05-15):
  - extracted the workspace `grid` + `editor` region into a temporary combined workspace fragment.
  - replaced the inline region in `frontend/index.html` with a combined workspace fragment placeholder while keeping `mainView === 'grid'` and `mainView === 'editor'` guards inside the fragment.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed eighth Phase 4 slice (2026-05-15):
  - split the temporary combined workspace fragment into `frontend/fragments/workspace/grid.html` and `frontend/fragments/workspace/editor.html`.
  - rewired `frontend/index.html` to use direct `data-fragment="workspace/grid"` and `data-fragment="workspace/editor"` placeholders and removed the combined fragment file.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed ninth Phase 4 slice (2026-05-15):
  - extracted the workspace view-toggle header bar into `frontend/fragments/workspace/view_header.html`.
  - replaced inline workspace shell header markup in `frontend/index.html` with `data-fragment="workspace/view_header"` while preserving existing Alpine bindings/classes.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed tenth Phase 4 slice (2026-05-15):
  - extracted the settings tab-switcher header into `frontend/fragments/settings/tab_header.html`.
  - restored settings-shell rendering by adding `data-fragment="settings/tab_header"` in `frontend/index.html` under the existing `uiSection === 'settings'` guard.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed eleventh Phase 4 slice (2026-05-15):
  - extracted the top app header bar into `frontend/fragments/shell/app_header.html`.
  - replaced inline root-template header markup in `frontend/index.html` with `data-fragment="shell/app_header"` while preserving Alpine bindings for backend health and settings toggle.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed twelfth Phase 4 slice (2026-05-15):
  - extracted the modal placeholder host block into `frontend/fragments/shell/modal_host.html`.
  - replaced inline root-template modal host markup in `frontend/index.html` with `data-fragment="shell/modal_host"` while preserving `imageboardImport.show` guard behavior.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed thirteenth Phase 4 slice (2026-05-15):
  - extracted the root workspace/settings content host into `frontend/fragments/shell/content_host.html`.
  - replaced inline root content-host markup in `frontend/index.html` with `data-fragment="shell/content_host"` and restored explicit `</main>` closure.
  - upgraded `frontend/js/core/fragments.js` to bounded multi-pass loading so nested placeholders resolve safely.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed fourteenth Phase 4 slice (2026-05-15):
  - performed a root-shell skeleton review pass for the consolidated shell-host structure.
  - normalized `frontend/fragments/shell/content_host.html` formatting/structure without behavior changes to reduce merge conflicts.
  - focused regressions passed (`43` tests across startup/smoke/native-picker/batch suites).
- Completed fifteenth Phase 4 slice (2026-05-15):
  - performed a compact fragment-manifest review pass across `frontend/index.html` + `frontend/fragments/**/*.html`.
  - verified parity: 18 referenced fragments and 18 fragment files, with no missing or unreferenced entries.
  - removed stale roadmap references to retired intermediate fragment naming.
- Completed sixteenth Phase 4 slice (2026-05-15):
  - reviewed and aligned fragment-loading cache/version suffixes between `frontend/js/core/fragments.js` and `frontend/index.html`.
  - replaced hardcoded fragment query text in the loader with a shared version constant and bumped both loader/script suffixes to `20260515b`.
  - no behavior changes expected; this is a consistency/operability maintenance pass.
- Completed seventeenth Phase 4 slice (2026-05-15):
  - added `tests/test_fragment_loader_phase4.py` as focused regression coverage for nested fragment placeholder resolution.
  - verifies the current nested placeholder topology requires multi-pass resolution and resolves fully within the loader's bounded `maxPasses` limit.
  - keeps behavior unchanged while hardening the fragment-loading contract.
- Completed eighteenth Phase 4 slice (2026-05-15):
  - executed a Phase 4 exit validation bundle (`node --check` on loader/app + focused startup/smoke/native-picker/batch/caption-batch pytest subset).
  - validation results: 43 passed, 1 warning; no regressions detected.
  - this keeps Phase 4 progression stable while remaining slices focus on guardrail and closure documentation.
- Completed nineteenth Phase 4 slice (2026-05-15):
  - extended `tests/test_fragment_loader_phase4.py` with a max-pass saturation guardrail test.
  - validates unresolved placeholders remain when synthetic topology depth exceeds `maxPasses`, and checks the loader overflow warning contract text.
  - targeted fragment-loader regression file passed (`2` tests).
- Completed twentieth Phase 4 slice (2026-05-15):
  - finalized Phase 4 fragment architecture docs with an explicit shell map and loader lifecycle snapshot.
  - verified stale intermediate fragment names are absent from active roadmap/audit entries.
  - locked a final Phase 4 closure checklist and queued the first Phase 5 follow-up item.

Phase 4 Final Architecture Snapshot (locked 2026-05-15):

- Root shell in `frontend/index.html`:
  - `shell/app_header`
  - `shell/sidebar`
  - `shell/content_host`
  - `shell/modal_host`
- Workspace/settings fragments currently hosted through shell map:
  - `workspace/home`, `workspace/project`, `workspace/view_header`, `workspace/grid`, `workspace/editor`, `workspace/batch`, `workspace/notes`, `workspace/io`
  - `settings/tab_header`, `settings/general`, `settings/presets`, `settings/imageboards`
  - `modals/keyboard_shortcuts`, `modals/imageboard_import`
- Loader lifecycle snapshot (`frontend/js/core/fragments.js`):
  - placeholders are resolved via bounded multi-pass loading (`maxPasses = 20`)
  - fragment URL versioning is centralized through `FRAGMENT_CACHE_VERSION`
  - Alpine boot is deferred until fragment injection completes
  - overflow/cycle saturation emits a deterministic warning message

Phase 4 Closure Checklist (locked):

- [x] Root shell decomposition completed with stable placeholder ownership.
- [x] Nested fragment resolution contract covered by focused regression tests.
- [x] Max-pass saturation guardrail behavior covered by focused regression tests.
- [x] Fragment manifest parity verified (referenced vs existing files).
- [x] Cache/version suffix alignment documented and implemented.
- [x] Focused Phase 4 validation bundle passed without regressions.
- [x] Stale intermediate fragment naming removed from active roadmap/audit entries.

First Phase 5 follow-up item queued:

1. Add one focused regression test ensuring Phase 5 caption-generation delegates in `frontend/app.js` remain strict module-required delegates (no inline fallback reintroduction).

Phase 5 follow-up progress:

- Completed Phase 5 follow-up 1 (2026-05-15):
  - added `tests/test_frontend_delegate_contract_phase5.py` to lock delegate contracts for `generateCaptionWithPreset`, `generateCaptionWithLLM`, and `generateCaptionWithTools`.
  - verifies each method delegates through `window.DescribeItFeatures.llm` and retains the expected module-unavailable error path.
  - prevents inline fallback drift by asserting delegate blocks do not contain direct API/fetch tokens.
- Completed Phase 5 follow-up 2 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` to cover backend/model discovery delegate contracts.
  - validates `availableModelsForBackend` and `loadLLMBackends` remain module-required delegates with safe-default fallback behavior.
  - keeps discovery flows protected from inline API/fetch fallback reintroduction.
- Completed Phase 5 follow-up 3 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` to lock preset CRUD delegate contracts.
  - validates `createPreset`, `updatePreset`, and `deletePreset` remain strict `window.DescribeItFeatures.llm` delegates with module-unavailable fallback behavior.
  - protects preset CRUD paths against inline API/fetch fallback drift.
- Completed Phase 5 follow-up 4 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with dedicated coverage for `loadLLMPresets` delegate contract.
  - validates strict `window.DescribeItFeatures.llm` delegation while preserving safe-default fallback behavior (`this.llm.presets = []` + module-unavailable error).
  - keeps preset-loading path protected from inline API/fetch fallback drift.
- Completed Phase 5 follow-up 5 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with helper-delegate safe-return coverage.
  - validates `selectedLLMBackend`, `selectedLLMModel`, and `availableModelsForBackend` preserve existing fallback contracts (`null`/`[]`) when module bindings are unavailable.
  - keeps helper delegate paths protected from inline API/fetch fallback drift.
- Completed Phase 5 follow-up 6 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with label-helper fallback coverage.
  - validates `modelCapabilityLabel` and `modelOptionLabel` preserve safe fallback contracts (`''` and `modelInfo?.name || ''`) when module bindings are unavailable.
  - keeps label helper paths protected from inline API/fetch fallback drift.
- Completed Phase 5 follow-up 7 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with dedicated `loadLLMBackends` startup/fallback contract coverage.
  - validates preserved fallback side effects (`this.llm.backends = []` + module-unavailable error) and strict delegate behavior.
  - adds duplicate-branch guards so fallback assignments/error path remain single-source in the method block.
- Completed Phase 5 follow-up 8 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with event-style delegate coverage.
  - validates `onLLMBackendChanged`, `onPresetBackendChanged`, and `onSelectedPresetChanged` remain strict llm-feature delegates with a single module-unavailable error path.
  - keeps event-style delegate paths protected from inline API/fetch fallback drift.
- Completed Phase 5 follow-up 9 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with helper-event delegate coverage for `pickDefaultLLMSelection` and `onModelVisibilityFilterChanged`.
  - validates strict llm-feature delegation with a single module-unavailable error path for each method block.
  - keeps helper-event delegate paths protected from inline API/fetch fallback drift.
- Completed Phase 5 follow-up 10 (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with preset-helper delegate coverage for `resetPresetForm` and `applyPresetToForm`.
  - validates strict delegation and single module-unavailable error path for both methods.
  - preserves `applyPresetToForm` argument pass-through contract (`applyPresetToForm(this, preset)`).
- Completed Phase 5 follow-up 11 (2026-05-15):
  - performed a contract-test consolidation pass by introducing shared helper assertions for event-style delegates.
  - reduced duplicate assertion blocks while preserving explicit fallback-contract and no-inline-API/fetch guarantees.
- Completed Phase 5 follow-up 12 (2026-05-15):
  - completed focused-contract closure for current LLM delegate surface.
  - documented covered delegate families, out-of-scope areas, and queued the next non-contract Phase 5 item.

Phase 5 non-contract follow-up progress:

- Completed Phase 5 non-contract follow-up 1 (2026-05-15):
  - added `tests/test_phase5_preset_selection_behavior.py` for preset-selection UX behavioral regression coverage.
  - verifies default preset auto-apply guards in `applyPresetPreference`, preset backend/model reselection behavior in `onPresetBackendChanged`, and stale-id reconciliation before reapplying preferences in `loadLLMPresets`.
  - focused behavioral suite passed (`3` tests).
- Completed Phase 5 non-contract follow-up 2 (2026-05-15):
  - extended `tests/test_phase5_preset_selection_behavior.py` with preset lifecycle consistency coverage for create/update/delete flows.
  - verifies selected preset continuity for create/update, reset+clear behavior for delete, and status-message contract strings for each flow.
  - focused behavioral suite passed (`4` tests).
- Completed Phase 5 non-contract follow-up 3 (2026-05-15):
  - extended `tests/test_phase5_preset_selection_behavior.py` with backend availability edge-case coverage for selection helpers.
  - verifies empty/backends-unavailable transitions in `pickDefaultLLMSelection`, safe defaults in `availableModelsForBackend`, and null-return behavior in `selectedLLMBackend`/`selectedLLMModel`.
  - focused behavioral suite passed (`5` tests).
- Completed Phase 5 non-contract follow-up 4 (2026-05-15):
  - performed compact behavioral-test consolidation in `tests/test_phase5_preset_selection_behavior.py` via shared helper assertions.
  - grouped assertions by UX flow and reduced duplicate marker checks while preserving behavior guarantees.
  - focused behavioral suite remained green (`5` tests).
- Completed Phase 5 non-contract follow-up 5 (2026-05-15):
  - completed Phase 5 non-contract closure for preset-selection behavioral coverage.
  - documented covered flows, intentionally out-of-scope areas, and queued the first Phase 6 planning item.

Phase 5 non-contract coverage summary (closed 2026-05-15):

- Covered behavioral flows:
  - default preset auto-apply guards (`applyPresetPreference`)
  - preset backend/model reselection logic (`onPresetBackendChanged`)
  - stale preset-id reconciliation before preference reapply (`loadLLMPresets`)
  - preset lifecycle continuity and status contracts (create/update/delete)
  - backend availability edge-cases for selection helpers (`pickDefaultLLMSelection`, `availableModelsForBackend`, `selectedLLMBackend`, `selectedLLMModel`)
- Intentionally out-of-scope for this non-contract pass:
  - cross-module UX flows outside LLM preset selection
  - async timing/race behavior requiring runtime event simulation
  - UI visual-state assertions/snapshots
- Next Phase 6 planning item queued:
  - draft a compact Phase 6 slice map for LLM UX hardening (error messaging consistency, optimistic status handling, and retry UX) with focused validation checkpoints.

## Phase 6 Plan: LLM UX Hardening (2026-05-15)

Objective:

- Improve user-facing resilience and clarity for LLM interactions without changing core backend API contracts.

Planned slices:

1. Slice A: Error messaging consistency
  - normalize common LLM error strings (backend unavailable, timeout, invalid preset/model selection) into a single helper path.
  - keep existing granular failure details available for debugging context.
2. Slice B: Optimistic status handling
  - standardize pending/success status messages across preset generation and direct generation flows.
  - ensure status messages are replaced/cleared deterministically on completion/failure.
3. Slice C: Retry UX guardrails
  - add lightweight retry affordance/state for transient fetch failures in backend/preset loading paths.
  - preserve current safe defaults when retries exhaust.
4. Slice D: Validation and closure
  - extend focused regression coverage for Phase 6 UX contracts.
  - run targeted startup/smoke/native-picker/batch/caption-batch regression subset before closing Phase 6.

Focused validation checkpoints per slice:

- JS syntax check: `node --check frontend/js/features/llm.js && node --check frontend/app.js`
- Focused frontend behavior tests:
  - `tests/test_frontend_delegate_contract_phase5.py`
  - `tests/test_phase5_preset_selection_behavior.py`
- Targeted regression subset after behavior-affecting slices:
  - `tests/test_startup_selection_regression.py`
  - `tests/test_smoke_e2e.py`
  - `tests/test_native_picker_api.py`
  - `tests/test_native_picker_service.py`
  - `tests/test_batch_regression.py`
  - `tests/test_caption_batch_phasec.py`

Phase 6 progress:

- Completed Phase 6 Slice A (2026-05-15):
  - implemented shared LLM UX error normalization in `frontend/js/features/llm.js` (`normalizeLlmUxErrorMessage`, `setLlmUxError`).
  - wired normalized error handling into `loadLLMBackends` and `loadLLMPresets` without API contract changes.
  - added focused regression coverage in `tests/test_phase6_llm_ux_hardening.py` and passed syntax + focused tests (`2` tests).

Phase 5 focused-contract coverage summary (closed 2026-05-15):

- Covered delegate families:
  - caption generation delegates (`generateCaptionWithPreset`, `generateCaptionWithLLM`, `generateCaptionWithTools`)
  - backend/model discovery delegates (`availableModelsForBackend`, `loadLLMBackends`)
  - label helpers (`modelCapabilityLabel`, `modelOptionLabel`)
  - preset lifecycle delegates (`loadLLMPresets`, `createPreset`, `updatePreset`, `deletePreset`)
  - event/helper delegates (`onLLMBackendChanged`, `onPresetBackendChanged`, `onSelectedPresetChanged`, `onModelVisibilityFilterChanged`, `pickDefaultLLMSelection`, `resetPresetForm`, `applyPresetToForm`)
- Intentionally out-of-scope for this focused contract pass:
  - non-LLM feature modules (projects/browser/editor/grid/batch/notes/export/import)
  - end-to-end UX behavior assertions beyond delegate/fallback contracts
  - visual/UI snapshot testing
- Next non-contract Phase 5 item queued:
  - add focused behavioral regression coverage for preset lifecycle consistency after create/update/delete flows (selected preset continuity, reset behavior, and status-message contract).

## Pull Request Guardrails

- Keep each PR focused to one extraction area.
- Preserve public API request/response shapes unless intentionally changed.
- Include targeted tests for backend/API behavior touched by frontend-driven changes.
- Do not introduce mandatory build steps for users.

## Optional Libraries (Allowed)

When needed, prefer small runtime-safe additions, such as:

- Alpine.js plugins
- small utility libraries loaded via CDN
- lightweight UI helper libraries that do not require bundling

If a library requires build output, commit generated assets so app startup remains Python-only.
