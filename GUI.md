# describe_it GUI Reference (Current Implementation)

Last verified: 2026-05-02

This is a current-state reference of what the GUI actually does today. It is intended to support redesign planning by separating implemented behavior from desired future behavior.

## 1. Runtime and UI architecture

- Frontend is static HTML/CSS/JS served by FastAPI from frontend/.
- UI state is Alpine.js-based, rooted at describeItApp() in frontend/app.js.
- Core features are split into modules under frontend/js/features/ and delegated from app.js.
- Backend API is mounted under /api and includes routers for projects, images, captions, llm, notes, and global_notes.

## 2. High-level page layout

The UI has three persistent areas:

1. Top bar
- Left: app identity ("describe_it" + "Dataset Captioning Workbench").
- Right: backend health badge (healthLabel), and a toggle button that switches between:
	- Workspace view
	- Settings view

2. Left sidebar
- No-project mode: compact app status/help and filesystem browser access.
- Project-open mode: current project metadata and close/switch controls.
- Filesystem browser for selecting directories and DB files.
- Global status and error message area.
- Recent projects list.

3. Main content area
- Workspace mode: tabbed work surface.
- Settings mode: full settings panel replaces workspace tabs.

## 3. Global behavior and view state

### 3.1 Startup behavior

On app init, the UI does all of the following:

- Checks backend health.
- Loads project session state (last project path, reopen preference).
- Loads filesystem browser context.
- Attempts to auto-open last project if enabled.
- In parallel loads: recent projects, LLM backends, settings, presets, global notes, and RAG status.

### 3.2 Main state flags and navigation

- uiSection controls top-level mode:
	- workspace
	- settings
- mainView controls workspace tab:
	- grid, editor, batch, notes, io

### 3.3 Guardrails and disabled states

- Editor tab is disabled when no image is selected.
- Data I/O tab is available only when a project is open.
- Many actions are disabled while operations are active.
- Closing a project prompts confirmation if active-caption edits are unsaved.

## 4. Sidebar: project and filesystem controls

### 4.1 No project open state

The sidebar is intentionally compact.

- Small app-status/help panel
- Filesystem browser access
- Global status/error area

Primary Create/Open/Recent workflows are now rendered in Home mode in the main content area.

### 4.2 Project open state

The sidebar shows Current Project and metadata editing:

- name
- description
- trigger word
- caption mode (description or tags)
- project context URL
- project context file path

It also includes:

- Close project button
- Collapsible switch-project section with DB path input

### 4.3 Filesystem browser

Collapsible browser with:

- current path display
- refresh and "up" navigation
- root shortcuts
- directory list
- DB file list (.db)

Contextual actions:

- choose folder for project creation
- choose DB file for opening project
- choose folder for export destination (via tab workflow)

### 4.4 Recent projects

- Displays tracked projects and highlights current open one.
- Clicking a recent project opens/switches to it.

## 5. Workspace tabs (implemented behavior)

## 5.1 Grid tab

Purpose:
- Project-wide image overview and selection.

Content:
- Summary cards: total images, images with captions, blank captions.
- Responsive card grid with thumbnail, filename/status, caption preview.

Behavior:
- Clicking an image selects it and switches to Editor.
- Empty-state messaging appears if no images are available.

## 5.2 Editor tab

Purpose:
- Single-image caption editing and generation workflow.

Sections:

1. Image display and metadata
- Image preview, filename, dimensions.
- Included/Excluded toggle per image.

2. LLM Caption Generator
- Backend/model selection.
- Vision-model filtering (show all models toggle).
- Preset selector or manual mode.
- Extra instructions.
- Context and Tools accordion:
	- web_search
	- web_fetch
	- context URL
	- context file path
	- include project notes
	- include global notes
	- reasoning mode
	- reasoning output formatting
- Generation actions:
	- Generate Manual Caption
	- Generate With Preset
	- Generate with Tools
- Optional "set generated caption as active" toggle.

3. Active Caption editor
- Editable textarea for active caption.
- Save Active Caption action.

4. Caption Candidates
- List of candidate captions with source + active marker.
- Actions per candidate:
	- set active
	- edit
	- delete
- Add new caption candidate:
	- add and activate
	- add as candidate

## 5.3 Batch tab

Purpose:
- Run caption generation across multiple images with job tracking.

Configuration:

- target set (included, uncaptioned included, all)
- use preset toggle
- output mode:
	- new candidate
	- replace active
	- append active
