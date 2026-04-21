from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.routers import captions, health, images, llm, projects

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(images.router)
app.include_router(captions.router)
app.include_router(llm.router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
