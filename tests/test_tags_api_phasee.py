from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database
from backend.main import app


client = TestClient(app)


def _create_tags_project_db(*, project_path: Path) -> dict[str, int]:
    initialize_database(project_path)
    session_factory = create_sqlite_session_factory(project_path)

    with session_factory() as session:
        project = ProjectRecord(
            name="Tag API Test",
            description="phase e api",
            trigger_word="",
            caption_mode="tags",
        )
        session.add(project)
        session.flush()

        image_one = ImageRecord(
            project_id=project.id,
            filename="img_1.png",
            original_blob=b"img-data-1",
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        image_two = ImageRecord(
            project_id=project.id,
            filename="img_2.png",
            original_blob=b"img-data-2",
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        image_three = ImageRecord(
            project_id=project.id,
            filename="img_3.png",
            original_blob=b"img-data-3",
            working_blob=None,
            width=32,
            height=32,
            included=False,
        )
        session.add_all([image_one, image_two, image_three])
        session.flush()

        caption_one = CaptionRecord(
            image_id=image_one.id,
            text="red, blue, Alice",
            is_active=True,
            source="manual",
        )
        caption_two = CaptionRecord(
            image_id=image_two.id,
            text="dog, yellow",
            is_active=True,
            source="manual",
        )
        caption_three_excluded = CaptionRecord(
            image_id=image_three.id,
            text="excluded_tag",
            is_active=True,
            source="manual",
        )
        session.add_all([caption_one, caption_two, caption_three_excluded])
        session.commit()

        return {
            "image_one_id": image_one.id,
            "image_two_id": image_two.id,
            "image_three_id": image_three.id,
            "caption_one_id": caption_one.id,
            "caption_two_id": caption_two.id,
            "caption_three_id": caption_three_excluded.id,
        }


def test_get_tags_endpoint_returns_categorized_tags(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api.db"
    ids = _create_tags_project_db(project_path=project_path)

    response = client.get(
        f"/api/captions/tags/{ids['caption_one_id']}",
        params={"project_path": str(project_path)},
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["text"] == "red, blue, Alice"
    assert len(payload["tags"]) == 3
    assert all("tag" in tag for tag in payload["tags"])
    assert all("category" in tag for tag in payload["tags"])


def test_get_tags_endpoint_returns_404_for_missing_caption(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_missing.db"
    _create_tags_project_db(project_path=project_path)

    response = client.get(
        "/api/captions/tags/9999",
        params={"project_path": str(project_path)},
    )
    assert response.status_code == 404, response.text


def test_update_tags_endpoint_persists_updated_text(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_update.db"
    ids = _create_tags_project_db(project_path=project_path)

    update_response = client.post(
        "/api/captions/tags/update",
        json={
            "project_path": str(project_path),
            "caption_id": ids["caption_one_id"],
            "tags": ["green", "furry", "safe"],
        },
    )
    assert update_response.status_code == 200, update_response.text

    payload = update_response.json()
    assert payload["caption_id"] == ids["caption_one_id"]
    assert payload["text"] == "green, furry, safe"

    get_response = client.get(
        f"/api/captions/tags/{ids['caption_one_id']}",
        params={"project_path": str(project_path)},
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["text"] == "green, furry, safe"


def test_batch_tag_operation_add_and_remove(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_batch.db"
    ids = _create_tags_project_db(project_path=project_path)

    add_response = client.post(
        "/api/captions/tags/batch-operation",
        json={
            "project_path": str(project_path),
            "image_ids": [ids["image_one_id"], ids["image_two_id"]],
            "operation": "add",
            "tags": ["new_tag", "Alice"],
        },
    )
    assert add_response.status_code == 200, add_response.text
    add_payload = add_response.json()
    assert add_payload["operation"] == "add"
    assert add_payload["affected_captions"] == 2

    remove_response = client.post(
        "/api/captions/tags/batch-operation",
        json={
            "project_path": str(project_path),
            "image_ids": [ids["image_one_id"], ids["image_two_id"]],
            "operation": "remove",
            "tags": ["blue", "new_tag"],
        },
    )
    assert remove_response.status_code == 200, remove_response.text
    remove_payload = remove_response.json()
    assert remove_payload["operation"] == "remove"
    assert remove_payload["affected_captions"] == 2


def test_batch_tag_operation_clear_requires_confirmed_scope(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_clear.db"
    ids = _create_tags_project_db(project_path=project_path)

    response = client.post(
        "/api/captions/tags/batch-operation",
        json={
            "project_path": str(project_path),
            "image_ids": [ids["image_one_id"], ids["image_two_id"]],
            "operation": "clear",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["operation"] == "clear"
    assert payload["affected_captions"] == 2


def test_batch_tag_operation_reorder_requires_tag_order(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_reorder.db"
    ids = _create_tags_project_db(project_path=project_path)

    response = client.post(
        "/api/captions/tags/batch-operation",
        json={
            "project_path": str(project_path),
            "image_ids": [ids["image_one_id"]],
            "operation": "reorder",
        },
    )
    assert response.status_code == 400, response.text
    assert "Tag order required" in response.text


def test_tag_statistics_excludes_non_included_images(tmp_path: Path) -> None:
    project_path = tmp_path / "tags_api_stats.db"
    _create_tags_project_db(project_path=project_path)

    response = client.get(
        "/api/captions/tags/statistics",
        params={"project_path": str(project_path)},
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["total_occurrences"] == 5
    assert "excluded_tag" not in payload["tag_frequency"]
