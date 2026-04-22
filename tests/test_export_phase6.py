from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database
from backend.main import app


client = TestClient(app)


def _create_project_db(
    *,
    project_path: Path,
    trigger_word: str,
    images: list[dict[str, object]],
) -> None:
    initialize_database(project_path)
    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        project = ProjectRecord(
            name="Test Project",
            description="export regression",
            trigger_word=trigger_word,
            caption_mode="description",
        )
        session.add(project)
        session.flush()

        for item in images:
            image = ImageRecord(
                project_id=project.id,
                filename=str(item["filename"]),
                original_blob=item.get("blob"),
                working_blob=None,
                width=32,
                height=32,
                included=bool(item.get("included", True)),
            )
            session.add(image)
            session.flush()

            caption = CaptionRecord(
                image_id=image.id,
                text=str(item.get("caption", "")),
                is_active=True,
                source="manual",
            )
            session.add(caption)

        session.commit()


def _post_json(path: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, dict)
    return data


def test_export_applies_trigger_word_when_present(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    output_folder = tmp_path / "out"

    _create_project_db(
        project_path=project_path,
        trigger_word="trigger_token",
        images=[
            {"filename": "img_a.png", "blob": b"img-a", "included": True, "caption": "a cat on a mat"},
        ],
    )

    payload = {
        "project_path": str(project_path),
        "output_folder": str(output_folder),
        "included_only": True,
        "apply_trigger_word": True,
        "include_metadata": False,
        "overwrite_existing": False,
        "clean_output_folder": False,
        "create_new_folder": False,
        "new_folder_name": "",
    }
    result = _post_json("/api/projects/export", payload)["result"]

    assert result["exported_images"] == 1
    assert result["trigger_word_applied"] is True

    caption_path = output_folder / "img_a.txt"
    assert caption_path.exists()
    caption = caption_path.read_text(encoding="utf-8")
    assert caption == "trigger_token, a cat on a mat"


def test_export_collision_overwrite_clean_behaviors(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    output_folder = tmp_path / "out"

    _create_project_db(
        project_path=project_path,
        trigger_word="",
        images=[
            {"filename": "img_a.png", "blob": b"img-a", "included": True, "caption": "first caption"},
        ],
    )

    base_payload = {
        "project_path": str(project_path),
        "output_folder": str(output_folder),
        "included_only": True,
        "apply_trigger_word": False,
        "include_metadata": False,
        "create_new_folder": False,
        "new_folder_name": "",
    }

    first = _post_json(
        "/api/projects/export",
        {
            **base_payload,
            "overwrite_existing": False,
            "clean_output_folder": False,
        },
    )["result"]
    assert first["exported_images"] == 1
    assert first["skipped_due_to_collision"] == 0

    second = _post_json(
        "/api/projects/export",
        {
            **base_payload,
            "overwrite_existing": False,
            "clean_output_folder": False,
        },
    )["result"]
    assert second["exported_images"] == 0
    assert second["skipped_due_to_collision"] == 1

    overwrite = _post_json(
        "/api/projects/export",
        {
            **base_payload,
            "overwrite_existing": True,
            "clean_output_folder": False,
        },
    )["result"]
    assert overwrite["exported_images"] == 1

    (output_folder / "orphan.txt").write_text("stale", encoding="utf-8")
    cleaned = _post_json(
        "/api/projects/export",
        {
            **base_payload,
            "overwrite_existing": False,
            "clean_output_folder": True,
        },
    )["result"]
    assert cleaned["exported_images"] == 1
    assert not (output_folder / "orphan.txt").exists()

    bad = client.post(
        "/api/projects/export",
        json={
            **base_payload,
            "overwrite_existing": True,
            "clean_output_folder": True,
        },
    )
    assert bad.status_code == 400
    assert "Choose either clean output folder or overwrite existing files" in bad.text


def test_export_preview_counts_match_export_results(tmp_path: Path) -> None:
    project_path = tmp_path / "project.db"
    output_root = tmp_path / "exports"

    _create_project_db(
        project_path=project_path,
        trigger_word="",
        images=[
            {"filename": "good.png", "blob": b"good", "included": True, "caption": ""},
            {"filename": "missing.png", "blob": None, "included": True, "caption": "missing blob"},
            {"filename": "excluded.png", "blob": b"excluded", "included": False, "caption": "excluded"},
        ],
    )

    preview_payload = {
        "project_path": str(project_path),
        "output_folder": str(output_root),
        "included_only": True,
        "apply_trigger_word": False,
        "create_new_folder": True,
        "new_folder_name": "run_01",
    }
    preview = _post_json("/api/projects/export-preview", preview_payload)["result"]

    assert preview["images_to_export"] == 1
    assert preview["excluded_images"] == 1
    assert preview["blank_captions"] == 1
    assert preview["would_overwrite"] is False

    export = _post_json(
        "/api/projects/export",
        {
            **preview_payload,
            "include_metadata": True,
            "overwrite_existing": False,
            "clean_output_folder": False,
        },
    )["result"]

    assert export["exported_images"] == preview["images_to_export"]
    assert export["skipped_missing_blob"] == 1
    assert export["skipped_due_to_collision"] == 0
    assert export["metadata_written"] is True

    manifest_path = Path(export["metadata_file"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["counts"]["exported_images"] == export["exported_images"]
    assert manifest["counts"]["skipped_missing_blob"] == export["skipped_missing_blob"]
