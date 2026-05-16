# Refactor and Duplication Audit (2026-05-15)

## Progress update (as of 2026-05-15)

Completed since this audit was created:
- Phase 1 complete:
  - Added shared project DB helpers in backend/services/project_db_utils.py.
  - Migrated repeated project path/project-record loading patterns in key services to shared helpers.
  - Promoted shared imageboard fetch_image_bytes behavior into backend/llm/imageboard/base.py and removed subclass duplicates in Derpibooru/Danbooru/E621/Twibooru clients.
  - Added optional complexity tooling and gate script (radon/xenon + scripts/check_complexity.sh).
- Phase 2 substantially complete:
  - Added backend/services/llm_generation_pipeline.py and routed context-overflow retry handling through it.
  - Further decomposed backend/services/llm_service.py by extracting shared runtime/config/context/tool-generation helpers.
  - Refactored backend/services/note_context_service.py into smaller helper functions to remove module-level Xenon blocker.
- Validation completed after refactors:
  - Focused regression suite: 109 passed.
  - Full regression suite: 181 passed, 6 skipped.
  - Complexity gate: passing (scripts/check_complexity.sh exit code 0).

## Scope and approach

I reviewed the repository for:
- Large files (line count and byte size)
- Duplicate code patterns
- Refactor opportunities (especially file-splitting)
- Python and JavaScript errors/diagnostics
- Places where existing libraries could reduce custom code

Checks run:
- Workspace diagnostics via editor diagnostics API (includes Pylance/Pyright diagnostics when available)
- Python syntax compile check: compileall on backend, tests, and run.py
- JavaScript parser check: node --check across JS files
- Heuristic duplicate scan for Python and JavaScript function/method blocks

## Error checking results

Status: no current syntax or static-analysis errors were found.

- Python: compileall completed successfully for backend, tests, run.py
- JavaScript: node --check completed successfully for JS files
- Editor diagnostics: no errors reported (this is where Pylance diagnostics would appear for Python files)

Note on Pylance files:
- No separate repository files specific to Pylance were identified in the workspace tree. Pylance findings are surfaced through diagnostics rather than project-owned files.

## Largest files (maintainability hotspots)

Top source/UI files by line count:
1. frontend/index.html (3174)
2. frontend/app.js (2547)
3. tests/test_imageboard_import.py (1240)
4. frontend/js/features/editor.js (1234)
5. backend/services/image_service.py (1185)
6. backend/services/llm_service.py (997)
7. tests/test_smoke_e2e.py (781)
8. backend/services/batch_service.py (730)

Top source files by bytes:
1. frontend/index.html (~239 KB)
2. frontend/app.js (~96 KB)
3. tests/test_imageboard_import.py (~45 KB)
4. backend/services/image_service.py (~42 KB)
5. frontend/js/features/editor.js (~42 KB)
6. backend/services/llm_service.py (~41 KB)

## High-value refactor opportunities

### 1) Split frontend state and action orchestration in frontend/app.js

Why this matters:
- describeItApp currently contains a very large monolithic state object and many delegated feature actions.
- This increases regression risk for seemingly small changes.

Evidence:
- frontend/app.js:1 contains the entire app object factory.
- Long methods include filteredGridCards at frontend/app.js:943 and project/navigation methods near frontend/app.js:702 and frontend/app.js:764.

Suggested refactor:
- Keep describeItApp as composition root only.
- Move state defaults into domain modules:
  - frontend/js/state/workspace-state.js
  - frontend/js/state/editor-state.js
  - frontend/js/state/llm-state.js
  - frontend/js/state/notes-state.js
- Move computed/view-model helpers into dedicated files:
  - frontend/js/view/grid-computed.js
  - frontend/js/view/editor-computed.js
- Keep feature delegates thin and consistently generated (or table-driven dispatcher) to reduce repetition.

Expected outcome:
- Smaller blast radius per feature change
- Easier test coverage for pure helpers
- Faster onboarding and code review

### 2) Break frontend/index.html into Alpine component fragments or template modules

Why this matters:
- index.html is currently the largest source file and contains many independent UI regions.

