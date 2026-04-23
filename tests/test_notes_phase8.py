from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_project_notes_crud(tmp_path: Path) -> None:
    project_path = str(tmp_path / "notes_project.db")

    create_project = client.post(
        "/api/projects/create",
        json={
            "path": project_path,
            "name": "Notes Project",
            "description": "",
        },
    )
    assert create_project.status_code == 200, create_project.text

    create_note = client.post(
        "/api/notes/create",
        json={
            "project_path": project_path,
            "title": "style guide",
            "content": "use concise language",
            "format": "markdown",
            "tags": "style,voice",
        },
    )
    assert create_note.status_code == 200, create_note.text
    note = create_note.json()["note"]
    note_id = note["id"]
    assert note["title"] == "style guide"
    assert note["is_archived"] is False

    list_notes = client.get("/api/notes", params={"project_path": project_path})
    assert list_notes.status_code == 200, list_notes.text
    notes = list_notes.json()["notes"]
    assert any(item["id"] == note_id for item in notes)

    update_note = client.post(
        "/api/notes/update",
        json={
            "project_path": project_path,
            "note_id": note_id,
            "title": "style guide updated",
            "content": "use concise language and active voice",
            "format": "text",
            "tags": "style",
            "is_archived": True,
        },
    )
    assert update_note.status_code == 200, update_note.text
    updated = update_note.json()["note"]
    assert updated["format"] == "text"
    assert updated["is_archived"] is True

    unarchived_list = client.get(
        "/api/notes",
        params={"project_path": project_path, "include_archived": False},
    )
    assert unarchived_list.status_code == 200, unarchived_list.text
    assert all(item["id"] != note_id for item in unarchived_list.json()["notes"])

    delete_note = client.post(
        "/api/notes/delete",
        json={"project_path": project_path, "note_id": note_id},
    )
    assert delete_note.status_code == 200, delete_note.text
    assert delete_note.json()["deleted_note_id"] == note_id


def test_global_notes_crud() -> None:
    create_note = client.post(
        "/api/global-notes/create",
        json={
            "title": "program-wide policy",
            "content": "global reference note",
            "format": "markdown",
            "tags": "global",
        },
    )
    assert create_note.status_code == 200, create_note.text
    note = create_note.json()["note"]
    note_id = note["id"]

    list_notes = client.get("/api/global-notes")
    assert list_notes.status_code == 200, list_notes.text
    assert any(item["id"] == note_id for item in list_notes.json()["notes"])

    update_note = client.post(
        "/api/global-notes/update",
        json={
            "note_id": note_id,
            "title": "program-wide policy v2",
            "content": "global reference note updated",
            "format": "text",
            "tags": "global,policy",
            "is_archived": True,
        },
    )
    assert update_note.status_code == 200, update_note.text
    updated = update_note.json()["note"]
    assert updated["is_archived"] is True
    assert updated["format"] == "text"

    unarchived_list = client.get("/api/global-notes", params={"include_archived": False})
    assert unarchived_list.status_code == 200, unarchived_list.text
    assert all(item["id"] != note_id for item in unarchived_list.json()["notes"])

    delete_note = client.post("/api/global-notes/delete", json={"note_id": note_id})
    assert delete_note.status_code == 200, delete_note.text
    assert delete_note.json()["deleted_note_id"] == note_id
