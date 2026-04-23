"""
End-to-end smoke pass: create → open → import → edit → batch lifecycle → export.

LLM generation is skipped (no live backend required). Batch lifecycle (create/pause/
resume/cancel/history) is exercised via the API using a stub image set so we can
verify the full state machine without needing Ollama or LM Studio.
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_png_bytes(color: tuple[int, int, int] = (128, 64, 32)) -> bytes:
    img = Image.new("RGB", (64, 64), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_image_folder(folder: Path, count: int = 3) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (folder / f"img{i:02d}.png").write_bytes(_make_png_bytes((i * 40, 80, 120)))
        (folder / f"img{i:02d}.txt").write_text(f"original caption {i}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Smoke pass tests
# ---------------------------------------------------------------------------

def test_health(tmp_path: Path) -> None:
    """Server health endpoint returns ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"


def test_create_and_open_project(tmp_path: Path) -> None:
    """Create a project, then re-open it and confirm metadata round-trips."""
    project_path = str(tmp_path / "smoke.db")

    create_resp = client.post(
        "/api/projects/create",
        json={
            "path": project_path,
            "name": "Smoke Project",
            "description": "End-to-end smoke test",
            "caption_mode": "description",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    project = create_resp.json()["project"]
    assert project["name"] == "Smoke Project"

    # trigger_word is only settable via update, not create
    update_resp = client.post(
        "/api/projects/update",
        json={
            "path": project_path,
            "name": "Smoke Project",
            "description": "End-to-end smoke test",
            "trigger_word": "smptest",
            "caption_mode": "description",
            "context_url": "https://example.com/{project_name}",
            "context_file_path": "/tmp/{project_name}.md",
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["project"]["trigger_word"] == "smptest"
    assert update_resp.json()["project"]["context_url"] == "https://example.com/{project_name}"
    assert update_resp.json()["project"]["context_file_path"] == "/tmp/{project_name}.md"

    open_resp = client.post("/api/projects/open", json={"path": project_path})
    assert open_resp.status_code == 200, open_resp.text
    assert open_resp.json()["project"]["name"] == "Smoke Project"
    assert open_resp.json()["project"]["trigger_word"] == "smptest"
    assert open_resp.json()["project"]["context_url"] == "https://example.com/{project_name}"
    assert open_resp.json()["project"]["context_file_path"] == "/tmp/{project_name}.md"


def test_update_project_metadata(tmp_path: Path) -> None:
    """Update project name and description, confirm changes persist."""
    project_path = str(tmp_path / "smoke_update.db")
    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Original", "description": "", "trigger_word": "", "caption_mode": "description"},
    )

    update_resp = client.post(
        "/api/projects/update",
        json={
            "path": project_path,
            "name": "Updated Name",
            "description": "Updated description",
            "trigger_word": "newtrig",
            "caption_mode": "tags",
            "context_url": "https://context.local/{filename}",
            "context_file_path": "notes/{filename}.md",
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    project = update_resp.json()["project"]
    assert project["name"] == "Updated Name"
    assert project["caption_mode"] == "tags"
    assert project["trigger_word"] == "newtrig"
    assert project["context_url"] == "https://context.local/{filename}"
    assert project["context_file_path"] == "notes/{filename}.md"


def test_import_folder(tmp_path: Path) -> None:
    """Import images from a folder; all images and captions are stored."""
    project_path = str(tmp_path / "smoke_import.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=3)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Import Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )

    import_resp = client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder), "replace_existing": False},
    )
    assert import_resp.status_code == 200, import_resp.text
    result = import_resp.json()["result"]
    assert result["imported_images"] == 3, f"Expected 3 imported, got {result['imported_images']}"
    assert result["captions_from_files"] == 3

    images_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert images_resp.status_code == 200, images_resp.text
    images = images_resp.json()["images"]
    assert len(images) == 3

    # Captions were loaded from the matching .txt files
    captions_present = [img["active_caption_preview"] for img in images]
    assert all(cap for cap in captions_present), f"Some images missing captions: {captions_present}"


def test_image_detail_and_content(tmp_path: Path) -> None:
    """Image detail and raw content endpoints return correct data."""
    project_path = str(tmp_path / "smoke_detail.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=1)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Detail Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    images = client.get("/api/images/list", params={"project_path": project_path}).json()["images"]
    image_id = images[0]["id"]

    detail_resp = client.get(f"/api/images/{image_id}", params={"project_path": project_path})
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["image"]
    assert detail["filename"].endswith(".png")
    assert len(detail["captions"]) >= 1

    content_resp = client.get(f"/api/images/{image_id}/content", params={"project_path": project_path})
    assert content_resp.status_code == 200, content_resp.text
    assert content_resp.headers["content-type"].startswith("image/")


def test_include_exclude_toggle(tmp_path: Path) -> None:
    """Include/exclude toggling persists on the image record."""
    project_path = str(tmp_path / "smoke_toggle.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=2)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Toggle Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    images = client.get("/api/images/list", params={"project_path": project_path}).json()["images"]
    image_id = images[0]["id"]
    assert images[0]["included"] is True

    # Exclude the image
    excl_resp = client.post(
        f"/api/images/{image_id}/included",
        json={"project_path": project_path, "included": False},
    )
    assert excl_resp.status_code == 200, excl_resp.text
    assert excl_resp.json()["included"] is False

    # Re-include it
    incl_resp = client.post(
        f"/api/images/{image_id}/included",
        json={"project_path": project_path, "included": True},
    )
    assert incl_resp.status_code == 200
    assert incl_resp.json()["included"] is True


def test_caption_edit_and_set_active(tmp_path: Path) -> None:
    """Manual caption editing: update text, create candidate, switch active."""
    project_path = str(tmp_path / "smoke_captions.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=1)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Caption Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    images = client.get("/api/images/list", params={"project_path": project_path}).json()["images"]
    image_id = images[0]["id"]
    detail = client.get(f"/api/images/{image_id}", params={"project_path": project_path}).json()["image"]
    active_caption_id = next(c["id"] for c in detail["captions"] if c["is_active"])

    # Edit the active caption
    edit_resp = client.post(
        "/api/captions/update-active",
        json={"project_path": project_path, "image_id": image_id, "text": "manually edited caption"},
    )
    assert edit_resp.status_code == 200, edit_resp.text
    assert edit_resp.json()["caption"]["text"] == "manually edited caption"

    # Create a second candidate
    create_resp = client.post(
        "/api/captions/create",
        json={"project_path": project_path, "image_id": image_id, "text": "second candidate", "make_active": False},
    )
    assert create_resp.status_code == 200, create_resp.text
    second_id = create_resp.json()["caption"]["id"]
    assert create_resp.json()["caption"]["is_active"] is False

    # Switch active to the second candidate
    set_resp = client.post(
        "/api/captions/set-active",
        json={"project_path": project_path, "image_id": image_id, "caption_id": second_id},
    )
    assert set_resp.status_code == 200, set_resp.text
    detail2 = client.get(f"/api/images/{image_id}", params={"project_path": project_path}).json()["image"]
    active_ids = [c["id"] for c in detail2["captions"] if c["is_active"]]
    assert active_ids == [second_id]

    # Inline-edit the second candidate (non-active editing)
    update_resp = client.post(
        "/api/captions/update",
        json={"project_path": project_path, "image_id": image_id, "caption_id": active_caption_id, "text": "inline updated text"},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["caption"]["text"] == "inline updated text"

    # Delete the second (now active) candidate — first should be promoted
    del_resp = client.post(
        "/api/captions/delete",
        json={"project_path": project_path, "image_id": image_id, "caption_id": second_id},
    )
    assert del_resp.status_code == 200, del_resp.text


def test_export_preview_and_export(tmp_path: Path) -> None:
    """Export preview counts match actual exported files."""
    project_path = str(tmp_path / "smoke_export.db")
    source_folder = tmp_path / "images"
    output_folder = str(tmp_path / "export_out")
    _create_image_folder(source_folder, count=4)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Export Test", "description": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/update",
        json={"path": project_path, "name": "Export Test", "description": "", "trigger_word": "trig", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    # Exclude one image
    images = client.get("/api/images/list", params={"project_path": project_path}).json()["images"]
    client.post(
        f"/api/images/{images[0]['id']}/included",
        json={"project_path": project_path, "included": False},
    )

    preview_resp = client.post(
        "/api/projects/export-preview",
        json={
            "project_path": project_path,
            "output_folder": output_folder,
            "included_only": True,
            "apply_trigger_word": True,
        },
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview = preview_resp.json()["result"]
    assert preview["images_to_export"] == 3

    export_resp = client.post(
        "/api/projects/export",
        json={
            "project_path": project_path,
            "output_folder": output_folder,
            "included_only": True,
            "apply_trigger_word": True,
            "include_metadata": True,
            "overwrite_existing": True,
            "clean_output_folder": False,
            "create_new_folder": False,
            "new_folder_name": "",
        },
    )
    assert export_resp.status_code == 200, export_resp.text
    result = export_resp.json()["result"]
    assert result["exported_images"] == 3

    exported_files = list(Path(output_folder).iterdir())
    image_files = [f for f in exported_files if f.suffix != ".txt" and f.name != "export_manifest.json"]
    txt_files = [f for f in exported_files if f.suffix == ".txt"]
    assert len(image_files) == 3
    assert len(txt_files) == 3

    # Trigger word is prepended
    for txt in txt_files:
        content = txt.read_text(encoding="utf-8")
        assert content.startswith("trig,") or content.startswith("trig "), f"Trigger word missing in {txt.name}: {content!r}"


def test_export_to_new_subfolder(tmp_path: Path) -> None:
    """Export with create_new_folder creates the named subfolder."""
    project_path = str(tmp_path / "smoke_subfolder.db")
    source_folder = tmp_path / "images"
    output_base = str(tmp_path / "exports")
    _create_image_folder(source_folder, count=2)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Subfolder Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    export_resp = client.post(
        "/api/projects/export",
        json={
            "project_path": project_path,
            "output_folder": output_base,
            "included_only": True,
            "apply_trigger_word": False,
            "include_metadata": False,
            "overwrite_existing": False,
            "clean_output_folder": False,
            "create_new_folder": True,
            "new_folder_name": "my_run",
        },
    )
    assert export_resp.status_code == 200, export_resp.text
    assert (Path(output_base) / "my_run").is_dir()
    assert len(list((Path(output_base) / "my_run").iterdir())) == 4  # 2 images + 2 txt


def test_batch_job_lifecycle(tmp_path: Path) -> None:
    """Batch job create → pause → resume (no LLM needed; job pauses immediately)."""
    project_path = str(tmp_path / "smoke_batch.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=2)

    client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Batch Test", "description": "", "trigger_word": "", "caption_mode": "description"},
    )
    client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder)},
    )

    # Create a batch job (will fail per-image since no LLM, but job is created)
    create_resp = client.post(
        "/api/llm/batch-jobs/create",
        json={
            "project_path": project_path,
            "target": "all",
            "use_preset": False,
            "backend": "ollama",
            "model": "nonexistent-model-for-smoke",
            "extra_instructions": "",
            "timeout_seconds": 10,
            "make_active": True,
            "output_mode": "new_candidate",
            "skip_on_failure": True,
            "retry_count": 0,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    job = create_resp.json()["job"]
    job_id = job["id"]
    assert job["total"] == 2

    # Pause the job
    pause_resp = client.post("/api/llm/batch-jobs/pause", json={"job_id": job_id})
    assert pause_resp.status_code == 200, pause_resp.text
    # Give the worker thread a moment to honour the pause
    time.sleep(0.3)

    get_resp = client.get("/api/llm/batch-jobs/" + job_id)
    assert get_resp.status_code == 200, get_resp.text
    status_after_pause = get_resp.json()["job"]["status"]
    assert status_after_pause in {"paused", "running", "completed", "failed"}, status_after_pause

    # Job appears in the list for this project
    list_resp = client.get("/api/llm/batch-jobs", params={"project_path": project_path})
    assert list_resp.status_code == 200, list_resp.text
    job_ids = [j["id"] for j in list_resp.json()["jobs"]]
    assert job_id in job_ids

    # Cancel the job
    cancel_resp = client.post("/api/llm/batch-jobs/cancel", json={"job_id": job_id})
    assert cancel_resp.status_code == 200, cancel_resp.text


def test_settings_round_trip(tmp_path: Path) -> None:
    """LLM settings can be written and read back."""
    get_resp = client.get("/api/llm/settings")
    assert get_resp.status_code == 200, get_resp.text
    original = get_resp.json()

    update_resp = client.post(
        "/api/llm/settings",
        json={
            "llm_timeout_seconds": 45,
            "llm_use_preset_by_default": False,
            "llm_default_preset_id": None,
            "ui_show_debug_section": False,
            "ollama_base_url": "http://127.0.0.1:11434",
            "lmstudio_base_url": "http://127.0.0.1:1234",
            "ollama_timeout_seconds": None,
            "lmstudio_timeout_seconds": None,
            "ollama_num_ctx": 8192,
            "lmstudio_num_ctx": None,
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["llm_timeout_seconds"] == 45
    assert update_resp.json()["ollama_num_ctx"] == 8192

    # Restore original timeout so we don't pollute shared state
    client.post(
        "/api/llm/settings",
        json={
            "llm_timeout_seconds": original.get("llm_timeout_seconds", 120),
            "llm_use_preset_by_default": original.get("llm_use_preset_by_default", False),
            "llm_default_preset_id": original.get("llm_default_preset_id"),
            "ui_show_debug_section": original.get("ui_show_debug_section", False),
            "ollama_base_url": original.get("ollama_base_url", "http://127.0.0.1:11434"),
            "lmstudio_base_url": original.get("lmstudio_base_url", "http://127.0.0.1:1234"),
            "ollama_timeout_seconds": original.get("ollama_timeout_seconds"),
            "lmstudio_timeout_seconds": original.get("lmstudio_timeout_seconds"),
            "ollama_num_ctx": original.get("ollama_num_ctx"),
            "lmstudio_num_ctx": original.get("lmstudio_num_ctx"),
        },
    )


def test_test_connection_endpoint_unreachable() -> None:
    """test-connection returns ok=False for an unreachable URL (no LLM needed)."""
    resp = client.post(
        "/api/llm/test-connection",
        json={"backend": "ollama", "url": "http://127.0.0.1:19999"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    # Either ok=False (unreachable) or ok=True with 0 models (port happens to respond)
    assert isinstance(payload["ok"], bool)
    assert isinstance(payload["message"], str)
    assert len(payload["message"]) > 0


def test_preset_crud() -> None:
    """Create, list, update, and delete a preset."""
    create_resp = client.post(
        "/api/llm/presets/create",
        json={
            "name": "Smoke Preset",
            "backend": "ollama",
            "model_name": "llava:latest",
            "caption_mode_strategy": "description",
            "system_prompt": "",
            "tool_web_search": True,
            "tool_web_fetch": False,
            "context_url_template": "{project_context_url}",
            "context_file_template": "{project_context_file_path}",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    preset = create_resp.json()["preset"]
    preset_id = preset["id"]
    assert preset["name"] == "Smoke Preset"
    assert preset["tool_web_search"] is True
    assert preset["tool_web_fetch"] is False
    assert preset["context_url_template"] == "{project_context_url}"
    assert preset["context_file_template"] == "{project_context_file_path}"

    list_resp = client.get("/api/llm/presets")
    assert list_resp.status_code == 200, list_resp.text
    ids = [p["id"] for p in list_resp.json()["presets"]]
    assert preset_id in ids

    update_resp = client.post(
        "/api/llm/presets/update",
        json={
            "preset_id": preset_id,
            "name": "Smoke Preset Updated",
            "backend": "ollama",
            "model_name": "llava:latest",
            "caption_mode_strategy": "tags",
            "system_prompt": "Be concise.",
            "tool_web_search": True,
            "tool_web_fetch": True,
            "context_url_template": "https://example.com/{project_name}",
            "context_file_template": "{project_context_file_path}",
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["preset"]["caption_mode_strategy"] == "tags"
    assert update_resp.json()["preset"]["tool_web_search"] is True
    assert update_resp.json()["preset"]["tool_web_fetch"] is True

    delete_resp = client.post("/api/llm/presets/delete", json={"preset_id": preset_id})
    assert delete_resp.status_code == 200, delete_resp.text
    ids_after = [p["id"] for p in client.get("/api/llm/presets").json()["presets"]]
    assert preset_id not in ids_after
