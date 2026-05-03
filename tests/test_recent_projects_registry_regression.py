from __future__ import annotations

from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import app

client = TestClient(app)


def test_recent_projects_endpoint_handles_empty_registry_file() -> None:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.recent_projects_path.write_text("", encoding="utf-8")

    response = client.get("/api/projects/recent")

    assert response.status_code == 200, response.text
    assert response.json() == {"projects": []}


def test_recent_projects_endpoint_handles_malformed_registry_file() -> None:
    settings = get_settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.recent_projects_path.write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/projects/recent")

    assert response.status_code == 200, response.text
    assert response.json() == {"projects": []}