Evidence:
- frontend/index.html:1 onward includes sidebar, workspace home, editor views, settings, modals, and feature-specific panels in one file.

Suggested refactor (compatible with no mandatory Node build):
- Keep static-first delivery.
- Extract major sections into HTML partial fragments loaded at runtime (fetch + template injection) or web-component templates:
  - frontend/fragments/sidebar.html
  - frontend/fragments/workspace-home.html
  - frontend/fragments/editor-panel.html
  - frontend/fragments/settings-panel.html
  - frontend/fragments/modals.html
- Preserve Alpine bindings and IDs; add a lightweight fragment loader.

Expected outcome:
- Reduced merge conflicts
- Better parallel work across UI areas
- Simpler diff review for frontend changes

### 3) Factor shared LLM generation flow in backend/services/llm_service.py

Why this matters:
- Multiple long functions share nearly identical flow (settings load, context fetch, tool fallback, retry on context overflow, backend dispatch).

Evidence:
- Very long functions:
  - generate_text_for_image_with_preset at backend/services/llm_service.py:389
  - generate_caption_with_tools at backend/services/llm_service.py:603
  - generate_note_text_with_tools at backend/services/llm_service.py:814
- Repeated patterns for:
  - backend/model settings resolution
  - context injection assembly
  - tool-capability fallback
  - retry loop over _CONTEXT_RETRY_CHAR_BUDGETS

Suggested refactor:
- Introduce an internal generation pipeline module, for example:
  - backend/services/llm_generation_pipeline.py
- Extract reusable units:
  - resolve_backend_runtime_config(...)
  - build_injected_context(...)
  - run_generation_with_context_retries(...)
  - run_model_generation(...)
- Keep public service API signatures stable while delegating internals.

Expected outcome:
- Reduced duplication
- Easier bug fixes (single retry/fallback logic path)
- Better unit-test granularity

### 4) Centralize duplicated project-path helpers in backend services

Why this matters:
- Path resolution/project-load boilerplate is repeated across service modules.

Evidence:
- Repeated _resolve_path helpers:
  - backend/services/caption_service.py:12
  - backend/services/caption_batch_service.py:32
  - backend/services/note_service.py:30
  - backend/services/export_service.py:70
  - backend/services/import_service.py:38
  - backend/services/image_service.py:61
- Repeated _load_project patterns:
  - backend/services/caption_batch_service.py:39
  - backend/services/note_service.py:58
  - backend/services/image_service.py:68

Suggested refactor:
- Add backend/services/project_db_utils.py with shared helpers:
  - resolve_project_path(...)
  - require_project_record(...)
  - with_project_session(...)
- Migrate services incrementally to avoid large risky rewrite.

Expected outcome:
- Less boilerplate and fewer subtle inconsistencies
- More consistent error messages and path handling

### 5) Reduce duplication across imageboard clients

Why this matters:
- Client implementations for Derpibooru, Danbooru, e621, and Twibooru share structure and utility logic.

Evidence:
- Repeated fetch_image_bytes implementations:
  - backend/llm/imageboard/derpibooru.py:185
  - backend/llm/imageboard/danbooru.py:182
  - backend/llm/imageboard/e621.py:241
  - backend/llm/imageboard/twibooru.py:185
- Similar search/get_image_details boilerplate with board-specific parameter differences.

Suggested refactor:
- Promote a richer shared base client in backend/llm/imageboard/base.py:
  - default fetch_image_bytes implementation
  - shared search request lifecycle template
- Keep only board-specific mapping/parsing in subclasses.

Expected outcome:
- Fewer bug-prone copy/paste updates
- Easier addition of new boards

## Additional decomposition candidates

- backend/services/image_service.py (1185 lines): split by operation family
  - listing/detail/read models
  - duplicate detection
  - transform ops (crop/scale/flip/rotate/extract)
  - cleanup workflows
- backend/services/batch_service.py (730 lines): split persistence, scheduler/orchestrator, job result aggregation
- frontend/js/features/editor.js (1234 lines): split image tools, caption tools, tag mode, and selection/navigation glue
- tests/test_imageboard_import.py (1240 lines): split by board/provider and import workflow stage to improve failure locality

