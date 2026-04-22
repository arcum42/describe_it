# describe_it Implementation Plan

## Goal

Turn the overview into an executable implementation roadmap, starting with a minimal but solid project scaffold using:

- Python backend
- SQLite per project
- BLOB image storage
- Plain HTML + vanilla JS + Alpine.js frontend
- Optional ChromaDB integration

## Current Status (April 2026)

- Phase 1: complete
- Phase 2: complete
- Phase 3: complete
- Phase 4: complete
- Phase 5: complete
- Phase 6: complete
- Phase 7: not started

---

## Guiding Principles

- Build the smallest working end-to-end slice first
- Keep the first version easy to run locally
- Avoid adding a JS build pipeline until it is clearly needed
- Keep project data portable and self-contained
- Make optional features like ChromaDB additive, not required

---

## Phase 1: Project Layout And Bootstrap

Status: complete

This is the first implementation step.

### Objectives

- Create the repository structure
- Set up the Python virtual environment and dependency files
- Add the FastAPI entrypoint
- Add the static frontend shell
- Add Copilot/LLM project instructions under `.github/instructions/`
- Establish a clean import structure so later features slot in without reorganizing the project

### Proposed Layout

```text
describe_it/
├── .github/
│   └── instructions/
│       └── describe_it.instructions.md
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── projects.py
│   │   ├── images.py
│   │   ├── captions.py
│   │   └── llm.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── import_service.py
│   │   ├── export_service.py
│   │   └── caption_service.py
│   └── llm/
│       ├── __init__.py
│       ├── base.py
│       ├── ollama_client.py
│       ├── lmstudio_client.py
│       └── prompt_builder.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── requirements.txt
├── requirements-optional.txt
├── run.py
└── README.md
```

### Deliverables

- Backend starts on port `7860`
- `GET /api/health` returns a simple success payload
- FastAPI serves `frontend/index.html`
- Browser opens to a simple shell UI with placeholders for project picker, grid view, and image editor
- Base and optional dependencies are separated cleanly

### Completed Notes

- FastAPI app bootstrap and static frontend hosting are implemented.
- Health endpoint is live and used by the UI.
- Project instruction file exists under `.github/instructions/`.
- Baseline dependency files and local run flow are in place.

### Notes

- `requirements.txt` should contain only the baseline needed to run the app
- `requirements-optional.txt` should include things like `chromadb` and other experimental or stretch-goal dependencies
- If database migrations are added later, Alembic can be introduced after the schema settles a bit

---

## Phase 2: Project And Database Foundation

Status: complete

### Objectives

- Define the initial SQLite schema
- Support creating and opening a project `.db`
- Store project metadata
- Add the first persistence layer abstractions

### Initial schema targets

- `projects`
- `images`
- `captions`
- `prompts`
- `presets`

### Deliverables

- Create new project from the UI or CLI
- Open an existing project `.db`
- Save and load project metadata

### Completed Notes

- SQLAlchemy models for projects, images, captions, prompts, and presets are implemented.
- Create/open/update project flows are available via API and UI.
- Recent project registry and bounded path browser are implemented.

---

## Phase 3: Import And Image Storage

Status: complete

### Objectives

- Import images from a folder
- Pair them with matching `.txt` files if present
- Store original image bytes in SQLite BLOBs
- Create blank captions when no caption file exists

### First test case

Use a local dataset under `practice_dataset/` as the first real import verification set.

- Create a project named `Practice Dataset`
- Store it at `projects/practice_dataset.db`
- Import the full selected folder (for example `practice_dataset/sample_set/`) into that project
- Verify that matching image/text pairs are detected correctly
- Verify that images without captions get blank caption entries
- Keep source dataset folders out of git; they are local test data, not project source

### Deliverables

- Folder import works for common image formats
- Original bytes are preserved untouched
- Imported records appear in the grid view
- Practice dataset import succeeds as the first end-to-end Phase 3 verification

### Completed Notes

- Folder import stores image bytes in SQLite BLOB fields and keeps source files untouched.
- Matching `.txt` captions are imported; missing captions are represented as blank captions.
- A folder under `practice_dataset/` was used as the first real import verification set.

---

## Phase 4: Core Editing UI

Status: complete

### Objectives

- Build the grid view
- Build the single-image editor
- Support manual caption editing
- Support include/exclude toggling
- Support multiple caption candidates per image

### Alpine.js scope

- App state store for selected project, selected image, and current view
- Fetch wrappers for API calls
- Modal visibility and lightweight UI interactions
- Keyboard shortcuts later, once the base interactions are stable

### Deliverables

- Click image in grid -> open image editor
- Edit active caption and save it
- Switch between caption candidates

### Completed Notes

- Grid and single-image editor flows are implemented.
- Include/exclude toggling, active caption editing, candidate creation, and active-candidate switching are implemented.
- Main workspace now supports section switching between Grid and Editor.
- Project/sidebar UX was cleaned up (conditional create/current project, close project, integrated path browser).

---

## Phase 5: LLM Integration

Status: complete

### Objectives

- Add Ollama backend integration
- Add LM Studio backend integration
- Support prompting the current image
- Store generated captions as new candidates

### Suggested implementation order

