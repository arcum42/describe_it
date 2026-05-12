from __future__ import annotations

from pathlib import Path

from backend.services.native_picker_service import _normalize_start_path


def test_normalize_start_path_uses_nearest_existing_parent(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist" / "nested" / "file.db"
    normalized = _normalize_start_path(str(missing))
    assert normalized == tmp_path


def test_normalize_start_path_keeps_existing_path(tmp_path: Path) -> None:
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_start_path(str(existing_dir))
    assert normalized == existing_dir
