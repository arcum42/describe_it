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

#### Option 1 — Plain HTML + Vanilla JS + Alpine.js ⭐ Easiest

- **Setup**: Drop `alpine.js` from a CDN into `index.html`. No build step, no `package.json`, nothing to install beyond the Python backend.
- **How it works**: Alpine.js adds reactive data binding (`x-data`, `x-bind`, `x-on`) directly in HTML attributes, handling UI state like open/closed modals, hover states, and toggling views without writing imperative JS.
- **Good for**: The grid view, single-image view, settings panel, and most forms work naturally with Alpine. Fetch calls to the backend are plain `fetch()`.
- **Difficulty**: Very low. If you know HTML and a little JS, you're productive immediately.
- **Limitation**: The tag bubble drag-and-drop editor would need a small vanilla JS library (e.g., [SortableJS](https://sortablejs.github.io/Sortable/)) to handle dragging. Manageable, but slightly awkward without a component model.
- **File layout**: Everything lives in `frontend/index.html` plus maybe a `frontend/app.js` for shared fetch helpers. No bundler, no build command.

#### Option 2 — HTMX

- **Setup**: Drop `htmx.js` from a CDN. No build step. The server renders HTML fragments that replace parts of the page.
- **How it works**: HTMX lets HTML elements trigger HTTP requests and swap the response into the DOM — e.g., clicking "Generate Caption" sends a POST and the server returns just the updated caption panel HTML. The Python backend (Jinja2 templates with FastAPI or Flask) handles all rendering logic.
- **Good for**: Apps that are fundamentally CRUD-heavy with discrete page regions that update independently. The grid, single-image view, and settings panel all fit this model well.
- **Difficulty**: Low to medium. Easy once the pattern clicks, but requires the backend to return HTML rather than JSON, which is a different mental model if you're used to SPA-style API design. It also means mixing presentation concerns into the Python server.
- **Limitation**: Live updates (e.g., a streaming progress bar during batch captioning) require HTMX's SSE or WebSocket extensions, which adds complexity. The tag bubble editor still needs a JS drag library.
- **Note**: HTMX and Alpine.js are frequently used together — HTMX for server-driven partial updates, Alpine for purely client-side interactivity. This combo covers most of the UI without a build step.

#### Option 3 — Vue 3 + Vite ⭐ Best balance for this project

- **Setup**: `npm create vite@latest frontend -- --template vue`, then `npm install`. Running `npm run dev` starts a hot-reloading dev server; `npm run build` outputs a `dist/` folder that FastAPI serves as static files.
- **How it works**: Vue's single-file components (`.vue` files) co-locate template, logic, and styles. The Composition API (`<script setup>`) makes state and reactivity straightforward. The whole app is a tree of components — `GridView.vue`, `ImageEditor.vue`, `TagBubble.vue`, etc.
- **Good for**: The tag bubble editor is a natural fit for a Vue component with a drag library (SortableJS or Vue Draggable). Complex reactive state — like tracking which caption candidate is active, live streaming tokens from the LLM into the text area, or a progress bar updating as batch captioning runs — is much cleaner in Vue than in Alpine or HTMX.
- **Difficulty**: Medium. Requires Node.js on the machine and familiarity with the Vite/npm workflow. The learning curve for Vue 3 Composition API is modest. The two-server dev experience (Vite on one port, FastAPI on another, with a proxy) adds a small setup step but is well-documented.
- **Limitation**: Adds a Node.js dependency and a build step. The `dist/` output must be rebuilt whenever frontend code changes (fine in production; the dev server handles this automatically).

#### Option 4 — React

- **Setup**: Similar to Vue + Vite (`npm create vite@latest frontend -- --template react`).
- **How it works**: Same SPA model as Vue, but with JSX syntax and a heavier ecosystem.
- **Difficulty**: Medium, same as Vue — but React is arguably more verbose for this type of form-heavy UI (more boilerplate for state management, no built-in two-way binding).
- **Verdict**: Only prefer React if there's existing familiarity with it. Vue is a better fit for this scope.

#### Recommendation

**Start with Alpine.js + vanilla fetch** for the fastest path to a working prototype — the whole frontend is a single HTML file with no tooling. If the tag bubble editor or the streaming LLM output becomes unwieldy, migrate to **Vue 3 + Vite** for that component specifically (or for the whole frontend). The backend API stays the same either way.

For this project, **Option 1 is the initial frontend choice**. The first implementation pass should assume:

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
- `images` — id, project_id, filename, original_blob (BLOB), working_blob (BLOB, nullable), width, height, included, parent_image_id
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
- **Dark mode**
- **RAG-assisted captioning** — see section below

---

## RAG / Embedding-Assisted Captioning (Stretch Goal)

**Would ChromaDB or similar RAG tooling be useful here?**

Short answer: yes, with caveats — it's more useful as datasets grow large.

### How it could help

Both Ollama and LM Studio can generate text embeddings (`ollama.embed()`, or LM Studio's embeddings endpoint). These could be stored in a vector store like [ChromaDB](https://www.trychroma.com/) alongside each image's caption, enabling:

- **Few-shot example retrieval** — when generating a caption for a new image, automatically find the `N` most similar already-captioned images (by caption embedding similarity) and inject their captions into the prompt as style examples. This significantly improves consistency across large datasets.
- **Semantic caption search** — search across all captions by meaning rather than exact keywords (e.g., "find all images with outdoor scenes").
- **Consistency enforcement** — detect when a new AI caption uses vocabulary or style that diverges significantly from the rest of the dataset.

### Caveats
- For small datasets (< a few hundred images), the overhead isn't worth it — a keyword search is sufficient.
- ChromaDB runs as an in-process library (no separate server needed for local use), so integration is not heavy.
- Embedding images directly (rather than their captions) would require a CLIP-compatible embedding model, which is a separate dependency. Caption-based embeddings are simpler and likely good enough for style matching.
- This is genuinely more useful once a dataset grows beyond ~500 images or when you want to enforce a consistent captioning style across a large set.

### Suggested approach
Add ChromaDB as an optional dependency. If installed, enable a "RAG mode" in the captioning workflow that retrieves similar captions and adds them to the prompt automatically. The collection can be rebuilt on demand from the current database.

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