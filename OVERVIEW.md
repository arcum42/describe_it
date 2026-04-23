# describe_it — Image Dataset Captioning Tool

## Overview

**describe_it** is a tool for assembling and managing captioned image datasets, intended for use in AI/ML model training (e.g., LoRA fine-tuning with Kohya, Flux, or similar pipelines). It combines manual caption editing with AI-assisted captioning via local vision-language models, and handles the full lifecycle of a dataset from import through export.

---

## Core Concepts

The standard format for image captioning datasets pairs each image with a plain text file of the same base name:

- `picture1.png` → `picture1.txt`
- `my_photo.jpg` → `my_photo.txt`

Captions can be either **natural language descriptions** (e.g., for Flux, Z-Image, Ernie, Klein, and similar models) or **comma-separated tag lists** (e.g., danbooru/e621 tags, typically used with SDXL-based models).

---

## Project Management

### Starting a Project
When the program is opened, the user must start or load a project:

- **New empty project** — blank project, images added manually later
- **Import from folder** — copy all images from a folder into the project; pair with existing `.txt` files where present, or create blank ones otherwise
- **Reopen existing project** — load a previously saved project from the database

Each project is stored in its own SQLite `.db` file, chosen at creation time (or defaulting to a location alongside a central project registry). All data — images, captions, prompts, settings — lives inside that single file, making projects easy to move, share, and back up.

### Project Metadata
Each project should store:
- Project name and description
- Date created / last modified
- Dataset description (optional) — a short summary of what the dataset contains; can optionally be injected into LLM prompts to give the model context
- Trigger word(s) — a word or short phrase prepended (or appended) to every active caption on export (e.g., `my_character_v1`)
- Caption mode: `description` or `tags`
- Default LLM preset

---

## Image Management

### Adding Images
- **From local disk** — file picker, single image or batch
- **From URL** — download and import a single image
- **From folder** — bulk import; copies images into the project
- **Future / stretch goal**: Import from imageboards (Danbooru, e621, Gelbooru, etc.) via their public APIs, optionally pulling existing tags along with images

### Image Storage
- The project preserves the **original, unmodified source image** for every imported file.
- Working copies are derived from originals; augmentations never overwrite the source.
- Images are stored as **BLOBs inside the SQLite database**, keeping everything in a single portable file. The project `.db` is fully self-contained.

### Image Augmentation
It should be possible to generate derived variants of any image for dataset augmentation:
- **Horizontal flip** (mirror)
- **Rotation** (90°, 180°, 270°, or arbitrary angle with optional crop-to-fit)
- **Crop** (manual region selection or preset aspect ratios)
- Derived images are linked to their parent in the database; their captions can be inherited from the parent or edited independently.

### Include / Exclude
Each image can be marked as **included** or **excluded** from the dataset. Excluded images remain in the project but are skipped on export. This is useful for culling low-quality images without deleting them.

---

## Caption / Text Management

### Caption Model
Each image can have **multiple caption candidates** stored against it. One is designated the **active caption** (the first one by default). This allows side-by-side comparison of, say, a manual caption and several AI-generated ones before committing to one.

### Manual Editing
In the single-image view, the active caption is shown in an editable text area next to the image. Switching the active caption can be done from a dropdown or tab list of available candidates.

### Batch Text Operations
Text operations that apply across all (or selected) images:
- **Prepend / append text** to all active captions
- **Find and replace** within captions
- **Add trigger word** to all captions (prepend by default, configurable)
- **Clear all captions** (with confirmation)
- **Copy caption from parent** for augmented/derived images
- **Strip duplicate tags** (for tag-mode datasets)
- **Sort tags alphabetically** or by frequency across the dataset

### Tag Bubble Mode
When the project is in **tag mode**, an alternative caption editor displays tags as interactive word bubbles:
- Drag to reorder tags
- Click a bubble to delete it
- Type to add a new tag
- Optionally color-code bubbles by tag category (character, general, meta, etc. — following danbooru taxonomy)

---

## LLM / AI Captioning

### Supported Backends