- retry count
- skip on failure
- if using preset: preset picker
- if manual mode: backend/model/extra instructions/reasoning
- optional "set generated caption as active"

Execution controls:

- Start
- Pause
- Resume
- Cancel

Monitoring:

- progress bar and counters
- current image preview and filename
- latest generated text
- last error
- job history with status filter
- per-image result table
- CSV export for selected job results

## 5.4 Notes tab

Purpose:
- Manage reusable textual context and optional AI-assisted note drafting.

Key model:

- Two scopes in one screen:
	- Project Notes
	- Global Notes

Features:

- Scope toggle and "include archived" filter.
- Notes list panel with selection and new-note creation.
- Note editor:
	- title
	- format (markdown/text)
	- tags
	- content
	- archived flag
	- save/delete/new draft

LLM Note Assistant:

- backend/model selection
- output format
- prompt input
- optional title/tags
- optional context URL/file
- optional tool usage (web_search/web_fetch)
- optional notes inclusion toggles
- optional selected image attachment
- reasoning mode/output
- actions:
	- generate draft
	- generate and save new note

## 5.5 Data I/O tab

Purpose:
- Import and export workflows in one screen.

Layout:

- Import and Export cards shown together (side-by-side on wide screens, stacked on smaller screens).

Import controls:

- source folder path
- replace existing images toggle
- import action button

Export controls:

- output folder (with sidebar browser assist)
- create new subfolder + optional folder name
- included-only filter
- apply project trigger word
- include export manifest metadata
- include project notes as files
- overwrite existing files
- clean output folder

Export flow:

- Request export preview
- Review preview stats and overwrite warnings
- Run export

## 6. Settings view (separate from tabs)

Settings is not a workspace tab. It is a separate uiSection opened from the top-right button.

Settings sub-tabs:

- General
- Presets

General panels:

1. LLM Defaults
- global timeout
- use preset by default
- default preset

2. Ollama
- base URL
- test connection
- optional timeout override
- optional context window override

3. LM Studio
- base URL
- test connection
- optional timeout override
- optional context window override

4. Project Behavior
- reopen last project on startup

5. Debug (collapsible)
- RAG availability and rebuild embeddings action
- backend diagnostics with online/offline and model counts

Presets panel:

- Preset list and selection
- Create/Edit form fields:
	- name
	- backend
	- model
	- caption mode strategy (auto/description/tags)
	- prompt template
	- tool toggles (web_search/web_fetch)
	- include project/global notes
	- reasoning mode and output
	- context URL template
	- context file template
- Supported placeholders are shown in-UI
- Actions:
	- create
	- update
	- delete
	- reset to new draft

Actions:

- Save Settings
- Back To Workspace

## 7. API surface by UI area

High-level endpoint families used by the GUI:

- Health: /api/health
- Projects: /api/projects/recent, /session-state, /browser, /create, /open, /update, /import-folder, /export, /export-preview
- Images: /api/images/summary, /list, /{id}, /{id}/content, /{id}/included
- Captions: /api/captions/update-active, /create, /set-active, /update, /delete
- LLM: /api/llm/backends, /test-connection, caption generation endpoints, presets CRUD, batch job lifecycle, RAG status/rebuild/search, settings
- Notes: /api/notes (CRUD)
- Global Notes: /api/global-notes (CRUD)

## 8. Accuracy notes vs original brief

What the original brief captured correctly:

- The major workspace tabs and their broad purpose.
- Sidebar focus on project management.

What was missing or needed correction:

- Settings is a separate top-level view, not one of the workspace tabs.
- Sidebar also contains a filesystem browser and metadata editor with caption mode/trigger/context fields.
- Notes is a unified Project vs Global notes workspace, not just a single note area.
- Editor and Batch both have expanded tool/reasoning/context controls.
- Export includes preview and multiple safety/options toggles.
- Startup behavior includes session restore and optional auto-reopen.

## 9. Redesign implications

If this is used as a redesign baseline, treat these as existing behavior contracts unless intentionally changed:

- One-page, sidebar + main workbench mental model.
- Explicit project-open dependency for import/export and most editing flows.
- Candidate-based caption workflow (active caption plus alternatives).
- Notes as reusable context for LLM features.
- Preset-centric and manual LLM paths coexisting.
- Long-running batch operations with resumable job state and historical visibility.

## 10. Redesign plan v1 (feature-complete baseline)

