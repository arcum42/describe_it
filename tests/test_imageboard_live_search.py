"""Live imageboard diagnostics.

These tests hit real board APIs and are skipped by default.
Enable with:
  RUN_LIVE_IMAGEBOARD_TESTS=1 pytest tests/test_imageboard_live_search.py -q -s

Credentials (when needed):
  E621_USERNAME / E621_API_KEY
  DANBOORU_USERNAME / DANBOORU_API_KEY
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.llm.imageboard.danbooru import DanbooruClient
from backend.llm.imageboard.derpibooru import DerpibooruClient
from backend.llm.imageboard.e621 import E621Client
from backend.llm.imageboard.tantabus import TantabusClient
from backend.llm.imageboard.twibooru import TwibooruClient
from backend.services.imageboard_import_service import ImageboardImportService


pytestmark = pytest.mark.anyio


def _live_enabled() -> bool:
    return os.environ.get("RUN_LIVE_IMAGEBOARD_TESTS", "0").strip() == "1"


def _assert_basic_search_shape(board_id: str, result) -> None:
    assert result.page == 1
    assert result.total_count >= 0
    assert len(result.images) <= 6
    if result.images:
        first = result.images[0]
        assert first.id is not None
        assert first.image_url
        assert first.source_url
    print(f"[{board_id}] total_count={result.total_count} preview={len(result.images)}")


def _get_saved_credentials(board_id: str) -> tuple[str | None, str | None]:
    """Read saved board credentials from default local app_state.db.

    This bypasses pytest's temporary DESCRIBE_IT_STATE_DIR and is only used
    for opt-in live diagnostics.
    """
    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / ".describe_it" / "app_state.db"
    if not db_path.exists():
        return None, None
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT username, api_key FROM imageboard_credentials WHERE board_id = ?",
            (board_id,),
        ).fetchone()
        conn.close()
        if not row:
            return None, None
        username, api_key = row
        return username, api_key
    except Exception:
        return None, None


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_derpibooru_search():
    client = DerpibooruClient()
    try:
        result = await client.search(query="fluttershy", sort_by="relevance", page=1, per_page=6)
        _assert_basic_search_shape("derpibooru", result)
        assert result.total_count >= len(result.images)
    finally:
        await client.close()


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_tantabus_search():
    client = TantabusClient()
    try:
        result = await client.search(query="fluttershy", sort_by="relevance", page=1, per_page=6)
        _assert_basic_search_shape("tantabus", result)
        assert result.total_count >= len(result.images)
    finally:
        await client.close()


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_twibooru_search():
    client = TwibooruClient()
    try:
        result = await client.search(query="fluttershy", sort_by="relevance", page=1, per_page=6)
        _assert_basic_search_shape("twibooru", result)
        assert result.total_count >= len(result.images)
    finally:
        await client.close()


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_e621_search_and_counts_consistency():
    username = os.environ.get("E621_USERNAME")
    api_key = os.environ.get("E621_API_KEY")
    if not username or not api_key:
        username, api_key = _get_saved_credentials("e621")
    if not username or not api_key:
        pytest.skip("Set E621_USERNAME/E621_API_KEY or save e621 credentials in ~/.describe_it/app_state.db")

    client = E621Client(api_key=api_key, username=username)
    query = "female"
    try:
        result = await client.search(query=query, sort_by="date", page=1, per_page=6)
        _assert_basic_search_shape("e621", result)

        # Compare against tag lookup payload shape used by the client.
        await client._ensure_http_client()
        raw_counts = await client.http_client.get(
            f"{client.base_url}/tags.json",
            params={"search[name_matches]": query, "limit": 1},
        )
        print(f"[e621] raw counts payload={raw_counts}")

        assert isinstance(raw_counts, list)
        assert raw_counts
        top = raw_counts[0]
        assert isinstance(top, dict)
        assert top.get("name") == query
        site_posts = top.get("post_count")
        if isinstance(site_posts, str):
            site_posts = int(site_posts)
        assert isinstance(site_posts, int)
        assert result.total_count == site_posts
    finally:
        await client.close()


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_e621_fluttershy_mlp_query_matches_tag_count_via_service():
    """Validate the exact UI query path through service normalization for e621."""
    username = os.environ.get("E621_USERNAME")
    api_key = os.environ.get("E621_API_KEY")
    if not username or not api_key:
        username, api_key = _get_saved_credentials("e621")
    if not username or not api_key:
        pytest.skip("Set E621_USERNAME/E621_API_KEY or save e621 credentials in repo .describe_it/app_state.db")

    client = E621Client(api_key=api_key, username=username)
    svc = ImageboardImportService()
    # Force known live client regardless of test-state credential DB redirection.
    svc.get_client = AsyncMock(return_value=client)

    try:
        result = await svc.search(
            board_id="e621",
            query="fluttershy (mlp)",
            sort_by="date",
            sort_direction="desc",
            page=1,
            per_page=6,
            rating_filter="any",
        )
        _assert_basic_search_shape("e621:fluttershy_(mlp)", result)

        await client._ensure_http_client()
        raw_tags = await client.http_client.get(
            f"{client.base_url}/tags.json",
            params={"search[name_matches]": "fluttershy_(mlp)", "limit": 1},
        )
        print(f"[e621:fluttershy_(mlp)] raw tags payload={raw_tags}")
        assert isinstance(raw_tags, list)
        assert raw_tags
        top = raw_tags[0]
        assert isinstance(top, dict)
        assert top.get("name") == "fluttershy_(mlp)"
        site_posts = top.get("post_count")
        if isinstance(site_posts, str):
            site_posts = int(site_posts)
        assert isinstance(site_posts, int)
        assert result.total_count == site_posts
    finally:
        await client.close()


@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_LIVE_IMAGEBOARD_TESTS=1 to run live API diagnostics")
async def test_live_danbooru_search():
    username = os.environ.get("DANBOORU_USERNAME")
    api_key = os.environ.get("DANBOORU_API_KEY")
    if not username or not api_key:
        username, api_key = _get_saved_credentials("danbooru")
    if not username or not api_key:
        pytest.skip("Set DANBOORU_USERNAME/DANBOORU_API_KEY or save danbooru credentials in ~/.describe_it/app_state.db")

    client = DanbooruClient(api_key=api_key, username=username)
    try:
        result = await client.search(query="1girl", sort_by="date", page=1, per_page=6)
        _assert_basic_search_shape("danbooru", result)
    finally:
        await client.close()