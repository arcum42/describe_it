# describe_it Instructions

## Project intent

This project is a local-first dataset captioning tool for image training datasets. Keep the application portable, simple to run, and conservative about destructive operations.

## Current frontend direction

- Use plain HTML, CSS, vanilla JavaScript, and Alpine.js.
- Avoid introducing a Node.js build pipeline unless it is clearly justified.
- Prefer small, understandable UI modules over large framework abstractions.

## Backend direction

- Keep the backend in Python.
- Use FastAPI for the HTTP layer.
- Prefer straightforward service modules over premature abstraction.
- Keep project files self-contained and portable.

## Data model expectations

- One SQLite database per project.
- Store source images as BLOBs in the project database.
- Preserve originals; do not mutate imported source images in place.
- Keep ChromaDB optional.

## Development guidelines

- Favor minimal end-to-end slices.
- Add optional dependencies to `requirements-optional.txt` unless they are required for baseline app startup.
- Preserve the existing folder layout unless there is a strong reason to change it.
- Keep future CLI support in mind when writing backend services.
