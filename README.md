# describe_it

Local tool for building and managing captioned image datasets with manual editing and AI-assisted caption generation.

## Phase 1 Status

This repository currently contains the Phase 1 scaffold:

- FastAPI backend
- Static frontend shell using HTML, CSS, and Alpine.js
- Health endpoint
- Project layout for services, routers, database helpers, and LLM integrations
- Optional dependency split for stretch-goal features like ChromaDB

## Quick Start

1. Create and activate the local virtual environment.
2. Install base dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python run.py
```

4. Open http://127.0.0.1:7860 if the browser does not open automatically.
