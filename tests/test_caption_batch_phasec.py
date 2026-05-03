from __future__ import annotations

import sqlite3
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
            name="Caption Batch",
            description="phase c",
            trigger_word="",
            caption_mode="description",
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
            width=48,
            height=48,
            included=False,
        )
        session.add(image_one)
        session.add(image_two)
        session.flush()

        session.add(
            CaptionRecord(
                image_id=image_one.id,
                text="alpha bear and alpha scarf",
                is_active=True,
                source="manual",
            )
        )
        session.add(
            CaptionRecord(
                image_id=image_one.id,
                text="inactive alpha caption",
                is_active=False,
                source="manual",
            )
        )
        session.add(
            CaptionRecord(
                image_id=image_two.id,
                text="alpha hidden image",
                is_active=True,
                source="manual",
            )
        )
        session.commit()

        return {
            "image_one_id": image_one.id,
            "image_two_id": image_two.id,
        }


def test_preview_replace_scoped_to_active_and_included(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    response = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "active_only",
                "image_scope": "included_only",
            },
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["impacted_captions_count"] == 1
    assert payload["impacted_images_count"] == 1
    assert payload["warnings"] == []

    sample = payload["sample_changes"][0]
    assert sample["image_id"] == ids["image_one_id"]
    assert "beta bear" in sample["after_preview"]


def test_apply_replace_requires_confirm(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    _create_project_db(project_path=project_path)

    preview_response = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "all_candidates",
                "image_scope": "all",
            },
        },
    )
    assert preview_response.status_code == 200, preview_response.text
    preview_id = preview_response.json()["preview_id"]

    apply_response = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": preview_id,
            "confirm": False,
            "create_undo_snapshot": True,
        },
    )
    assert apply_response.status_code == 400, apply_response.text


def test_apply_and_undo_replace_round_trip(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    preview_response = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "all_candidates",
                "image_scope": "selected_ids",
                "image_ids": [ids["image_one_id"]],
            },
        },
    )
    assert preview_response.status_code == 200, preview_response.text
    preview_payload = preview_response.json()
    assert preview_payload["impacted_captions_count"] == 2

    apply_response = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": preview_payload["preview_id"],
            "confirm": True,
            "create_undo_snapshot": True,
        },
    )
    assert apply_response.status_code == 200, apply_response.text
    apply_payload = apply_response.json()
    assert apply_payload["updated_captions_count"] == 2
    assert apply_payload["updated_images_count"] == 1
    assert apply_payload["undo_available"] is True

    image_response = client.get(
        f"/api/images/{ids['image_one_id']}",
        params={"project_path": str(project_path)},
    )
    assert image_response.status_code == 200, image_response.text
    captions = image_response.json()["image"]["captions"]
    assert all("beta" in caption["text"] for caption in captions)

    undo_response = client.post(
        "/api/captions/batch/undo",
        json={
            "project_path": str(project_path),
            "operation_id": apply_payload["operation_id"],
        },
    )
    assert undo_response.status_code == 200, undo_response.text
    assert undo_response.json()["restored_captions_count"] == 2

    second_undo_response = client.post(
        "/api/captions/batch/undo",
        json={
            "project_path": str(project_path),
            "operation_id": apply_payload["operation_id"],
        },
    )
    assert second_undo_response.status_code == 409, second_undo_response.text

    restored_image_response = client.get(
        f"/api/images/{ids['image_one_id']}",
        params={"project_path": str(project_path)},
    )
    assert restored_image_response.status_code == 200, restored_image_response.text
    restored_captions = restored_image_response.json()["image"]["captions"]
    assert any("alpha bear" in caption["text"] for caption in restored_captions)