This section proposes a redesign direction that keeps all current capabilities while improving flow and discoverability.

Design principles for this redesign:

- Keep behavior parity first, then improve layout and workflows.
- Keep Python-only runtime and static frontend delivery.
- Preserve safe data handling (no destructive defaults).
- Reduce tab sprawl by grouping related workflows.

## 11. Proposed information architecture

### 11.1 Top-level modes

1. Home (no project open)
- Main canvas shows:
	- Create Project
	- Open Project
	- Recent Projects
	- Optional "quick tips" and project browser launcher
- Sidebar is minimized to lightweight app status/help when no project is open.

2. Workspace (project open)
- Main tabs:
	- Library
	- Captions
	- Batch
	- Notes
	- Data I/O
- Settings remains a separate top-level mode from header button.

3. Settings
- Tabs inside Settings:
	- LLM Connections
	- Presets (moved from workspace LLM tab)
	- Defaults
	- Project Behavior
	- Debug

### 11.2 Sidebar rethink

When a project is open, sidebar becomes project operations only:

- Current project card (name/path/status)
- Project actions:
	- Close project
	- Switch project
	- Open filesystem browser drawer
- Project metadata editor (name, description, trigger word, caption mode, context URL/file)
- Compact status/error panel

When no project is open:

- Hide metadata and close/switch controls.
- Keep only compact app info and optional filesystem browser trigger.
- Primary create/open actions move to Home main content (not sidebar).

## 12. Feature mapping (current -> redesigned)

This mapping keeps all current features available:

- Grid + Single Image Editor -> Library
- LLM single-image generation controls -> Captions (single-image panel)
- LLM batch generation jobs -> Batch
- Notes and note assistant -> Notes
- Import + Export -> Data I/O (single combined tab with two panels)
- LLM Preset Manager -> Settings / Presets

## 13. New capabilities requested (planned)

### 13.1 Image editing capabilities

Add a non-destructive Image Tools panel under Library.

Planned operations:

1. Duplicate image
- Creates a new image record with copied bytes and inherited active caption/candidates policy.

2. Delete image
- Soft-delete by default, with an explicit permanent delete action.

3. Crop
- Rectangular crop with preview and apply.

4. Scale
- Resize by percent and/or target width/height, with aspect lock.

5. Extract region as new image
- Draw rectangle over source image and create a new image from selected region.
- Default carry-over is all caption candidates from the source image.

Data safety model:

- Preserve original imported bytes.
- Store edit outputs as derived images with lineage metadata:
	- source_image_id
	- operation_type
	- operation_params (JSON)
- Never overwrite the original image bytes in place.

### 13.2 Batch caption text operations

Add caption maintenance tools under Captions and optionally Batch:

1. Find and replace
- Scope options:
	- active captions only
	- all candidates
	- included images only
	- selected subset
- Modes:
	- plain text
	- regex
	- case sensitive toggle
- Preview first, then apply.

2. Bulk transforms (phase 2)
- trim whitespace
- normalize punctuation spacing
- prepend/append token
- deduplicate repeated tags (tags mode)

3. Safety
- show impacted caption count before apply
- multi-step undo history for bulk operations

## 14. Data I/O merge plan

Replace separate Import and Export tabs with one Data I/O tab:

- Left panel: Import
- Right panel: Export

Shared benefits:

- single place for dataset ingress/egress
- shared path picker and folder browser context
- fewer navigation hops

Keep all current controls from both tabs, including export preview and safety flags.

## 15. Settings and presets move

Move preset management from workspace to Settings.

Rationale:

- Presets are installation-global, not project-local.
- Reduces workspace cognitive load.
- Aligns preset lifecycle with backend/timeout/default settings.

Compatibility detail:

- Workspace single-image and batch generation keep preset selectors.
- "Manage Presets" links from workspace jump to Settings / Presets.

## 16. Proposed screen-level UX changes

### 16.1 Home screen (no project)

- Big primary actions:
	- Create Project
	- Open Project
- Recent projects list with quick open
- Optional filesystem browser drawer
- Empty-state guidance for first-time use

### 16.2 Library screen

- Left: image grid with filters/search/sort
- Center: selected image viewer
- Right: stacked panels
	- active caption editor
	- candidate list
	- image tools (duplicate/delete/crop/scale/extract)

### 16.3 Captions screen

- Single-image generation panel (current editor LLM controls)
- Batch text operations panel (find/replace and transforms)
- Optional audit list of recent bulk edits

