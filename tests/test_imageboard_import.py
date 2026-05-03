"""
Tests for imageboard import service and router.

Uses mock imageboard clients to avoid hitting real APIs.
Covers: search parsing, tag normalization, import flow, duplicate detection,
        database state after import, and error handling.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.main import app
from backend.services.imageboard_import_service import ImageboardImportService, ImportResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_png_bytes(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (16, 16), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_project(tmp_path: Path, name: str = "import_test") -> str:
    db_path = str(tmp_path / f"{name}.db")
    resp = client.post(
        "/api/projects/create",
        json={
            "path": db_path,
            "name": name,
            "description": "",
            "caption_mode": "description",
        },
    )
    assert resp.status_code == 200, resp.text
    return db_path


def _fake_image(
    image_id: int = 1,
    tags: list[str] | None = None,
    rating: str = "safe",
    url: str = "https://example.com/image.png",
) -> ImageboardImage:
    return ImageboardImage(
        id=image_id,
        title=f"image_{image_id}.png",
        image_url=url,
        source_url=f"https://example.com/posts/{image_id}",
        tags=tags or ["tag_a", "tag_b"],
        rating=rating,
    )


def _fake_search_result(images: list[ImageboardImage], total: int | None = None) -> SearchResult:
    return SearchResult(
        images=images,
        total_count=total if total is not None else len(images),
        page=1,
        has_next_page=False,
    )


class _MockClient(ImageboardClient):
    """Minimal mock client that returns pre-configured results."""

    board_name = "mock"
    board_display_name = "Mock Board"
    base_url = "https://example.com"
    available_sorts = ["relevance", "score"]

    def __init__(self, search_result: SearchResult, image_bytes: bytes | None = None):
        self._search_result = search_result
        self._image_bytes = image_bytes or _make_png_bytes()

    async def get_image_details(self, image_id: str | int) -> ImageboardImage:
        return _fake_image(int(image_id))

    async def search(self, query: str, sort_by: str = "relevance", sort_direction: str = "desc",
                     page: int = 1, per_page: int = 20, **kwargs) -> SearchResult:
        return self._search_result

    async def fetch_image_bytes(self, image_url: str) -> bytes:
        return self._image_bytes

    def normalize_tags(self, raw_tags: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in raw_tags})

    async def close(self) -> None:
        pass


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Unit tests: ImageboardImportService internals
# ---------------------------------------------------------------------------

class TestBuildExistingHashes:
    """Tests for _build_existing_hashes."""

    def test_empty_project_returns_empty_set(self, tmp_path):
        db_path = _create_project(tmp_path, "hash_empty")
        sf = create_sqlite_session_factory(db_path)
        svc = ImageboardImportService()
        result = svc._build_existing_hashes(sf)
        assert result == set()

    def test_returns_hash_for_existing_blob(self, tmp_path):
        db_path = _create_project(tmp_path, "hash_existing")
        sf = create_sqlite_session_factory(db_path)

        blob = _make_png_bytes((1, 2, 3))
        expected_hash = hashlib.sha256(blob).hexdigest()

        with sf() as session:
            project = session.scalar(__import__("sqlalchemy").select(ProjectRecord).limit(1))
            img = ImageRecord(
                project_id=project.id,
                filename="existing.png",
                original_blob=blob,
                working_blob=None,
                width=None,
                height=None,
                included=True,
            )
            session.add(img)
            session.commit()

        svc = ImageboardImportService()
        result = svc._build_existing_hashes(sf)
        assert expected_hash in result

    def test_skips_null_blobs(self, tmp_path):
        db_path = _create_project(tmp_path, "hash_null")
        sf = create_sqlite_session_factory(db_path)

        with sf() as session:
            project = session.scalar(__import__("sqlalchemy").select(ProjectRecord).limit(1))
            img = ImageRecord(
                project_id=project.id,
                filename="no_blob.png",
                original_blob=None,
                working_blob=None,
                width=None,
                height=None,
                included=True,
            )
            session.add(img)
            session.commit()

        svc = ImageboardImportService()
        result = svc._build_existing_hashes(sf)
        assert result == set()

    def test_skips_deleted_blobs(self, tmp_path):
        from datetime import datetime

        db_path = _create_project(tmp_path, "hash_deleted")
        sf = create_sqlite_session_factory(db_path)
        blob = _make_png_bytes((9, 8, 7))

        with sf() as session:
            project = session.scalar(__import__("sqlalchemy").select(ProjectRecord).limit(1))
            img = ImageRecord(
                project_id=project.id,
                filename="deleted.png",
                original_blob=blob,
                working_blob=None,
                width=None,
                height=None,
                included=True,
                deleted_at=datetime.utcnow(),
            )
            session.add(img)
            session.commit()

        svc = ImageboardImportService()
        result = svc._build_existing_hashes(sf)
        assert result == set()


# ---------------------------------------------------------------------------
# Integration tests: import_images via mocked client
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_import_creates_image_and_caption(tmp_path):
    """Happy path: one image imported with tags as caption."""
    db_path = _create_project(tmp_path, "import_happy")
    image_bytes = _make_png_bytes((50, 100, 150))
    fake_img = _fake_image(1, tags=["fluffy", "solo"], rating="safe")
    mock_client = _MockClient(
        search_result=_fake_search_result([fake_img]),
        image_bytes=image_bytes,
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="fluffy",
            import_count=1,
            include_tags_in_caption=True,
            skip_duplicates=False,
        )

    assert result.imported_count == 1
    assert result.failed_count == 0
    assert result.duplicate_count == 0

    sf = create_sqlite_session_factory(db_path)
    from sqlalchemy import select
    with sf() as session:
        images = session.scalars(select(ImageRecord)).all()
        assert len(images) == 1
        assert images[0].original_blob == image_bytes
        assert images[0].filename.startswith("mock_1.")

        captions = session.scalars(select(CaptionRecord)).all()
        assert len(captions) == 1
        assert "fluffy" in captions[0].text
        assert "solo" in captions[0].text
        assert captions[0].source == "imageboard:mock"


@pytest.mark.anyio
async def test_import_without_tags_creates_no_caption(tmp_path):
    db_path = _create_project(tmp_path, "import_notags")
    fake_img = _fake_image(2, tags=["tag_a"])
    mock_client = _MockClient(search_result=_fake_search_result([fake_img]))

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=1,
            include_tags_in_caption=False,
        )

    assert result.imported_count == 1

    sf = create_sqlite_session_factory(db_path)
    from sqlalchemy import select
    with sf() as session:
        captions = session.scalars(select(CaptionRecord)).all()
        assert len(captions) == 0


@pytest.mark.anyio
async def test_import_multiple_images(tmp_path):
    db_path = _create_project(tmp_path, "import_multi")
    images = [
        _fake_image(i, url=f"https://example.com/img{i}.png")
        for i in range(1, 4)
    ]
    # Give each image unique bytes to avoid dup detection
    image_bytes_list = [_make_png_bytes((i * 50, i * 30, 10)) for i in range(1, 4)]

    call_count = 0

    class _MultiClient(_MockClient):
        async def fetch_image_bytes(self, image_url: str) -> bytes:
            nonlocal call_count
            idx = call_count % len(image_bytes_list)
            call_count += 1
            return image_bytes_list[idx]

    mock_client = _MultiClient(search_result=_fake_search_result(images, total=3))
    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=3,
            skip_duplicates=True,
        )

    assert result.imported_count == 3
    assert result.failed_count == 0


# ---------------------------------------------------------------------------
# Duplicate detection tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_skip_duplicates_skips_existing_image(tmp_path):
    """When an identical image already exists, it should be counted as duplicate."""
    db_path = _create_project(tmp_path, "dup_existing")
    shared_bytes = _make_png_bytes((77, 88, 99))

    # Pre-insert the image into the project DB
    sf = create_sqlite_session_factory(db_path)
    from sqlalchemy import select
    with sf() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        session.add(ImageRecord(
            project_id=project.id,
            filename="preexisting.png",
            original_blob=shared_bytes,
            working_blob=None,
            width=None,
            height=None,
            included=True,
        ))
        session.commit()

    fake_img = _fake_image(99)
    mock_client = _MockClient(
        search_result=_fake_search_result([fake_img]),
        image_bytes=shared_bytes,  # same bytes as what's already in DB
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=1,
            skip_duplicates=True,
        )

    assert result.duplicate_count == 1
    assert result.imported_count == 0

    # Make sure no extra image was inserted
    with sf() as session:
        count = len(session.scalars(select(ImageRecord)).all())
    assert count == 1  # only the pre-inserted one


@pytest.mark.anyio
async def test_allow_duplicates_when_flag_false(tmp_path):
    """With skip_duplicates=False, same image bytes should be imported anyway."""
    db_path = _create_project(tmp_path, "dup_allow")
    shared_bytes = _make_png_bytes((11, 22, 33))

    sf = create_sqlite_session_factory(db_path)
    from sqlalchemy import select
    with sf() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        session.add(ImageRecord(
            project_id=project.id,
            filename="original.png",
            original_blob=shared_bytes,
            working_blob=None,
            width=None,
            height=None,
            included=True,
        ))
        session.commit()

    fake_img = _fake_image(100)
    mock_client = _MockClient(
        search_result=_fake_search_result([fake_img]),
        image_bytes=shared_bytes,
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=1,
            skip_duplicates=False,
        )

    assert result.imported_count == 1
    assert result.duplicate_count == 0

    with sf() as session:
        count = len(session.scalars(select(ImageRecord)).all())
    assert count == 2


@pytest.mark.anyio
async def test_intra_batch_duplicate_skipped(tmp_path):
    """Two images with the same bytes in the same batch: second should be a dup."""
    db_path = _create_project(tmp_path, "dup_batch")
    shared_bytes = _make_png_bytes((55, 66, 77))

    images = [_fake_image(i) for i in range(1, 3)]
    mock_client = _MockClient(
        search_result=_fake_search_result(images, total=2),
        image_bytes=shared_bytes,  # both return identical bytes
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=2,
            skip_duplicates=True,
        )

    assert result.imported_count == 1
    assert result.duplicate_count == 1


# ---------------------------------------------------------------------------
# Tag normalization tests
# ---------------------------------------------------------------------------

def test_mock_client_normalize_tags_deduplicates_and_lowercases():
    mc = _MockClient(search_result=_fake_search_result([]))
    result = mc.normalize_tags(["Fluffy", "FLUFFY", "solo", "  Solo  "])
    assert result == sorted({"fluffy", "solo"})


def test_tag_normalization_empty_list():
    mc = _MockClient(search_result=_fake_search_result([]))
    assert mc.normalize_tags([]) == []


# ---------------------------------------------------------------------------
# API endpoint tests (router layer)
# ---------------------------------------------------------------------------

def test_do_import_endpoint_returns_200_with_mock(tmp_path):
    """End-to-end: POST /api/imageboard-import/do-import with mocked client."""
    db_path = _create_project(tmp_path, "router_import")

    with patch(
        "backend.routers.imageboard_import.get_imageboard_import_service"
    ) as mock_factory:
        instance = MagicMock()
        mock_factory.return_value = instance
        instance.import_images = AsyncMock(
            return_value=ImportResult(
                board_id="mock",
                imported_count=1,
                failed_count=0,
                skipped_count=0,
                duplicate_count=0,
                errors=[],
            )
        )

        resp = client.post(
            "/api/imageboard-import/do-import",
            json={
                "project_path": db_path,
                "board_id": "mock",
                "query": "art",
                "import_count": 1,
                "include_tags_in_caption": True,
                "skip_duplicates": True,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["imported_count"] == 1
    assert data["duplicate_count"] == 0
    assert data["failed_count"] == 0


def test_do_import_endpoint_passes_skip_duplicates_flag(tmp_path):
    """Verify skip_duplicates is forwarded to the service."""
    db_path = _create_project(tmp_path, "router_dup_flag")

    with patch(
        "backend.routers.imageboard_import.get_imageboard_import_service"
    ) as mock_factory:
        instance = MagicMock()
        mock_factory.return_value = instance
        instance.import_images = AsyncMock(
            return_value=ImportResult(
                board_id="mock",
                imported_count=0,
                failed_count=0,
                skipped_count=0,
                duplicate_count=2,
                errors=[],
            )
        )

        resp = client.post(
            "/api/imageboard-import/do-import",
            json={
                "project_path": db_path,
                "board_id": "mock",
                "query": "test",
                "import_count": 5,
                "skip_duplicates": False,
            },
        )

    assert resp.status_code == 200
    _, kwargs = instance.import_images.call_args
    assert kwargs.get("skip_duplicates") is False


def test_do_import_endpoint_rejects_missing_project_path():
    resp = client.post(
        "/api/imageboard-import/do-import",
        json={
            "board_id": "derpibooru",
            "query": "test",
            "import_count": 5,
        },
    )
    assert resp.status_code == 422


def test_do_import_endpoint_rejects_zero_import_count(tmp_path):
    db_path = _create_project(tmp_path, "router_bad_count")
    resp = client.post(
        "/api/imageboard-import/do-import",
        json={
            "project_path": db_path,
            "board_id": "derpibooru",
            "query": "test",
            "import_count": 0,
        },
    )
    assert resp.status_code == 422


def test_preview_endpoint_returns_200_with_mock(tmp_path):
    """GET /api/imageboard-import/preview returns preview data."""

    with patch(
        "backend.routers.imageboard_import.get_imageboard_import_service"
    ) as mock_factory:
        instance = MagicMock()
        mock_factory.return_value = instance
        from backend.services.imageboard_import_service import ImportPreview
        instance.get_import_preview = AsyncMock(
            return_value=ImportPreview(
                board_id="mock",
                query="preview_tag",
                sort_by="relevance",
                total_available=42,
                preview_images=[
                    {
                        "id": 5,
                        "title": "image_5.png",
                        "url": "https://example.com/5.png",
                        "source_url": None,
                        "tags": ["preview_tag"],
                        "rating": "safe",
                    }
                ],
            )
        )

        resp = client.post(
            "/api/imageboard-import/preview",
            json={
                "board_id": "mock",
                "query": "preview_tag",
                "sort_by": "relevance",
                "sort_direction": "desc",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_available"] == 42
    assert len(data["preview_images"]) == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_import_handles_download_failure_gracefully(tmp_path):
    """If image download fails, failed_count increments and import continues."""
    db_path = _create_project(tmp_path, "import_dl_fail")
    good_bytes = _make_png_bytes((1, 2, 3))
    bad_img = _fake_image(1)
    good_img = _fake_image(2, url="https://example.com/good.png")

    call_count = 0

    class _FailFirstClient(_MockClient):
        async def fetch_image_bytes(self, image_url: str) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network failure")
            return good_bytes

    mock_client = _FailFirstClient(
        search_result=_fake_search_result([bad_img, good_img], total=2)
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        result = await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="test",
            import_count=2,
            skip_duplicates=False,
        )

    assert result.failed_count == 1
    assert result.imported_count == 1
    assert len(result.errors) == 1


@pytest.mark.anyio
async def test_import_unknown_board_raises(tmp_path):
    db_path = _create_project(tmp_path, "import_bad_board")
    svc = ImageboardImportService()
    with pytest.raises((ValueError, Exception)):
        await svc.import_images(
            project_path=db_path,
            board_id="nonexistent_board",
            query="test",
            import_count=1,
        )


# ---------------------------------------------------------------------------
# Per-client: tag extraction & normalization
# ---------------------------------------------------------------------------

class TestDerpibooruClient:
    """Tests for Derpibooru tag extraction and normalization."""

    def test_extract_tags_flat_strings(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        img_data = {"tags": ["Fluttershy", "solo", "safe"]}
        assert DerpibooruClient._extract_tags(img_data) == ["Fluttershy", "solo", "safe"]

    def test_extract_tags_dict_objects(self):
        """Tags can come as dicts with a 'name' key."""
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        img_data = {"tags": [{"name": "Fluttershy", "slug": "fluttershy"}, {"name": "solo"}]}
        assert DerpibooruClient._extract_tags(img_data) == ["Fluttershy", "solo"]

    def test_extract_tags_empty(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        assert DerpibooruClient._extract_tags({}) == []

    def test_extract_rating_safe(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        assert DerpibooruClient._extract_rating({"rating": "safe"}) == "safe"

    def test_extract_rating_explicit(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        assert DerpibooruClient._extract_rating({"rating": "explicit"}) == "explicit"

    def test_extract_rating_unknown_returns_none(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        assert DerpibooruClient._extract_rating({"rating": "gore"}) is None

    def test_normalize_tags_removes_rating_tags(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        c = DerpibooruClient()
        result = c.normalize_tags(["safe", "explicit", "suggestive", "solo", "Fluttershy"])
        assert "safe" not in result
        assert "explicit" not in result
        assert "suggestive" not in result
        assert "solo" in result
        assert "fluttershy" in result

    def test_normalize_tags_removes_meta_tags(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        c = DerpibooruClient()
        result = c.normalize_tags(["derpibooru exclusive", "requires cropping", "rainbow dash"])
        assert "derpibooru exclusive" not in result
        assert "requires cropping" not in result
        assert "rainbow dash" in result

    def test_normalize_tags_sorted(self):
        from backend.llm.imageboard.derpibooru import DerpibooruClient
        c = DerpibooruClient()
        result = c.normalize_tags(["zebra", "apple", "mare"])
        assert result == sorted(result)


class TestDanbooruClient:
    """Tests for Danbooru tag extraction and normalization."""

    def test_extract_tags_from_tag_strings(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        post_data = {
            "tag_string_general": "1girl solo",
            "tag_string_artist": "some_artist",
            "tag_string_character": "reimu_hakurei",
            "tag_string_copyright": "touhou",
            "tag_string_meta": "highres",
        }
        tags = DanbooruClient._extract_tags(post_data)
        assert "1girl" in tags
        assert "solo" in tags
        assert "some_artist" in tags
        assert "reimu_hakurei" in tags
        assert "touhou" in tags
        assert "highres" in tags

    def test_extract_tags_empty_fields(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        assert DanbooruClient._extract_tags({}) == []

    def test_extract_rating_letter_codes(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        assert DanbooruClient._extract_rating({"rating": "s"}) == "safe"
        assert DanbooruClient._extract_rating({"rating": "q"}) == "questionable"
        assert DanbooruClient._extract_rating({"rating": "e"}) == "explicit"
        assert DanbooruClient._extract_rating({"rating": "x"}) is None

    def test_extract_image_url_prefers_file(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        post_data = {
            "file": {"url": "https://cdn.example.com/full.png"},
            "sample": {"url": "https://cdn.example.com/sample.jpg"},
        }
        assert DanbooruClient._extract_image_url(post_data) == "https://cdn.example.com/full.png"

    def test_extract_image_url_falls_back_to_sample(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        post_data = {
            "file": {"url": None},
            "sample": {"url": "https://cdn.example.com/sample.jpg"},
        }
        assert DanbooruClient._extract_image_url(post_data) == "https://cdn.example.com/sample.jpg"

    def test_extract_image_url_empty(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        assert DanbooruClient._extract_image_url({}) == ""

    def test_normalize_tags_underscores_to_spaces(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        c = DanbooruClient()
        result = c.normalize_tags(["blue_eyes", "long_hair", "1girl"])
        assert "blue eyes" in result
        assert "long hair" in result
        assert "1girl" in result

    def test_normalize_tags_removes_rating_tags(self):
        from backend.llm.imageboard.danbooru import DanbooruClient
        c = DanbooruClient()
        result = c.normalize_tags(["safe", "explicit", "translated", "1girl"])
        assert "safe" not in result
        assert "explicit" not in result
        assert "translated" not in result
        assert "1girl" in result


class TestE621Client:
    """Tests for e621 tag extraction and normalization."""

    def test_extract_tags_from_category_dict(self):
        from backend.llm.imageboard.e621 import E621Client
        post_data = {
            "tags": {
                "general": ["fluffy", "solo"],
                "species": ["canine"],
                "character": ["fido"],
                "artist": ["some_artist"],
                "copyright": [],
                "meta": ["highres"],
            }
        }
        tags = E621Client._extract_tags(post_data)
        assert "fluffy" in tags
        assert "solo" in tags
        assert "canine" in tags
        assert "fido" in tags
        assert "some_artist" in tags
        assert "highres" in tags

    def test_extract_tags_flat_list_fallback(self):
        from backend.llm.imageboard.e621 import E621Client
        post_data = {"tags": ["fluffy", "solo"]}
        assert E621Client._extract_tags(post_data) == ["fluffy", "solo"]

    def test_extract_tags_empty(self):
        from backend.llm.imageboard.e621 import E621Client
        assert E621Client._extract_tags({}) == []

    def test_extract_rating_letter_codes(self):
        from backend.llm.imageboard.e621 import E621Client
        assert E621Client._extract_rating({"rating": "s"}) == "safe"
        assert E621Client._extract_rating({"rating": "q"}) == "questionable"
        assert E621Client._extract_rating({"rating": "e"}) == "explicit"
        assert E621Client._extract_rating({}) is None

    def test_extract_image_url_file_object(self):
        from backend.llm.imageboard.e621 import E621Client
        post_data = {
            "file": {"url": "https://cdn.e621.net/data/full.png"},
            "sample": {"url": "https://cdn.e621.net/data/sample.jpg"},
        }
        assert E621Client._extract_image_url(post_data) == "https://cdn.e621.net/data/full.png"

    def test_normalize_tags_underscores_to_spaces(self):
        from backend.llm.imageboard.e621 import E621Client
        c = E621Client()
        result = c.normalize_tags(["blue_eyes", "long_hair", "solo"])
        assert "blue eyes" in result
        assert "long hair" in result
        assert "solo" in result

    def test_normalize_tags_removes_rating_words(self):
        from backend.llm.imageboard.e621 import E621Client
        c = E621Client()
        result = c.normalize_tags(["safe", "explicit", "questionable", "fluffy"])
        assert "safe" not in result
        assert "explicit" not in result
        assert "fluffy" in result


class TestTwibooruClient:
    """Tests for Twibooru tag extraction and normalization."""

    def test_extract_tags_flat_list(self):
        from backend.llm.imageboard.twibooru import TwibooruClient
        post_data = {"tags": ["rainbow dash", "flying", "safe"]}
        assert TwibooruClient._extract_tags(post_data) == ["rainbow dash", "flying", "safe"]

    def test_extract_tags_empty(self):
        from backend.llm.imageboard.twibooru import TwibooruClient
        assert TwibooruClient._extract_tags({}) == []

    def test_extract_rating_philomena_strings(self):
        from backend.llm.imageboard.twibooru import TwibooruClient
        assert TwibooruClient._extract_rating({"rating": "safe"}) == "safe"
        assert TwibooruClient._extract_rating({"rating": "explicit"}) == "explicit"
        assert TwibooruClient._extract_rating({"rating": "suggestive"}) == "suggestive"
        assert TwibooruClient._extract_rating({"rating": "unknown"}) is None

    def test_normalize_tags_removes_rating_tags(self):
        from backend.llm.imageboard.twibooru import TwibooruClient
        c = TwibooruClient()
        result = c.normalize_tags(["safe", "suggestive", "rainbow dash"])
        assert "safe" not in result
        assert "suggestive" not in result
        assert "rainbow dash" in result


# ---------------------------------------------------------------------------
# Source attribution
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_caption_includes_source_url_when_available(tmp_path):
    """When source_url is present on the image, caption should note it."""
    db_path = _create_project(tmp_path, "source_attr")
    image_bytes = _make_png_bytes((20, 40, 60))
    fake_img = ImageboardImage(
        id=42,
        title="image_42.png",
        image_url="https://cdn.example.com/42.png",
        source_url="https://derpibooru.org/images/42",
        tags=["pony", "solo"],
        rating="safe",
    )
    mock_client = _MockClient(
        search_result=_fake_search_result([fake_img]),
        image_bytes=image_bytes,
    )

    svc = ImageboardImportService()
    with patch.object(svc, "get_client", new=AsyncMock(return_value=mock_client)):
        await svc.import_images(
            project_path=db_path,
            board_id="mock",
            query="pony",
            import_count=1,
            include_tags_in_caption=True,
            skip_duplicates=False,
        )

    from sqlalchemy import select
    sf = create_sqlite_session_factory(db_path)
    with sf() as session:
        caption = session.scalar(select(CaptionRecord))
        assert caption is not None
        assert "derpibooru.org/images/42" in caption.text


# ---------------------------------------------------------------------------
# Rating filter
# ---------------------------------------------------------------------------

class TestApplyRatingFilter:
    """Tests for _apply_rating_filter query modifier."""

    def test_any_returns_query_unchanged(self):
        svc = ImageboardImportService()
        assert svc._apply_rating_filter("fluffy", "derpibooru", "any") == "fluffy"

    def test_empty_filter_returns_query_unchanged(self):
        svc = ImageboardImportService()
        assert svc._apply_rating_filter("fluffy", "derpibooru", "") == "fluffy"

    # --- Philomena boards ---
    def test_safe_appended_for_derpibooru(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("fluffy", "derpibooru", "safe")
        assert result == "fluffy, safe"

    def test_questionable_becomes_suggestive_for_philomena(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("art", "tantabus", "questionable")
        assert "suggestive" in result

    def test_explicit_appended_for_twibooru(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("art", "twibooru", "explicit")
        assert result == "art, explicit"

    def test_empty_query_philomena_returns_just_rating(self):
        svc = ImageboardImportService()
        assert svc._apply_rating_filter("", "derpibooru", "safe") == "safe"

    # --- Rails boards ---
    def test_safe_appended_for_danbooru(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("1girl", "danbooru", "safe")
        assert result == "1girl rating:s"

    def test_questionable_appended_for_e621(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("canine", "e621", "questionable")
        assert result == "canine rating:q"

    def test_explicit_appended_for_e621(self):
        svc = ImageboardImportService()
        result = svc._apply_rating_filter("canine", "e621", "explicit")
        assert result == "canine rating:e"

    def test_empty_query_rails_returns_just_rating(self):
        svc = ImageboardImportService()
        assert svc._apply_rating_filter("", "danbooru", "safe") == "rating:s"
