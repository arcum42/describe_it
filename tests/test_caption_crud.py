from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database
from backend.main import app


client = TestClient(app)


def _create_project_db(*, project_path: Path) -> dict[str, int]:
    initialize_database(project_path)
    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        project = ProjectRecord(
            name="Caption CRUD",
            description="caption test",
            trigger_word="",
            caption_mode="description",
        )
        session.add(project)
        session.flush()

        image = ImageRecord(
            project_id=project.id,
            filename="img.png",
            original_blob=b"img-data",
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        session.add(image)
        session.flush()

        first = CaptionRecord(image_id=image.id, text="first caption", is_active=True, source="manual")
        second = CaptionRecord(image_id=image.id, text="second caption", is_active=False, source="manual")
        session.add(first)
        session.add(second)
        session.commit()

        return {"image_id": image.id, "first_caption_id": first.id, "second_caption_id": second.id}


def test_update_caption_by_id(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    response = client.post(
        "/api/captions/update",
        json={
            "project_path": str(project_path),
            "image_id": ids["image_id"],
            "caption_id": ids["second_caption_id"],
            "text": "updated second caption",
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["caption"]["id"] == ids["second_caption_id"]
    assert payload["caption"]["text"] == "updated second caption"
    assert payload["caption"]["is_active"] is False


def test_delete_active_caption_promotes_remaining_candidate(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    response = client.post(
        "/api/captions/delete",
        json={
            "project_path": str(project_path),
            "image_id": ids["image_id"],
            "caption_id": ids["first_caption_id"],
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["deleted_caption_id"] == ids["first_caption_id"]
    assert payload["active_caption_id"] == ids["second_caption_id"]

    detail_response = client.get(
        f"/api/images/{ids['image_id']}",
        params={"project_path": str(project_path)},
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()["image"]
    assert len(detail["captions"]) == 1
    assert detail["captions"][0]["id"] == ids["second_caption_id"]
    assert detail["captions"][0]["is_active"] is True