#### Ollama
- **REST API**: `http://localhost:11434` (see [docs](https://docs.ollama.com/) and [API reference](https://github.com/ollama/ollama/blob/main/docs/api.md))
- **Python library**: `ollama` (`pip install ollama`) — supports sync and async clients, streaming, embeddings (`ollama.embed()`), and model management (`ollama.list()`, `ollama.pull()`, etc.)
- Models are identified by short names like `llava`, `llama3.2-vision`, `minicpm-v`, `qwen2-vl`

#### LM Studio
LM Studio exposes several API layers — it is worth being familiar with all of them:

| API | Base URL | Notes |
|---|---|---|
| **Native REST API (v1)** | `http://localhost:1234/api/v1/` | Stateful chats, model load/unload/download, MCP, streaming load events — prefer this |
| **OpenAI-compatible** | `http://localhost:1234/v1/` | Use with `openai` Python library; chat, embeddings, structured output, tool calling |
| **Anthropic-compatible** | `http://localhost:1234/` | Claude-style Messages API |
| **Python SDK** | — | `pip install lmstudio` (`import lmstudio as lms`); native SDK with convenience, scoped resource, and async APIs |

The native LM Studio REST API has meaningful extras over the OpenAI-compat layer: stateful chat sessions, model load/unload/download endpoints, MCP server support, and streaming events for model loading and prompt processing. It is worth evaluating both the Python SDK and the raw REST API to see which fits better.

- Docs: [developer overview](https://lmstudio.ai/docs/developer), [REST API](https://lmstudio.ai/docs/developer/rest), [Python SDK](https://lmstudio.ai/docs/python)
- Models are identified by path-style names like `"qwen/qwen3-4b-2507"`

The app should detect which backends are currently running and list available vision-capable models from each.

### Model Selection
- Choose backend (Ollama / LM Studio)
- Choose a vision model from those currently loaded/available (e.g., `llava`, `llama3.2-vision`, `minicpm-v`, `qwen2-vl`)
- The selected model + backend can be saved as part of a **preset**

### Prompt Management
- Store named prompts in the database
- Associate a prompt with a model/backend as a **preset**
- Example prompts:
  - `"Describe this image in detail."`
  - `"List the contents of this image as danbooru tags, comma-separated."`
  - `"Describe the character, their clothing, pose, and the background."`
- Prompt templates can include a `{dataset_description}` placeholder that is filled in from the project's dataset description field
- Optionally include the image's **current active caption** in the prompt as guidance (e.g., `"Here are some existing notes: {current_caption}. Now write a full description."`)

### Captioning Workflow
- **Caption current image** — sends the current image + prompt to the model, stores the result as a new caption candidate
- **Caption all images** — batch processes every included image; shows a progress bar
- **Caption uncaptioned images only** — batch, but skips images that already have a non-empty active caption
- Result can be set to:
  - **Replace** the active caption
  - **Append** to the active caption
  - **Add as new candidate** (default — non-destructive)
- A **cancel** button should interrupt a running batch

---

## Views / UI

The application runs as a local web server (Python backend) with a browser-based frontend. On launch it starts the server and opens the browser to `http://localhost:<port>`.

### Project Picker / Home Screen
- List of recent projects
- Buttons: New Project, Import Folder, Open Project file

### Grid View
- Thumbnail grid of all images in the project
- Visual indicator for: included/excluded, has caption, has no caption
- Hover tooltip shows the active caption text
- Click to open Single Image View
- Toolbar for bulk operations (select all, exclude selected, batch caption, export)

### Single Image View
- Large image display (with zoom/pan)
- Caption editor panel alongside:
  - Active caption text area (or tag bubbles in tag mode)
  - Caption candidate list (select active, view/delete others)
  - "Generate Caption" button with model/prompt selector
- Navigation arrows (previous / next image)
- Image info: filename, dimensions, file size, augmentation source if derived

### Settings Panel
- LLM backend configuration (URLs, API keys if needed)
- Default caption mode (description vs. tags)
- Prompt library management
- Preset management

---

## Export

When the dataset is ready for training:

- Exports **only included images** and their **active captions**
- Creates copies of images in a flat output folder (no subdirectory nesting, as most training tools expect)
- Writes `image_name.txt` alongside each image
- Trigger word is prepended to every caption at export time (non-destructive — the stored caption is unchanged)
- Export dialog options:
  - Output folder path
  - Image format conversion (keep original / convert to PNG / convert to JPEG with quality setting)
  - Whether to resize images (e.g., bucket to 512, 768, 1024 px on the long edge)
  - Whether to include a `dataset.json` metadata file summarizing the export

---

## Technical Stack

### Backend (Python)
- **Framework**: FastAPI (async, fast, easy REST + WebSocket support) or Flask (simpler, adequate for local use)
- **Database**: SQLite via SQLAlchemy ORM (single-file, no server required)
- **Image processing**: Pillow for augmentation and format conversion
- **LLM clients**: `ollama` Python library; `lmstudio` Python SDK and/or `openai` library (for LM Studio — evaluate both the native SDK and raw REST API)
- **Optional retrieval / embeddings**: ChromaDB as an optional dependency for semantic search and few-shot example retrieval
- **Virtual environment**: local `.venv` created at first run or via a `setup.sh` / `install.bat` script

### Frontend

The frontend is served as static files from the Python server (FastAPI can serve a `static/` directory directly). The browser talks to the backend via a simple JSON REST API — no separate frontend server is needed in production.

For CSS, **DaisyUI on top of Tailwind CSS** is a strong default: it provides ready-made components (buttons, modals, cards, badges) that suit this UI well, and Tailwind can be pulled in via CDN for a no-build setup, or via the Vite pipeline if a build step is used anyway.

The frontend uses **Alpine.js + vanilla fetch** with no build step. The whole frontend is served as static files from the FastAPI backend.

- `frontend/index.html` contains the main UI shell
- `frontend/app.js` contains shared state, API calls, and view logic
- `frontend/styles.css` contains project-specific styling on top of Tailwind/DaisyUI if needed
- Alpine.js is loaded from CDN initially to avoid introducing a Node.js build toolchain before it is necessary

### Project File Layout (on disk)
```
describe_it/
├── .venv/
├── .github/
│   └── instructions/
│       └── describe_it.instructions.md
├── backend/
│   ├── main.py          # server entrypoint
│   ├── models.py        # SQLAlchemy models
│   ├── services/        # import/export, captions, project operations
│   ├── routers/         # API route modules
│   ├── llm/             # ollama / lm_studio client wrappers
│   └── db/              # database session, migrations, repository helpers
├── frontend/
│   ├── index.html       # main Alpine.js UI
│   ├── app.js           # frontend behavior and API client calls
│   └── styles.css       # optional local styles
├── requirements.txt     # base dependencies
├── requirements-optional.txt
├── IMPLEMENTATION_PLAN.md
└── run.py               # convenience launcher
```

Notes:
- `.github/instructions/describe_it.instructions.md` is intended for Copilot and other LLM tooling guidance.
- `requirements-optional.txt` can hold extras like `chromadb`, `imagehash`, or other stretch-goal packages without bloating the base install.

### Database Schema (sketch)
- `projects` — id, name, description, trigger_word, caption_mode, created_at
- `images` — id, project_id, filename, original_blob (BLOB), width, height, included
- `captions` — id, image_id, text, is_active, source (manual | model_name), created_at
- `prompts` — id, project_id, name, text
- `presets` — id, project_id, name, prompt_id, backend, model_name

Note: `original_blob` stores the unmodified source bytes. `working_blob` is null until an augmentation is applied (flip, crop, etc.), at which point it holds the derived image. The active caption is always read from `captions`, never baked into the blob.

---

## Future / Stretch Goals

- **Imageboard API import** — bulk import from Danbooru, e621, Gelbooru with existing tags
- **Duplicate detection** — perceptual hashing (e.g., `imagehash` library) to flag near-duplicate images
- **CLIP-based auto-sorting** — embed all images and cluster or sort by visual similarity
- **Tag frequency analysis** — show a histogram of all tags in the dataset; useful for balancing
- **Caption quality scoring** — use a second LLM call to rate or critique a caption
- **Interrogator integration** — support WD14 tagger / CLIP interrogator for automatic tag generation without a full VLM
- **Multi-project export** — merge several projects into one export folder
- **Undo/redo** for caption edits
- **Keyboard shortcuts** in single-image view (arrow keys to navigate, `E` to edit, `G` to generate caption, etc.)

---

## RAG / Embedding-Assisted Captioning

ChromaDB is supported as an **optional dependency** (`requirements-optional.txt`). When installed it enables:

- **Few-shot example retrieval** — finds the `N` most similar already-captioned images (by caption embedding similarity) and injects their captions into the prompt as style examples.
- **Semantic caption search** — search across captions by meaning rather than exact keywords.

The RAG collection is built from caption text embeddings (not raw image embeddings) and can be rebuilt on demand from the Settings panel. When ChromaDB is not installed the feature is gracefully disabled and all other functionality is unaffected.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Project storage | One `.db` file per project | Most portable; easy to move, share, and back up |
| Image storage | BLOBs inside SQLite | Self-contained single file; no external folder to manage |
| Default port | `7860` | Already common in the local ML tooling space (Gradio, etc.) |
| CLI mode | Yes | Useful for headless/scripted batch captioning |

### CLI Mode
A CLI interface (`python -m describe_it` or a `describe-it` entry point) should support at minimum:

```
describe-it caption --project path/to/project.db --preset my_preset [--all | --uncaptioned]
describe-it export --project path/to/project.db --output ./export_folder
describe-it import --project path/to/project.db --folder ./images
```

The web server is optional when using the CLI — the same backend logic is called directly without starting the HTTP server.