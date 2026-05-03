from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_session_state_reopen_round_trip_and_open(tmp_path: Path) -> None:
    """Startup-critical flow: session-state persists and can immediately drive open."""
    project_path = str(tmp_path / "startup_regression.db")

    create_resp = client.post(
        "/api/projects/create",
        json={
            "path": project_path,
            "name": "Startup Regression",
            "description": "",
            "caption_mode": "description",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created_path = create_resp.json()["project"]["path"]

    save_state_resp = client.post(
        "/api/projects/session-state",
        json={
            "last_project_path": created_path,
            "last_project_directory": str(Path(created_path).parent),
            "reopen_last_project": True,
        },
    )
    assert save_state_resp.status_code == 200, save_state_resp.text

    state_resp = client.get("/api/projects/session-state")
    assert state_resp.status_code == 200, state_resp.text
    state = state_resp.json()
    assert state["last_project_path"] == created_path
    assert state["reopen_last_project"] is True

    open_resp = client.post("/api/projects/open", json={"path": state["last_project_path"]})
    assert open_resp.status_code == 200, open_resp.text
    assert open_resp.json()["project"]["path"] == created_path


def test_frontend_startup_order_keeps_reopen_before_deferred_tasks() -> None:
    """Protect the startup ordering fix: reopen happens before deferred async tasks complete."""
    repo_root = Path(__file__).resolve().parents[1]
    app_js = (repo_root / "frontend" / "app.js").read_text(encoding="utf-8")

    anchor_reopen = "await this.autoOpenLastProjectIfNeeded();"
    anchor_deferred_wait = "await Promise.all(deferredStartupTasks);"
    anchor_deferred_decl = "const deferredStartupTasks = ["

    assert anchor_deferred_decl in app_js
    assert anchor_reopen in app_js
    assert anchor_deferred_wait in app_js
    assert app_js.index(anchor_reopen) < app_js.index(anchor_deferred_wait)


def test_frontend_editor_has_last_request_wins_guards() -> None:
    """Protect selection race fix: stale async responses must not overwrite newer user actions."""
    repo_root = Path(__file__).resolve().parents[1]
    editor_js = (repo_root / "frontend" / "js" / "features" / "editor.js").read_text(encoding="utf-8")

    required_tokens = [
        "const requestSeq = (Number(app.loadImagesRequestSeq) || 0) + 1;",
        "if (app.loadImagesRequestSeq !== requestSeq) {",
        "const requestSeq = (Number(app.selectImageRequestSeq) || 0) + 1;",
        "if (app.selectImageRequestSeq !== requestSeq) {",
    ]

    for token in required_tokens:
        assert token in editor_js


def test_frontend_grid_auto_select_behavior_still_exists() -> None:
    """Sanity-check that first-image auto-select logic still exists when nothing is selected."""
    repo_root = Path(__file__).resolve().parents[1]
    editor_js = (repo_root / "frontend" / "js" / "features" / "editor.js").read_text(encoding="utf-8")

    assert "if (app.images.length > 0 && !app.selectedImage) {" in editor_js
    assert "await selectImage(app, app.images[0].id, false);" in editor_js
