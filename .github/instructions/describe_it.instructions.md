# describe_it Instructions

## Project intent

This project is a local-first dataset captioning tool for image training datasets. Keep the application portable, simple to run, and conservative about destructive operations.

## Runtime contract (do not break)

- A user should be able to run the app with only Python setup:
	- create a virtual environment
	- install `requirements.txt`
	- run `python run.py`
- Do not require Node.js, npm, pnpm, bun, or any frontend build/install step for baseline app usage.

## Frontend direction

- Use plain HTML, CSS, vanilla JavaScript, and Alpine.js.
- Keep the runtime frontend delivery static-first (`frontend/` served by FastAPI).
- Prefer small, understandable UI modules over large framework abstractions.
- It is acceptable to add lightweight frontend libraries/framework helpers when they reduce complexity.
- Preferred integration order for new UI libraries:
	1. CDN include (pin major/minor version where practical).
	2. Vendored static asset in the repo (`frontend/vendor` or similar).
	3. Optional contributor-only build tooling, only if (1) and (2) are not enough.
- If optional frontend tooling is introduced for contributor ergonomics, generated assets must be committed so end users still run with Python-only setup.
- Avoid introducing a required SPA toolchain or mandatory transpilation step for baseline development.

## Frontend organization guidance

- As `frontend/app.js` grows, split by feature area (for example project state, image editor, llm, batch, notes) into small modules.
- Keep fetch/API utilities centralized and consistent in error handling.
- Keep progressive enhancement mindset: core workflows should remain robust even if optional UI niceties fail.

## Backend direction

- Keep the backend in Python.
- Use FastAPI for the HTTP layer.
- Prefer straightforward service modules over premature abstraction.
- Keep project files self-contained and portable.
- Preserve API compatibility where possible; when request/response shapes change, update frontend and tests in the same change.

## Data model expectations

- One SQLite database per project.
- Store source images as BLOBs in the project database.
- Preserve originals; do not mutate imported source images in place.
- Keep ChromaDB optional.

## Dependency policy

- Keep baseline runtime dependencies in `requirements.txt`.
- Put non-baseline or feature-gated dependencies in `requirements-optional.txt`.
- Do not move optional capabilities into required dependencies unless needed for startup or core CRUD flows.

## Development guidelines

- Favor minimal end-to-end slices.
- Add optional dependencies to `requirements-optional.txt` unless they are required for baseline app startup.
- Preserve the existing folder layout unless there is a strong reason to change it.
- Keep future CLI support in mind when writing backend services.
- For behavior changes, add or update focused pytest coverage in `tests/` for API/service regressions.
- Prefer safe file and DB operations; avoid destructive defaults for imports/exports/cleanup flows.
