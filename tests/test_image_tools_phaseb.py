from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app

client = TestClient(app)


def _make_png_bytes(color: tuple[int, int, int] = (120, 90, 60), size: tuple[int, int] = (48, 48)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_image_folder(folder: Path, count: int = 1) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (folder / f"img{i:02d}.png").write_bytes(_make_png_bytes((i * 30 + 10, 80, 120)))
        (folder / f"img{i:02d}.txt").write_text(f"import caption {i}", encoding="utf-8")


def _create_project_with_one_image(tmp_path: Path) -> tuple[str, int]:
    project_path = str(tmp_path / "phaseb.db")
    source_folder = tmp_path / "images"
    _create_image_folder(source_folder, count=1)

    create_resp = client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Phase B Test", "description": "", "caption_mode": "description"},
    )
    assert create_resp.status_code == 200, create_resp.text

    import_resp = client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder), "replace_existing": False},
    )
    assert import_resp.status_code == 200, import_resp.text

    images_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert images_resp.status_code == 200, images_resp.text
    image_id = images_resp.json()["images"][0]["id"]
    return project_path, image_id


def test_duplicate_image_copies_all_captions_by_default(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    create_caption_resp = client.post(
        "/api/captions/create",
        json={
            "project_path": project_path,
            "image_id": image_id,
            "text": "second candidate",
            "make_active": False,
        },
    )
    assert create_caption_resp.status_code == 200, create_caption_resp.text

    duplicate_resp = client.post(
        f"/api/images/{image_id}/duplicate",
        json={"project_path": project_path},
    )
    assert duplicate_resp.status_code == 200, duplicate_resp.text
    payload = duplicate_resp.json()
    assert payload["source_image_id"] == image_id
    assert payload["copied_caption_count"] == 2
    assert payload["new_image"]["source_image_id"] == image_id
    assert payload["new_image"]["derived_operation"] == "duplicate"

    images_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert images_resp.status_code == 200, images_resp.text
    images = images_resp.json()["images"]
    assert len(images) == 2

    new_image_id = payload["new_image"]["id"]
    detail_resp = client.get(f"/api/images/{new_image_id}", params={"project_path": project_path})
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["image"]
    assert detail["source_image_id"] == image_id
    assert detail["derived_operation"] == "duplicate"
    assert len(detail["captions"]) == 2


def test_soft_delete_hides_image_and_restore_returns_it(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    delete_resp = client.post(
        f"/api/images/{image_id}/delete",
        json={"project_path": project_path, "mode": "soft"},
    )
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["mode"] == "soft"
    assert delete_resp.json()["deleted_at"] is not None

    list_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["images"] == []

    summary_resp = client.get("/api/images/summary", params={"project_path": project_path})
    assert summary_resp.status_code == 200, summary_resp.text
    assert summary_resp.json()["count"] == 0

    detail_resp = client.get(f"/api/images/{image_id}", params={"project_path": project_path})
    assert detail_resp.status_code == 400

    restore_resp = client.post(
        f"/api/images/{image_id}/restore",
        json={"project_path": project_path},
    )
    assert restore_resp.status_code == 200, restore_resp.text
    assert restore_resp.json()["deleted_at"] is None

    list_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert list_resp.status_code == 200, list_resp.text
    assert len(list_resp.json()["images"]) == 1


def test_hard_delete_requires_confirmation_and_removes_image(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    missing_confirm_resp = client.post(
        f"/api/images/{image_id}/delete",
        json={"project_path": project_path, "mode": "hard"},
    )
    assert missing_confirm_resp.status_code == 400
    assert "confirm_hard_delete" in missing_confirm_resp.text

    confirmed_resp = client.post(
        f"/api/images/{image_id}/delete",
        json={"project_path": project_path, "mode": "hard", "confirm_hard_delete": True},
    )
    assert confirmed_resp.status_code == 200, confirmed_resp.text
    assert confirmed_resp.json()["mode"] == "hard"

    list_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["images"] == []

    restore_resp = client.post(
        f"/api/images/{image_id}/restore",
        json={"project_path": project_path},
    )
    assert restore_resp.status_code == 400


def test_crop_and_scale_create_derived_images_with_expected_sizes(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    crop_resp = client.post(
        f"/api/images/{image_id}/crop",
        json={
            "project_path": project_path,
            "rect": {"x": 4, "y": 4, "width": 20, "height": 16},
            "include_captions": True,
            "caption_copy_mode": "active_only",
        },
    )
    assert crop_resp.status_code == 200, crop_resp.text
    crop_payload = crop_resp.json()
    assert crop_payload["new_image"]["derived_operation"] == "crop"
    assert crop_payload["new_image"]["width"] == 20
    assert crop_payload["new_image"]["height"] == 16

    cropped_id = crop_payload["new_image"]["id"]
    cropped_detail_resp = client.get(f"/api/images/{cropped_id}", params={"project_path": project_path})
    assert cropped_detail_resp.status_code == 200, cropped_detail_resp.text
    cropped_detail = cropped_detail_resp.json()["image"]
    assert len(cropped_detail["captions"]) == 1

    scale_resp = client.post(
        f"/api/images/{image_id}/scale",
        json={
            "project_path": project_path,
            "mode": "percent",
            "percent": 50,
        },
    )
    assert scale_resp.status_code == 200, scale_resp.text
    scale_payload = scale_resp.json()
    assert scale_payload["new_image"]["derived_operation"] == "scale"
    assert scale_payload["new_image"]["width"] == 24
    assert scale_payload["new_image"]["height"] == 24


def test_flip_and_rotate_create_derived_images(tmp_path: Path) -> None:
    project_path = str(tmp_path / "phaseb_rotate_flip.db")
    source_folder = tmp_path / "images_rect"
    source_folder.mkdir(parents=True, exist_ok=True)
    (source_folder / "rect.png").write_bytes(_make_png_bytes((20, 140, 200), size=(64, 32)))
    (source_folder / "rect.txt").write_text("rect caption", encoding="utf-8")

    create_resp = client.post(
        "/api/projects/create",
        json={"path": project_path, "name": "Phase B Transform Test", "description": "", "caption_mode": "description"},
    )
    assert create_resp.status_code == 200, create_resp.text

    import_resp = client.post(
        "/api/projects/import-folder",
        json={"project_path": project_path, "source_folder": str(source_folder), "replace_existing": False},
    )
    assert import_resp.status_code == 200, import_resp.text

    list_resp = client.get("/api/images/list", params={"project_path": project_path})
    assert list_resp.status_code == 200, list_resp.text
    image_id = list_resp.json()["images"][0]["id"]

    flip_resp = client.post(
        f"/api/images/{image_id}/flip",
        json={"project_path": project_path, "mode": "horizontal"},
    )
    assert flip_resp.status_code == 200, flip_resp.text
    flip_payload = flip_resp.json()
    assert flip_payload["new_image"]["derived_operation"] == "flip"
    assert flip_payload["new_image"]["width"] == 64
    assert flip_payload["new_image"]["height"] == 32

    rotate_resp = client.post(
        f"/api/images/{image_id}/rotate",
        json={"project_path": project_path, "angle": 90},
    )
    assert rotate_resp.status_code == 200, rotate_resp.text
    rotate_payload = rotate_resp.json()
    assert rotate_payload["new_image"]["derived_operation"] == "rotate"
    assert rotate_payload["new_image"]["width"] == 32
    assert rotate_payload["new_image"]["height"] == 64


def test_transform_validation_errors_return_400(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    bad_crop = client.post(
        f"/api/images/{image_id}/crop",
        json={"project_path": project_path, "rect": {"x": 0, "y": 0, "width": 1000, "height": 1000}},
    )
    assert bad_crop.status_code == 400

    bad_scale = client.post(
        f"/api/images/{image_id}/scale",
        json={
            "project_path": project_path,
            "mode": "percent",
            "percent": 200,
            "upscale": False,
        },
    )
    assert bad_scale.status_code == 400

    bad_rotate = client.post(
        f"/api/images/{image_id}/rotate",
        json={"project_path": project_path, "angle": 45},
    )
    assert bad_rotate.status_code == 400


def test_extract_region_creates_derived_image_and_copies_all_captions(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    create_caption_resp = client.post(
        "/api/captions/create",
        json={
            "project_path": project_path,
            "image_id": image_id,
            "text": "second candidate",
            "make_active": False,
        },
    )
    assert create_caption_resp.status_code == 200, create_caption_resp.text

    extract_resp = client.post(
        f"/api/images/{image_id}/extract-region",
        json={
            "project_path": project_path,
            "rect": {"x": 6, "y": 8, "width": 18, "height": 12},
            "add_source_reference_note": True,
        },
    )
    assert extract_resp.status_code == 200, extract_resp.text
    payload = extract_resp.json()
    assert payload["new_image"]["derived_operation"] == "extract_region"
    assert payload["new_image"]["width"] == 18
    assert payload["new_image"]["height"] == 12

    new_image_id = payload["new_image"]["id"]
    detail_resp = client.get(f"/api/images/{new_image_id}", params={"project_path": project_path})
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["image"]
    assert detail["source_image_id"] == image_id
    assert detail["derived_operation"] == "extract_region"
    assert len(detail["captions"]) == 2


def test_extract_region_out_of_bounds_returns_400(tmp_path: Path) -> None:
    project_path, image_id = _create_project_with_one_image(tmp_path)

    response = client.post(
        f"/api/images/{image_id}/extract-region",
        json={
            "project_path": project_path,
            "rect": {"x": 0, "y": 0, "width": 1000, "height": 1000},
        },
    )
    assert response.status_code == 400