def test_apply_replace_rejects_expired_preview(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    _create_project_db(project_path=project_path)

    preview_response = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "active_only",
                "image_scope": "all",
            },
        },
    )
    assert preview_response.status_code == 200, preview_response.text
    preview_id = preview_response.json()["preview_id"]

    connection = sqlite3.connect(project_path)
    try:
        connection.execute(
            "UPDATE caption_batch_previews SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (preview_id,),
        )
        connection.commit()
    finally:
        connection.close()

    apply_response = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": preview_id,
            "confirm": True,
            "create_undo_snapshot": True,
        },
    )
    assert apply_response.status_code == 409, apply_response.text


def test_batch_operations_history_reports_apply_and_undo_state(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    preview_response = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "all_candidates",
                "image_scope": "selected_ids",
                "image_ids": [ids["image_one_id"]],
            },
        },
    )
    assert preview_response.status_code == 200, preview_response.text

    apply_response = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": preview_response.json()["preview_id"],
            "confirm": True,
            "create_undo_snapshot": True,
        },
    )
    assert apply_response.status_code == 200, apply_response.text
    operation_id = apply_response.json()["operation_id"]

    operations_response = client.get(
        "/api/captions/batch/operations",
        params={"project_path": str(project_path), "limit": 10},
    )
    assert operations_response.status_code == 200, operations_response.text
    operations = operations_response.json()["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_id"] == operation_id
    assert operations[0]["type"] == "replace"
    assert operations[0]["impacted_captions_count"] == 2
    assert operations[0]["impacted_images_count"] == 1
    assert operations[0]["undone_at"] is None

    undo_response = client.post(
        "/api/captions/batch/undo",
        json={
            "project_path": str(project_path),
            "operation_id": operation_id,
        },
    )
    assert undo_response.status_code == 200, undo_response.text

    post_undo_operations_response = client.get(
        "/api/captions/batch/operations",
        params={"project_path": str(project_path), "limit": 10},
    )
    assert post_undo_operations_response.status_code == 200, post_undo_operations_response.text
    post_undo_operations = post_undo_operations_response.json()["operations"]
    assert len(post_undo_operations) == 1
    assert post_undo_operations[0]["operation_id"] == operation_id
    assert post_undo_operations[0]["undone_at"] is not None


def test_undo_latest_supports_multi_step_history(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    ids = _create_project_db(project_path=project_path)

    first_preview = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "alpha",
                "replace_text": "beta",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "active_only",
                "image_scope": "selected_ids",
                "image_ids": [ids["image_one_id"]],
            },
        },
    )
    assert first_preview.status_code == 200, first_preview.text

    first_apply = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": first_preview.json()["preview_id"],
            "confirm": True,
            "create_undo_snapshot": True,
        },
    )
    assert first_apply.status_code == 200, first_apply.text

    second_preview = client.post(
        "/api/captions/batch/preview-replace",
        json={
            "project_path": str(project_path),
            "query": {
                "find_text": "beta",
                "replace_text": "gamma",
                "mode": "plain",
                "case_sensitive": False,
            },
            "scope": {
                "caption_scope": "active_only",
                "image_scope": "selected_ids",
                "image_ids": [ids["image_one_id"]],
            },
        },
    )
    assert second_preview.status_code == 200, second_preview.text

    second_apply = client.post(
        "/api/captions/batch/apply-replace",
        json={
            "project_path": str(project_path),
            "preview_id": second_preview.json()["preview_id"],
            "confirm": True,
            "create_undo_snapshot": True,
        },
    )
    assert second_apply.status_code == 200, second_apply.text

    # Undo latest should undo second operation first.
    undo_latest_one = client.post(
        "/api/captions/batch/undo",
        json={"project_path": str(project_path)},
    )
    assert undo_latest_one.status_code == 200, undo_latest_one.text
    assert undo_latest_one.json()["undone_operation_id"] == second_apply.json()["operation_id"]

    # A second undo-latest should continue to the previous undoable operation.
    undo_latest_two = client.post(
        "/api/captions/batch/undo",
        json={"project_path": str(project_path)},
    )
    assert undo_latest_two.status_code == 200, undo_latest_two.text
    assert undo_latest_two.json()["undone_operation_id"] == first_apply.json()["operation_id"]