### 16.4 Data I/O screen

- Import card and Export card side-by-side (stack on mobile)
- Shared path browser trigger
- Export preview remains mandatory before destructive options (clean/overwrite)

## 17. Backend and model changes required

Planned additions to support redesign:

1. Image edit service and endpoints
- duplicate image endpoint
- delete/restore image endpoint
- crop endpoint
- scale endpoint
- extract region endpoint

2. Caption batch edit service and endpoints
- preview replace operation endpoint
- apply replace operation endpoint
- undo endpoint with operation history support

3. Schema additions (proposed)
- images table:
	- deleted_at nullable timestamp (soft delete)
	- source_image_id nullable FK (derived image lineage)
	- derived_operation nullable string
	- derived_operation_params nullable JSON/text
- caption_bulk_ops table (required for multi-step audit/undo)

4. API compatibility
- existing endpoints remain stable for current views while new UI is phased in.

## 18. Delivery phases

Phase A: UX restructuring without feature loss

- Introduce Home mode for no-project state.
- Move preset manager UI into Settings.
- Merge Import/Export into Data I/O tab.
- Keep existing APIs and logic; mostly frontend composition changes.

Phase B: Image tools MVP

- Duplicate and soft delete first.
- Then crop and scale.
- Then extract region as new image.

Phase C: Batch caption operations

- Find/replace preview + apply + audit trail.
- Add multi-step undo over operation history.

Phase D: Polish and optimization

- Keyboard shortcuts for image tools.
- Improved filtering/search in Library.
- Performance tuning for large projects.

## 19. Acceptance criteria

The redesign is successful when:

- All current workflows are still possible.
- New no-project Home flow replaces sidebar create/open friction.
- Import and Export are unified without loss of options.
- Presets are manageable in Settings and still usable in generation flows.
- Image editing operations are non-destructive and auditable.
- Batch caption replace supports preview-before-apply and scoped targeting.

## 20. Decision status

Confirmed decisions:

1. Deletion policy
- soft + permanent delete action

2. Derived caption behavior
- duplicate/extract should copy all candidates by default

3. Regex support
- include regex find/replace in MVP

4. Undo depth
- multi-step operation history

5. Mobile priority
- desktop-first for MVP; mobile is not a priority

## 21. Phase A ticket breakdown (frontend-first restructuring)

This section translates Phase A into executable tickets. Goal: reshape IA and navigation without removing functionality.

### A-1: Add Home mode for no-project state

Status: Implemented (2026-05-02)

Scope:

- Add new no-project Home canvas in workspace area.
- Move Create/Open forms and Recent Projects from sidebar into Home canvas.
- Keep sidebar minimal when no project is open.

Tasks:

- Add ui state for home-mode rendering when currentProject is null.
- Move/reuse existing create/open/recent controls into main content template.
- Keep existing actions unchanged (createProject, openProject, openRecentProject).

Acceptance:

- User can create/open/reopen projects from Home without using sidebar forms.
- Existing project open/close behavior still works.

### A-2: Sidebar split by project-open state

Status: Implemented (2026-05-02)

Scope:

- Open project: show metadata/actions/browser/status.
- No project: show compact app info and optional browser launcher.

Tasks:

- Add explicit sidebar sections for "project-open" and "no-project".
- Keep project metadata editor and close/switch actions only in open state.
- Keep filesystem browser accessible in both states (reduced footprint in no-project state).

Acceptance:

- Sidebar contains no create/open forms when no project is open.
- Metadata edit controls are hidden when no project is open.

### A-3: Merge Import and Export into Data I/O tab

Status: Implemented (2026-05-02)

Scope:

- Replace separate Import and Export tab buttons with one Data I/O tab.
- Render import and export cards in one screen.

Tasks:

- Update mainView options: remove import/export tab buttons, add io tab.
- Move existing import/export form blocks under io view.
- Keep all options and buttons (including export preview) unchanged.

Acceptance:

- All import/export options remain available.
- Existing backend endpoints are reused unchanged.

### A-4: Move preset management to Settings

Status: Implemented (2026-05-02)

Scope:

- Remove LLM presets manager from workspace tab strip.
- Add Settings sub-tab for preset management.

Tasks:

- Add settings sub-navigation state (for example settingsTab).
- Mount current presets manager UI into Settings > Presets.
- Add "Manage Presets" links from generation UI to Settings > Presets.

Acceptance:

