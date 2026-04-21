# describe_it Implementation Plan

## Goal

Turn the overview into an executable implementation roadmap, starting with a minimal but solid project scaffold using:

- Python backend
- SQLite per project
- BLOB image storage
- Plain HTML + vanilla JS + Alpine.js frontend
- Optional ChromaDB integration

---

## Guiding Principles

- Build the smallest working end-to-end slice first
- Keep the first version easy to run locally
- Avoid adding a JS build pipeline until it is clearly needed
- Keep project data portable and self-contained
- Make optional features like ChromaDB additive, not required

---

## Phase 1: Project Layout And Bootstrap

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

### Notes

- `requirements.txt` should contain only the baseline needed to run the app
- `requirements-optional.txt` should include things like `chromadb` and other experimental or stretch-goal dependencies
- If database migrations are added later, Alembic can be introduced after the schema settles a bit

---

## Phase 2: Project And Database Foundation

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

---

## Phase 3: Import And Image Storage

### Objectives

- Import images from a folder
- Pair them with matching `.txt` files if present
- Store original image bytes in SQLite BLOBs
- Create blank captions when no caption file exists

### Deliverables

- Folder import works for common image formats
- Original bytes are preserved untouched
- Imported records appear in the grid view

---

## Phase 4: Core Editing UI

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

---

## Phase 5: LLM Integration

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

---

## Phase 6: Export

### Objectives

- Export included images and active captions to a folder
- Apply trigger words during export
- Keep export behavior non-destructive

### Deliverables

- Flat export folder with image + `.txt` pairs
- Optional dataset metadata output

---

## Phase 7: Optional ChromaDB / RAG Layer

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

1. Create the base directory structure and placeholder files
2. Set up `requirements.txt` and `requirements-optional.txt`
3. Add a minimal FastAPI app that serves the frontend shell and a health endpoint
4. Add the initial `.github/instructions/describe_it.instructions.md`
5. Verify the app starts locally on port `7860`

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