## Library opportunities to reduce custom code

These are optional improvements; use requirements-optional.txt unless needed for baseline startup.

1) Retry and backoff simplification
- Current: custom retry/backoff branches in backend/llm/imageboard/http_client.py:95 and backend/llm/imageboard/http_client.py:204.
- Candidate: tenacity (or backoff) for declarative retry rules.
- Benefit: smaller code, clearer retry policy, fewer edge-case branches.

2) Declarative HTTP API clients
- Current: manual response parsing and request plumbing in each imageboard client.
- Candidate: pydantic models for API responses and/or typed wrappers (still using httpx).
- Benefit: validation and stronger contracts, less repeated dict defensive coding.

3) Frontend templating/partial rendering helper
- Current: very large single HTML document with many repeated panel patterns.
- Candidate: lit-html, petite-vue, or tiny runtime template loader (no build required).
- Benefit: major HTML file-size reduction and cleaner component boundaries.

4) Path/session helper utility module instead of repeated ad hoc helpers
- Current: repeated _resolve_path/_load_project logic in many services.
- Candidate: internal shared utility module (no third-party dependency required).
- Benefit: lower maintenance, consistent behavior.

5) Optional complexity tooling for CI quality gates
- Candidate: radon/xenon for complexity thresholds on Python hotspots.
- Benefit: prevents new monolithic growth after refactor.

## Prioritized implementation plan

### Phase 1 (low risk, high leverage) - Completed
1. Create backend/services/project_db_utils.py and migrate one service at a time (caption_service, note_service first).
2. Add shared fetch_image_bytes implementation in imageboard base client and remove subclass duplicates.
3. Add CI-level complexity reporting (optional dependency) and baseline thresholds.

Deliverable:
- Reduced helper duplication without API changes.

### Phase 2 (medium risk) - In progress (majority completed)
1. Extract llm generation internals into llm_generation_pipeline.py. Completed.
2. Keep public functions in llm_service.py as stable wrappers. Completed.
3. Add focused unit tests around retry/fallback/context-injection behavior. Partially covered by focused + full regression runs; additional direct unit tests for extracted helpers are still recommended.

Deliverable:
- llm_service.py reduced substantially with equivalent behavior.

### Phase 3 (medium/high risk) - Not started
1. Split frontend app state defaults into domain modules.
2. Move heavy computed helpers out of app.js.
3. Introduce a small dispatcher pattern for feature delegates.

Deliverable:
- app.js becomes orchestration glue, not primary implementation surface.

### Phase 4 (high-impact UI maintainability) - Not started
1. Decompose index.html into major fragments.
2. Add a minimal fragment loader preserving Alpine lifecycle order.
3. Regression test key workflows (project open, image edit, batch, notes, settings).

Deliverable:
- Much smaller index.html and fewer merge conflicts.

### Phase 5 (ongoing hygiene) - Ongoing
1. Split large tests into scenario-focused files.
2. Add per-module ownership notes in docs (which file owns which behavior).
3. Re-run duplicate scan periodically and fail CI if duplication exceeds threshold.

## Updated next steps

1. Complete the remaining Phase 2 test hardening. Completed (2026-05-15):
  - added direct unit tests around backend/services/llm_generation_pipeline.py helper behavior (overflow detection, prompt truncation, retry progression) in tests/test_llm_generation_pipeline.py.
2. Continue Phase 2 hardening. Completed (2026-05-15):
  - added targeted llm_service helper-path tests in tests/test_llm_service_helpers.py (tool-capability downgrade, runtime config resolution, preset config wiring, and note-context helper constraints).
3. Start Phase 3 frontend modularization in a narrow first slice. Started (2026-05-15):
  - extracted notes default state from frontend/app.js into frontend/js/state/notes-state.js and wired app initialization to consume modular state with fallback behavior.
4. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted batch domain default state from frontend/app.js into frontend/js/state/batch-state.js (caption batch, caption text edit job state, and batch-run state) and wired app initialization to consume modular state with fallback behavior.
5. Focused regression validation after Phase 3 slices. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + state modules) and focused regression suite passed (57 tests).
6. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted grid filter default state from frontend/app.js into frontend/js/state/grid-state.js and moved filtered grid computed logic into frontend/js/features/grid.js with app-level delegation.
7. Focused regression validation for grid extraction. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + grid feature + grid state module) and focused regression suite passed (30 tests).
8. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted editor zoom/navigation computed helpers from frontend/app.js into frontend/js/features/editor.js with app-level delegation.
9. Focused regression validation for editor extraction. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + editor feature module) and focused regression suite passed (34 tests).
10. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted project/session + workspace navigation helpers from frontend/app.js into frontend/js/features/projects.js with app-level delegation.
11. Focused regression validation for project/session extraction. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + projects feature module) and focused regression suite passed (32 tests).
12. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted UI shell toggles/panel helpers (keyboard help, tab helpers, panel open/close state) from frontend/app.js into frontend/js/features/ui-shell.js with app-level delegation.
13. Focused regression validation for UI shell extraction. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + ui-shell feature module) and focused regression suite passed (32 tests).
14. Continue Phase 3 modularization. Completed slice (2026-05-15):
  - extracted native path-picker + browser selection glue helpers from frontend/app.js into frontend/js/features/browser.js with app-level delegation.
15. Focused regression validation for native-picker extraction. Completed (2026-05-15):
  - frontend syntax checks passed (app.js + browser feature module) and focused regression suite passed (37 tests, including native picker API/service coverage).
16. Begin Phase 4 lightweight design spike. Completed (2026-05-15):
  - defined fragment boundaries and Alpine-safe loader lifecycle constraints for frontend/index.html in FRONTEND_MODULE_PLAN.md (Phase 4 spike section).
17. Start Phase 4 implementation with one low-risk slice. Completed (2026-05-15):
  - added frontend/js/core/fragments.js pre-Alpine loader and extracted sidebar/workspace-home/keyboard-shortcuts sections into static fragments; focused startup/smoke/native-picker regressions passed (35 tests).
18. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted settings tabs (general + presets + imageboards) into `frontend/fragments/settings/*` with `frontend/index.html` placeholders, preserving script order and modal behavior.
19. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted workspace notes + data I/O sections into `frontend/fragments/workspace/*` with `frontend/index.html` placeholders; focused startup/smoke/native-picker/imageboard/notes/export regressions passed (107 tests).
20. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted imageboard import modal into `frontend/fragments/modals/imageboard_import.html` with `frontend/index.html` placeholder, preserving `@keydown.escape.window` behavior and modal state wiring.
21. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted workspace batch tools section into `frontend/fragments/workspace/batch.html` with `frontend/index.html` placeholder; focused startup/smoke/native-picker/imageboard/batch regressions passed (115 tests).
22. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the workspace project settings section (`mainView === 'project'`) into `frontend/fragments/workspace/project.html` and replaced the inline block in `frontend/index.html` with a fragment placeholder under the existing `x-if` guard.
  - while implementing the slice, repaired malformed `frontend/index.html` structure and restored the pre-Alpine fragment-loader bootstrap script include.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
23. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the workspace grid/editor region into a temporary combined workspace fragment and replaced the inline region in `frontend/index.html` with a combined workspace placeholder.
  - preserved existing `mainView === 'grid'` and `mainView === 'editor'` ownership boundaries inside the extracted fragment.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
24. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - split the temporary combined workspace fragment into dedicated `frontend/fragments/workspace/grid.html` and `frontend/fragments/workspace/editor.html` fragments.
  - replaced the combined placeholder in `frontend/index.html` with direct `workspace/grid` and `workspace/editor` placeholders while preserving wrapper closures in the root template.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
25. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the workspace view-toggle header bar (Project/Grid/Editor/Batch/Notes/Data I/O controls) into `frontend/fragments/workspace/view_header.html`.
  - replaced the inline header markup in `frontend/index.html` with `data-fragment="workspace/view_header"` while preserving active-view state classes and running-status text.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
26. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the settings tab-switcher header (General/Presets/Imageboards controls) into `frontend/fragments/settings/tab_header.html`.
  - restored settings-shell rendering in `frontend/index.html` by inserting `data-fragment="settings/tab_header"` under the `uiSection === 'settings'` guard.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
27. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the top app header bar (`describe_it` title + backend health + settings toggle button) into `frontend/fragments/shell/app_header.html`.
  - replaced the inline header block in `frontend/index.html` with `data-fragment="shell/app_header"` while preserving health/status bindings and settings-toggle behavior.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
28. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the modal placeholder host block (keyboard shortcuts + imageboard import modal placeholders) into `frontend/fragments/shell/modal_host.html`.
  - replaced the inline modal host block in `frontend/index.html` with `data-fragment="shell/modal_host"` while preserving `imageboardImport.show` visibility wiring.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
29. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - extracted the root workspace/settings content host (`<section class="space-y-6">` and top-level view guards) into `frontend/fragments/shell/content_host.html`.
  - replaced inline root content-host markup in `frontend/index.html` with `data-fragment="shell/content_host"` and restored explicit root `</main>` closure.
  - updated `frontend/js/core/fragments.js` loader to resolve nested placeholders via bounded multi-pass loading.
  - focused startup/smoke/native-picker/batch regressions passed (43 tests).
30. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - completed a root-shell skeleton review pass after consolidating `shell/content_host` responsibilities.
  - normalized `frontend/fragments/shell/content_host.html` structure/indentation without behavior changes to reduce future merge friction.
  - re-ran focused startup/smoke/native-picker/batch regressions (43 passed).
31. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - performed a compact fragment-manifest review pass across `frontend/index.html` + `frontend/fragments/**/*.html`.
  - verified parity: 18 referenced fragments and 18 fragment files, with no missing or unreferenced entries.
  - removed stale roadmap references to retired intermediate fragment naming.
32. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - completed a lightweight cache/version review for fragment-loading assets (`frontend/js/core/fragments.js` and `frontend/index.html`).
  - aligned the fragment URL suffix and loader script suffix to the same revision token (`20260515b`) and replaced loader-side hardcoded query text with a shared constant.
  - verified no behavior changes in fragment placeholder inventory expectations.
33. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - added focused regression coverage in `tests/test_fragment_loader_phase4.py` for the bounded multi-pass fragment-loader behavior.
  - test verifies nested `data-fragment` placeholders remain after one pass and then fully resolve within the loader `maxPasses` bound.
  - validated current fragment topology remains acyclic/resolvable for root placeholders defined in `frontend/index.html`.
34. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - ran a compact docs consistency sweep for Phase 4 slice numbering/naming across `FRONTEND_MODULE_PLAN.md`, `REFACTOR_AUDIT_2026-05-15.md`, and `/memories/repo/notes.md`.
  - corrected `FRONTEND_MODULE_PLAN.md` progression drift by restoring the missing fifteenth-slice manifest cleanup entry and renumbering subsequent entries to sixteenth/seventeenth.
  - added an explicit remaining-step backlog for Phase 4 with a defined closure step.
35. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - ran Phase 4 exit validation bundle:
    - `node --check frontend/js/core/fragments.js && node --check frontend/app.js` (passed)
    - focused pytest subset: `tests/test_startup_selection_regression.py`, `tests/test_smoke_e2e.py`, `tests/test_native_picker_api.py`, `tests/test_native_picker_service.py`, `tests/test_batch_regression.py`, `tests/test_caption_batch_phasec.py` (43 passed, 1 warning).
  - no regressions detected from recent Phase 4 doc/test hardening slices.
36. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - added focused fragment-loader guardrail coverage in `tests/test_fragment_loader_phase4.py` for max-pass saturation behavior.
  - new test validates that an over-deep synthetic placeholder chain remains unresolved after `maxPasses` iterations and confirms warning text presence in `frontend/js/core/fragments.js`.
  - targeted test file passed (`2 passed`).
37. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - completed final fragment architecture docs pass in `FRONTEND_MODULE_PLAN.md` with a locked shell map and loader lifecycle snapshot.
  - verified stale intermediate fragment naming is absent in active roadmap/audit entries.
  - confirmed fragment-loader contract documentation now explicitly includes bounded multi-pass behavior, centralized version suffix constant, and deferred Alpine boot ordering.
38. Continue Phase 4 implementation with next low-risk slice. Completed (2026-05-15):
  - finalized and locked Phase 4 closure checklist in `FRONTEND_MODULE_PLAN.md`.
  - recorded Phase 4 completion summary: shell decomposition done, manifest parity and cache/version alignment verified, and focused validation/guardrail tests green.
  - queued first Phase 5 follow-up item for delegate-contract regression protection.
39. Phase 5 follow-up (queued). Completed (2026-05-15):
  - added `tests/test_frontend_delegate_contract_phase5.py` with focused contract coverage for `generateCaptionWithPreset`, `generateCaptionWithLLM`, and `generateCaptionWithTools` in `frontend/app.js`.
  - test asserts each method remains a strict `window.DescribeItFeatures.llm` delegate with the expected module-unavailable error path.
  - test also guards against inline fallback reintroduction by rejecting inline API/fetch tokens in the delegate method blocks.
  - targeted regression passed (`1 passed`).
40. Phase 5 follow-up (queued). Completed (2026-05-15):
  - added backend/model discovery delegate contract coverage to `tests/test_frontend_delegate_contract_phase5.py`.
  - aligned the follow-up to current method names in `frontend/app.js` (`availableModelsForBackend`, `loadLLMBackends`) and verified module-required delegate wiring plus safe-default fallbacks (`return []`, `this.llm.backends = []`).
  - test also guards against inline API/fetch fallback reintroduction in these discovery method blocks.
  - targeted regression passed (`2 passed`).
41. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused contract coverage for `createPreset`, `updatePreset`, and `deletePreset` in `frontend/app.js`.
  - test verifies each method remains a strict `window.DescribeItFeatures.llm` delegate with module-unavailable fallback path.
  - test guards against inline API/fetch fallback reintroduction in preset CRUD delegate method blocks.
  - targeted regression passed (`3 passed`).
42. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused contract coverage for `loadLLMPresets` in `frontend/app.js`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation and preserves safe-default fallback behavior (`this.llm.presets = []` + module-unavailable error).
  - test guards against inline API/fetch fallback reintroduction in the `loadLLMPresets` method block.
  - targeted regression passed (`4 passed`).
43. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with helper-delegate safe-return contract coverage for `selectedLLMBackend`, `selectedLLMModel`, and `availableModelsForBackend`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation paths and preserved fallback contracts (`null` for selected backend/model and `[]` for available models).
  - test guards these helper method blocks against inline API/fetch fallback reintroduction.
  - targeted regression passed (`5 passed`).
44. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused label-helper fallback contract coverage for `modelCapabilityLabel` and `modelOptionLabel`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation paths and preserved safe fallback contracts (`''` and `modelInfo?.name || ''`).
  - test guards these helper method blocks against inline API/fetch fallback reintroduction.
  - targeted regression passed (`6 passed`).
45. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with dedicated startup/fallback contract coverage for `loadLLMBackends`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation path and preserves current fallback side effects (`this.llm.backends = []` and module-unavailable error).
  - test adds duplicate-branch guard checks to ensure fallback assignments/messages are not duplicated within the method block.
  - targeted regression passed (`7 passed`).
46. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused event-style delegate contract coverage for `onLLMBackendChanged`, `onPresetBackendChanged`, and `onSelectedPresetChanged`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation paths and enforces a single module-unavailable error assignment per method block.
  - test guards these event-style delegate method blocks against inline API/fetch fallback reintroduction.
  - targeted regression passed (`8 passed`).
47. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused helper-event delegate coverage for `pickDefaultLLMSelection` and `onModelVisibilityFilterChanged`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation paths and enforces a single module-unavailable error assignment per method block.
  - test guards these helper method blocks against inline API/fetch fallback reintroduction.
  - targeted regression passed (`9 passed`).