- Presets can still be created/updated/deleted.
- Preset selectors in editor/batch continue to function.

### A-5: Preserve behavior parity regression checks

Status: Completed (2026-05-02 live browser pass)

Scope:

- Guard against functional regressions while layout changes.

Tasks:

- Add/update smoke test checklist covering:
	- create/open/close/switch project
	- grid -> editor image selection
	- manual caption save and candidate ops
	- preset generation and manual generation
	- batch start/pause/resume/cancel
	- notes CRUD and note generation
	- import + export preview + export run
- Add targeted UI/API regression tests where feasible.

Acceptance:

- All existing tests remain green.
- Manual smoke checklist passes for updated navigation.

### A-5.1 Parity execution checklist (current)

Automated verification:

- Backend/API regression suite: pass
- Command: ./.venv/bin/python -m pytest -q
- Latest result: 51 passed, 1 warning

Manual smoke checklist for updated IA:

1. Home and project lifecycle
- Create project from Home
- Open existing project from Home
- Open a recent project from Home
- Close current project and return to Home
- Switch project from sidebar when project is open

2. Library and editor flow
- Select image in Grid and verify editor state updates
- Save active caption edits
- Candidate operations: create, activate, edit, delete

3. Caption generation
- Manual single-image generation path
- Preset generation path
- Manage Presets shortcut opens Settings > Presets

4. Batch operations
- Start batch job
- Pause batch job
- Resume batch job
- Cancel batch job

5. Notes workflows
- Project note CRUD
- Global note CRUD
- Generate note draft and generate+save paths

6. Data I/O workflows
- Import folder with replace_existing off/on
- Request export preview
- Run export after preview

