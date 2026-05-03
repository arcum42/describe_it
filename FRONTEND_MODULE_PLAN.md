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