48. Phase 5 follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_frontend_delegate_contract_phase5.py` with focused preset-helper delegate contract coverage for `resetPresetForm` and `applyPresetToForm`.
  - test verifies strict `window.DescribeItFeatures.llm` delegation paths, single module-unavailable error assignment, and argument pass-through preservation for `applyPresetToForm(this, preset)`.
  - targeted regression passed (`10 passed`).
49. Phase 5 follow-up (queued). Completed (2026-05-15):
  - performed contract-test consolidation in `tests/test_frontend_delegate_contract_phase5.py` by introducing shared helper `_assert_llm_event_delegate_contract` for event-style delegate assertions.
  - reduced duplicate assertion blocks while preserving explicit fallback-contract checks and no-inline-API/fetch guardrails.
  - focused suite remained green after consolidation (`10 passed`).
50. Phase 5 follow-up (queued). Completed (2026-05-15):
  - completed Phase 5 contract-coverage closure summary with covered delegate families and intentionally out-of-scope areas.
  - locked the focused-contract backlog for current LLM delegate surface and queued the first non-contract Phase 5 improvement item.
51. Phase 5 non-contract follow-up (queued). Completed (2026-05-15):
  - added `tests/test_phase5_preset_selection_behavior.py` with focused behavioral regression coverage for preset selection UX flow.
  - coverage locks: default preset auto-apply guards (`applyPresetPreference`), preset backend/model reselection behavior (`onPresetBackendChanged`), and stale-id reconciliation before preference reapply (`loadLLMPresets`).
  - targeted behavioral suite passed (`3 passed`).
52. Phase 5 non-contract follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_phase5_preset_selection_behavior.py` with focused preset lifecycle consistency coverage for create/update/delete flows.
  - test verifies selected preset continuity for create/update, reset+clear behavior for delete, and status-message contract strings for each flow.
  - targeted behavioral suite passed (`4 passed`).
53. Phase 5 non-contract follow-up (queued). Completed (2026-05-15):
  - extended `tests/test_phase5_preset_selection_behavior.py` with backend availability edge-case coverage in selection helpers.
  - test verifies empty/backends-unavailable transitions in `pickDefaultLLMSelection`, safe defaults in `availableModelsForBackend`, and null-return behavior in `selectedLLMBackend`/`selectedLLMModel`.
  - targeted behavioral suite passed (`5 passed`).
54. Phase 5 non-contract follow-up (queued). Completed (2026-05-15):
  - performed compact behavioral-test consolidation in `tests/test_phase5_preset_selection_behavior.py` via shared helper assertions (`_llm_feature_text`, `_assert_contains_all`).
  - kept assertions grouped by UX flow while reducing duplicate marker-check patterns.
  - focused suite remained green after consolidation (`5 passed`).
55. Phase 5 non-contract follow-up (queued). Completed (2026-05-15):
  - completed Phase 5 non-contract closure summary with covered behavioral flows and intentionally out-of-scope areas.
  - locked the non-contract backlog for current preset-selection scope and queued first Phase 6 planning/refinement item.
56. Phase 6 planning follow-up (queued). Completed (2026-05-15):
  - drafted a compact Phase 6 LLM UX hardening slice map in `FRONTEND_MODULE_PLAN.md`.
  - defined slices for error-message consistency, optimistic status handling, retry UX guardrails, and validation closure.
  - documented focused validation checkpoints (JS syntax, focused behavioral tests, and targeted regression subset).
57. Phase 6 implementation follow-up (queued). Completed (2026-05-15):
  - implemented Slice A (error messaging consistency) in `frontend/js/features/llm.js` via shared helpers `normalizeLlmUxErrorMessage` and `setLlmUxError`.
  - wired helper usage into core LLM loading paths (`loadLLMBackends`, `loadLLMPresets`) without changing backend API contracts.
  - added focused regression coverage in `tests/test_phase6_llm_ux_hardening.py` for normalization rules and helper wiring.
  - validation checkpoints passed: JS syntax checks + focused Phase 6 test (`2 passed`).
58. Phase 6 implementation follow-up (queued):
  - implement Slice B (optimistic status handling): standardize pending/success/failure status transitions for preset generation and direct generation flows.