1. Ollama Python client
2. LM Studio Python SDK
3. LM Studio native REST API evaluation if the SDK proves limiting

### Deliverables

- Generate caption for one image
- Generate captions for selected or all images
- Preserve manual captions while adding generated alternatives

### Completed In This Phase So Far

- LLM backend discovery endpoint is implemented (`/api/llm/backends`) with model listing.
- Single-image generation endpoint is implemented (`/api/llm/generate-caption`).
- Ollama and LM Studio clients are wired for generation requests.
- Generated captions are stored as new caption candidates with source metadata.
- Error handling for upstream HTTP and timeout failures is implemented to avoid server crashes.
- User-configurable generation timeout is implemented and persisted in frontend settings.
- A dedicated Settings view (gear button in header) is implemented, separate from main workspace views.
- Vision capability detection is implemented from provider metadata (Ollama show metadata and LM Studio model capabilities).
- Model picker UX now supports vision-only filtering, show-all toggle, and visual vision markers.
- Preset workflows are implemented: list/create/update/delete presets and generate using selected preset.
- Debug controls are implemented in settings, with conditional debug panel visibility.
- Server-side batch orchestration is implemented: create/list/get/pause/resume/cancel, plus live polling support.
- Batch processing options are implemented: output mode, retry count, and skip-on-failure behavior.
- Batch jobs and per-image results are persisted in app state storage and recovered across backend restart.
- Batch UI now includes job history, status filtering, per-image result table, and CSV export.

### Phase 5 Completion Notes

- Presets now support explicit caption mode strategy (`auto`, `description`, `tags`) and generation respects the selected strategy.
- Optional per-backend runtime settings are implemented and persisted: base URL and timeout overrides for Ollama and LM Studio.
- Backend discovery and generation now use the configured backend runtime settings.
- Batch flow includes persistent jobs/results, restart recovery, job history filtering, per-image result inspection, and CSV export.

---

## Phase 6: Export

Status: complete

### Objectives

- Export included images and active captions to a folder
- Apply trigger words during export
- Keep export behavior non-destructive

### Deliverables

- Flat export folder with image + `.txt` pairs
- Optional dataset metadata output

### Completed In This Phase So Far

- Export API route is implemented at `/api/projects/export`.
- Export preview route is implemented at `/api/projects/export-preview`.
- Included-image export to folder is implemented as image + active-caption `.txt` pairs.
- Trigger word application is implemented as optional behavior and is skipped when trigger word is unset.
- Export flow is wired into the sidebar UI with explicit options:
	- Export only included images
	- Apply project trigger word (if set)
	- Configurable output folder
- Optional metadata manifest export (`export_manifest.json`) is implemented.
- Collision handling controls are implemented:
	- overwrite existing files
	- clean output folder before export
- Export preview is implemented in UI and API with destination/collision/count visibility.
- Export can target a new subfolder in the selected destination path.
- Regression checks were added for:
	- trigger-word positive application path
	- overwrite vs clean-output behavior and collision handling
	- preview and export count consistency
- End-user export guide is published in `PHASE_6_EXPORT_GUIDE.md` with comprehensive workflow examples and troubleshooting.

### Phase 6 Complete

Phase 6 deliverables are finalized: flat export folder with image/txt pairs, optional metadata manifest, non-destructive collision controls, preview functionality, and new-subfolder export option. Export regression tests pass. All features are ready for production use.

---

## Phase 7: Optional ChromaDB / RAG Layer

Status: not started

This should remain optional and not block the base application.

### Objectives

- Add a feature flag or availability check for ChromaDB
- Build embeddings from captions
- Retrieve similar captions during AI generation
- Add semantic search for captions

### Suggested design

- Keep Chroma collections outside the main SQLite database
- Rebuild the vector index from project data on demand
- Only enable RAG features when ChromaDB is installed and configured

### Deliverables

- Rebuild embeddings for a project
- Search captions semantically
- Optional few-shot retrieval in prompt generation

---

## CLI Plan

Status: planned

The CLI should reuse backend services directly rather than going through HTTP.

### Initial commands

```text
describe-it create-project --project path/to/project.db --name "My Dataset"
describe-it import-folder --project path/to/project.db --folder ./images
describe-it caption --project path/to/project.db --preset default --all
describe-it export --project path/to/project.db --output ./export
```

### Why this matters

- Easier scripting
- Easier batch jobs
- Easier testing of backend logic without the browser

---

## Immediate Next Tasks

1. Add regression checks for batch resume/restart recovery, results integrity, and CSV export behavior.
2. Add UI affordances for backend settings validation (URL sanity checks and connection test button).
3. Update end-user docs for preset mode strategy, backend runtime settings, and batch workflows.
4. Run a full end-to-end smoke pass across project lifecycle: create/open/import/edit/generate/batch/export.
5. Consider Phase 7 (ChromaDB/RAG) if needed, or focus on hardening/polish before public release.

---

## Recommended Dependency Split

### Base

- fastapi
- uvicorn
- sqlalchemy
- pydantic
- pillow
- ollama
- lmstudio
- python-multipart

### Optional

- chromadb
- imagehash
- httpx

`httpx` may move to base if it becomes part of the standard LM Studio REST path.