Latest live run notes (2026-05-02, local app at http://127.0.0.1:7860):

- PASS: Open existing project from Home, close to Home, reopen from Recent Projects, and Switch Project panel toggle.
- PASS: Grid -> Editor selection, active caption save, and candidate activate flow.
- PASS: Manage Presets shortcut from Editor opens Settings > Presets.
- PASS: Data I/O tab shows merged import/export cards with full controls.
- PASS: Export preview and export run completed (46 images exported, notes exported).
- PASS: Import run completed after correcting source path to practice_dataset/CheerBear (46 images imported).
- PASS: Batch control transitions validated in live job: Start, Pause request, Resume, Cancel.
- PASS: Manual single-image generation and preset generation were re-run and validated.
- PASS: Notes workflows re-run: project/global create-update-delete plus note assistant Generate Draft and Generate + Save.

Observed runtime risk:

- Intermittent /api/projects/recent 500 caused by JSONDecodeError while reading recent-project registry; app recovered in-session, but this should be hardened.

Open items to finish A-5:

- None.

### A-6: Incremental delivery strategy

Recommended PR sequence:

1. PR-A1: Home mode + sidebar no-project cleanup
2. PR-A2: Data I/O merge
3. PR-A3: Presets move to Settings
4. PR-A4: UX polish + regression fixes

Each PR should preserve backend API contracts and keep app runnable with Python-only setup.

## 22. API contract draft: image editing endpoints

These endpoints are additive and do not replace existing image/caption APIs.

Base prefix: /api/images

### 22.1 Duplicate image

Endpoint:

- POST /api/images/{image_id}/duplicate

Request body:

- include_captions: boolean (default true)
- copy_mode: "active_only" | "all_candidates" | "none" (default "all_candidates")

Response:

- 200 OK
- payload:
	- source_image_id
	- new_image: full image summary object
	- copied_caption_count

Errors:

- 404 image not found
- 409 duplicate conflict (rare)

### 22.2 Soft delete / restore image

Endpoints:

- POST /api/images/{image_id}/delete
- POST /api/images/{image_id}/restore

Request body (delete):

- mode: "soft" | "hard" (default "soft")
- hard delete requires explicit confirmation in request payload (for example confirm_hard_delete=true)

Response:

- 200 OK
- payload:
	- image_id
	- deleted_at (null on restore)
	- mode

Notes:

- Soft-deleted images are hidden from default list endpoints.
- Optional include_deleted=true query can expose them for admin/recovery views.

### 22.3 Crop image

Endpoint:

- POST /api/images/{image_id}/crop

Request body:

- rect:
	- x: integer >= 0
	- y: integer >= 0
	- width: integer > 0
	- height: integer > 0
- output_name: optional string
- include_captions: boolean (default true)
- caption_copy_mode: "active_only" | "all_candidates" | "none" (default "all_candidates")

Response:

- 200 OK
- payload:
	- source_image_id
	- new_image
	- operation:
		- type: "crop"
		- params

Validation:

- rect must be fully inside source bounds
- reject zero-area or out-of-bounds rectangles with 422

### 22.4 Scale image

Endpoint:

- POST /api/images/{image_id}/scale

Request body:

- mode: "percent" | "dimensions"
- percent: number > 0 (required for percent mode)
- width: integer > 0 (required for dimensions mode)
- height: integer > 0 (required for dimensions mode)
- keep_aspect_ratio: boolean (default true)
- upscale: boolean (default false)
- include_captions: boolean (default true)
- caption_copy_mode: "active_only" | "all_candidates" | "none" (default "all_candidates")

Response:

- 200 OK
- payload:
	- source_image_id
	- new_image
	- operation:
		- type: "scale"
		- params

Validation:

- if upscale=false, target dimensions must not exceed source bounds

### 22.5 Extract region as new image

Endpoint:

- POST /api/images/{image_id}/extract-region

Request body:

- rect (same contract as crop)
- output_name: optional string
- include_captions: boolean (default true)
- caption_copy_mode: "active_only" | "all_candidates" | "none" (default "all_candidates")
- add_source_reference_note: boolean (default true)

Response:

- 200 OK
- payload:
	- source_image_id
	- new_image
	- operation:
		- type: "extract_region"
		- params

Notes:

- Functionally similar to crop, but semantically treated as asset extraction for dataset authoring.

### 22.6 Shared response object expectations

For all derived-image endpoints, new_image should include:

- id
- filename
- width
- height
- included
- source_image_id
- derived_operation
- derived_operation_params
- created_at

## 23. API contract draft: caption batch find/replace + undo

Base prefix: /api/captions/batch

### 23.1 Preview batch edit

Endpoint:

- POST /api/captions/batch/preview-replace

Request body:

- query:
	- find_text: string
	- replace_text: string
	- mode: "plain" | "regex" (default "plain")
	- case_sensitive: boolean (default false)
- scope:
	- caption_scope: "active_only" | "all_candidates" (default "active_only")
	- image_scope: "all" | "included_only" | "selected_ids"
	- image_ids: array[int] (required when image_scope is selected_ids)

Response:

- 200 OK
- payload:
	- preview_id (uuid)
	- impacted_captions_count
	- impacted_images_count
	- sample_changes: array of
		- image_id
		- caption_id
		- before_preview
		- after_preview
	- warnings: array[string]

### 23.2 Apply batch edit

Endpoint:

- POST /api/captions/batch/apply-replace

Request body:

- preview_id: uuid
- confirm: boolean (must be true)
- create_undo_snapshot: boolean (default true)

Response:

- 200 OK
- payload:
	- operation_id (uuid)
	- updated_captions_count
	- updated_images_count
	- undo_available: boolean

Validation:

- preview_id must exist and not be expired
- applying without confirm=true returns 400

### 23.3 Undo last batch edit

Endpoint:

- POST /api/captions/batch/undo

Request body:

- operation_id: optional uuid
- if omitted, undo most recent undoable operation for current project

Response:

- 200 OK
- payload:
	- undone_operation_id
	- restored_captions_count

Errors:

- 404 no undoable operation found
- 409 operation already undone

### 23.4 Operation history

Endpoint:

- GET /api/captions/batch/operations?limit=50

Response:

- 200 OK
- payload: list of operations
	- operation_id
	- type
	- created_at
	- impacted_captions_count
	- undone_at

### 23.5 Safety and expiry rules

- preview_id expiry: 15 minutes (configurable)
- max impacted captions guardrail: configurable threshold requiring extra confirmation
- regex mode should validate pattern at preview time and return 422 for invalid patterns

## 24. Suggested test matrix for new APIs

Minimum backend tests to add once implementation starts:

1. Image duplicate
- copies expected caption set by copy_mode
- preserves source image unchanged

2. Image delete/restore
- soft delete hides from list by default
- restore returns image to normal listing

3. Crop/scale/extract
- validates bounds and dimensions
- produces derived image with lineage fields

4. Caption preview/apply
- preview counts match apply results
- apply only works with valid, unexpired preview

5. Undo and history
- supports multi-step undo across operation history
- cannot undo same operation twice

6. Regression
- existing caption CRUD and image listing semantics remain stable when no new endpoints are used