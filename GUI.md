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
- Project lifecycle controls (create/open, current project metadata, close/switch).
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
	- grid, editor, llm, batch, notes, import, export

### 3.3 Guardrails and disabled states

- Editor tab is disabled when no image is selected.
- Import and Export tabs are disabled when no project is open.
- Many actions are disabled while operations are active.
- Closing a project prompts confirmation if active-caption edits are unsaved.

## 4. Sidebar: project and filesystem controls

### 4.1 No project open state

The sidebar shows a Create/Open toggle panel.

- Create project form:
	- name
	- DB path
	- description
- Open project form:
	- existing DB path

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

## 5.3 LLM tab (Preset manager)

Purpose:
- Manage reusable global LLM presets (shared across projects).

Features:

- Preset list and selection.
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
- Supported placeholders are shown in-UI.
- Actions:
	- create
	- update
	- delete
	- reset to new draft

## 5.4 Batch tab

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

## 5.5 Notes tab

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

## 5.6 Import tab

Purpose:
- Import dataset folder contents into current project.

Controls:

- source folder path
- replace existing images toggle
- import action button

## 5.7 Export tab

Purpose:
- Export image/caption dataset from current project.

Controls:

- output folder (with sidebar browser assist)
- create new subfolder + optional folder name
- included-only filter
- apply project trigger word
- include export manifest metadata
- include project notes as files
- overwrite existing files
- clean output folder

Flow:

- Request export preview
- Review preview stats and overwrite warnings
- Run export

## 6. Settings view (separate from tabs)

Settings is not a workspace tab. It is a separate uiSection opened from the top-right button.

Panels:

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
- Soft-delete first (recoverable), optional permanent delete later.

3. Crop
- Rectangular crop with preview and apply.

4. Scale
- Resize by percent and/or target width/height, with aspect lock.

5. Extract region as new image
- Draw rectangle over source image and create a new image from selected region.
- Optional carry-over of source caption as starter candidate.

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
	- regex (optional advanced mode)
	- case sensitive toggle
- Preview first, then apply.

2. Bulk transforms (phase 2)
- trim whitespace
- normalize punctuation spacing
- prepend/append token
- deduplicate repeated tags (tags mode)

3. Safety
- show impacted caption count before apply
- one-click undo for last bulk operation (project session level)

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
- optional undo endpoint

3. Schema additions (proposed)
- images table:
	- deleted_at nullable timestamp (soft delete)
	- source_image_id nullable FK (derived image lineage)
	- derived_operation nullable string
	- derived_operation_params nullable JSON/text
- caption_bulk_ops table (optional but recommended for audit/undo)

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
- Add lightweight undo for last operation.

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

## 20. Open decisions

Before implementation, confirm:

1. Deletion policy
- soft delete only, or soft + permanent delete action

2. Derived caption behavior
- duplicate/extract should copy active caption only, all candidates, or none by default

3. Regex support
- include regex find/replace in MVP or phase it after plain text mode

4. Undo depth
- single-step undo vs multi-step operation history

5. Mobile priority
- whether full editing tools must be first-class on smaller screens or desktop-first for MVP