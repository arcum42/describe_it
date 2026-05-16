# Notes Feature Plan

## Goal
Add a Notes feature with:
- A dedicated Notes tab in the UI.
- Multiple notes per scope:
  - Project-level notes (stored with a project DB).
  - Program-level notes (global notes shared across projects).
- Notes authored as plain text or markdown.
- Notes indexed in RAG.
- Notes selectable as context for LLM generation:
  - Manual Generate with Tools flow.
  - Preset-based generation.
- Notes exported with project export output.

---

## Scope and Product Decisions

### Note types
1. `project` notes
- Belong to one project DB.
- Export with that project.
- Indexed for that project in RAG.

2. `global` notes
- Stored in app state DB.
- Available in all projects.
- Indexed for RAG as global context.
- Not bundled into per-project export by default (unless explicitly enabled later).

### Note format
- `format`: `text` or `markdown`.
- Store raw content exactly as entered.
- Render markdown in UI preview (optional first pass), but indexing uses normalized text.

### Export behavior
- Export project notes under export output as one of:
  - `notes/` folder with one file per note (recommended), or
  - single `notes.md` aggregate.
- Initial implementation: `notes/` folder, deterministic filenames and metadata header.

---

## Data Model and Storage

### Project DB (`projects` SQLite)
Add table:
- `notes`
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `project_id INTEGER NOT NULL` (FK projects.id)
  - `title TEXT NOT NULL DEFAULT ''`
  - `content TEXT NOT NULL DEFAULT ''`
  - `format TEXT NOT NULL DEFAULT 'markdown'` (`text|markdown`)
  - `tags TEXT NOT NULL DEFAULT ''` (CSV for now; normalize later if needed)
  - `is_archived INTEGER NOT NULL DEFAULT 0`
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`

Migration strategy:
- Add schema guard in DB initialization/open path similar to existing column migration logic.

### Global app state DB (`app_state.db`)
Add table:
- `global_notes`
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `title TEXT NOT NULL DEFAULT ''`
  - `content TEXT NOT NULL DEFAULT ''`
  - `format TEXT NOT NULL DEFAULT 'markdown'`
  - `tags TEXT NOT NULL DEFAULT ''`
  - `is_archived INTEGER NOT NULL DEFAULT 0`
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`

Also add optional global settings defaults:
- `notes_default_format` (optional future)

---

## Backend Services and API

### New services
1. `backend/services/note_service.py`
- CRUD for project notes.
- List/filter by archived, search query, tags.
- Validate format enum.
- Normalize and return DTOs.

2. `backend/services/global_note_service.py`
- CRUD for global notes in app state DB.

3. `backend/services/note_context_service.py`
- Build note context payloads for LLM:
  - by explicit note IDs
  - by scope (`project`, `global`, both)
  - capped by char/token budget

### New routers
1. `backend/routers/notes.py` (project notes)
- `GET /api/notes?project_path=...`
- `POST /api/notes/create`
- `POST /api/notes/update`
- `POST /api/notes/delete`
- `POST /api/notes/archive`
- `POST /api/notes/unarchive`

2. `backend/routers/global_notes.py`
- `GET /api/global-notes`
- `POST /api/global-notes/create`
- `POST /api/global-notes/update`
- `POST /api/global-notes/delete`
- `POST /api/global-notes/archive`
- `POST /api/global-notes/unarchive`

### LLM API integration
Extend generate endpoints payloads:
- Manual tools endpoint (`generate-caption-with-tools`):
  - `project_note_ids: list[int] = []`
  - `global_note_ids: list[int] = []`
  - `include_project_notes: bool = false` (quick include-all toggle)
  - `include_global_notes: bool = false`

- Preset generation:
  - Preset fields for notes context behavior:
    - `include_project_notes`
    - `include_global_notes`
    - `project_note_ids_template` (optional placeholder-enabled string list form)
    - `global_note_ids_template` (optional)

Service behavior:
- Resolve selected notes.
- Append notes context into injected system/context block before tool loop/native call.
- Include note usage in `tool_usage_log` / generation status.

---

## RAG Indexing Plan

