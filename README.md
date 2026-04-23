# describe_it

Local tool for building and managing captioned image datasets with manual editing and AI-assisted caption generation.

## Features

- Import images from a folder; source files are never modified
- Manual caption editing with multiple caption candidates per image
- AI caption generation via Ollama or LM Studio (vision models)
- Configurable presets with caption mode strategy (description or tags)
- Batch generation across all or selected images with pause/resume support
- Export to flat folder of image + `.txt` pairs, ready for training
- Optional semantic search and RAG-assisted generation via ChromaDB

## Quick Start

1. Create and activate the local virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. Install base dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python run.py
```

The browser opens automatically when the server is ready. If it does not, go to http://127.0.0.1:7860.

## Optional: Semantic Search

Install ChromaDB to enable RAG-assisted caption generation:

```bash
pip install -r requirements-optional.txt
```

See [PHASE_7_RAG_GUIDE.md](PHASE_7_RAG_GUIDE.md) for setup and usage.

## Guides

- [BATCH_GUIDE.md](BATCH_GUIDE.md) — Presets, caption modes, backend settings, and batch workflows
- [PHASE_6_EXPORT_GUIDE.md](PHASE_6_EXPORT_GUIDE.md) — Exporting datasets for training
- [PHASE_7_RAG_GUIDE.md](PHASE_7_RAG_GUIDE.md) — Semantic search and RAG integration