### Source documents
Index these document categories:
- Image captions (existing behavior).
- Project notes.
- Global notes.

### Metadata schema (Chroma docs)
For each note chunk:
- `doc_type`: `project_note` or `global_note`
- `note_id`
- `project_path` (for project notes)
- `title`
- `format`
- `tags`
- `updated_at`

### Index lifecycle
- On note create/update/delete/archive:
  - upsert or delete corresponding embeddings.
- On project open:
  - ensure project note index state is current.
- Global notes:
  - maintain in shared index namespace or metadata-filtered docs.

### Retrieval behavior
- For project generation, retrieve from:
  - project note docs
  - optionally global note docs
  - existing caption examples if enabled
- Add filtering controls in RAG service to include/exclude note types.

---

## Frontend UX Plan

### New Notes tab
Add top-level tab in workspace view:
- `Notes`
- Split layout:
  - Left: note list + filters/scope switch.
  - Right: editor (title, format, tags, content) + preview.

### Scope switch
- Toggle between:
  - Project Notes
  - Global Notes
- If no project open, project notes UI disabled with helper text.

### LLM context selection
In editor generation panel and preset editor:
- Add notes context controls:
  - Include all project notes
  - Include all global notes
  - Optional multi-select picker for specific notes
  - Budget indicator (chars used/limit)

### Placeholder support messaging
Update helper text for placeholders to include note-related options where relevant.

---

## Preset Model Changes

Extend global preset schema with fields:
- `include_project_notes INTEGER DEFAULT 0`
- `include_global_notes INTEGER DEFAULT 0`
- `project_note_ids_template TEXT DEFAULT ''`
- `global_note_ids_template TEXT DEFAULT ''`

Support placeholder rendering in all text fields (consistent with current implementation).

---

## Export Plan

### Project export output
When exporting dataset:
- Add `notes/` directory in output root.
- For each active project note write:
  - `<slug>-<id>.md` for markdown notes
  - `<slug>-<id>.txt` for text notes

File header block:
- title
- id
- format
- tags
- created_at/updated_at

### Export settings
Add export option:
- `include_project_notes` (default true).

Optional future:
- Include global notes toggle (default false).

---

## Implementation Phases

### Phase 1: Storage + API foundation
- Add DB schema/migrations for project/global notes.
- Add service-layer CRUD.
- Add notes routers and tests.

### Phase 2: Notes tab UI
- Add tab and list/editor UX.
- Wire CRUD flows.
- Add markdown/text format support.

### Phase 3: RAG integration
- Index note docs.
- Upsert/delete hooks on note changes.
- Retrieval filter support.

### Phase 4: LLM context integration
- Manual generation note selection support.
- Preset note options and template fields.
- Status/log output for included notes.

### Phase 5: Export integration
- Export project notes as files.
- Add export setting toggle and tests.

---

## Test Plan

### Backend tests
- CRUD tests for project notes and global notes.
- Migration tests for existing DBs without notes tables.
- Preset schema round-trip tests for note-related fields.
- LLM request payload tests to ensure note context is injected correctly.
- Export tests verifying notes files are produced.

### RAG tests
- Index insert/update/delete for notes.
- Retrieval includes/excludes notes by scope.

### Frontend tests (smoke/integration style)
- Notes tab loads and saves notes.
- Scope switching works.
- Note selection affects generation payload.
- Preset create/update includes note options.

---

## Risks and Mitigations

1. RAG growth and performance
- Mitigation: chunk notes, metadata filter first, enforce max context budget.

2. Context overload in generation
- Mitigation: deterministic truncation policy + overflow retry (already present).

3. UI complexity creep
- Mitigation: staged rollout and sensible defaults (include-none initially).

4. Migration safety
- Mitigation: additive schema changes only, guarded with PRAGMA checks.

---

## Acceptance Criteria

1. User can create/edit/delete multiple notes in both project and global scope.
2. Notes support text or markdown format.
3. Notes are indexed and retrievable via RAG.
4. User can include notes as generation context in:
- Manual tools flow
- Preset flow
5. Presets persist note-context options and templates.
6. Project export includes project notes as files when enabled.
7. Existing projects and presets continue to work without manual migration steps.
