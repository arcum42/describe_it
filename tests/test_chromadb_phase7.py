"""Regression tests for Phase 7: ChromaDB/RAG integration."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.models import ImageRecord, CaptionRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database
from backend.services.chromadb_service import is_chromadb_available, chromadb_service
from backend.services.rag_service import rag_service
from sqlalchemy import select


def _create_project_db(project_path: str) -> str:
    """Create a project database with test data."""
    db_path = Path(project_path) / "project.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    session_factory = create_sqlite_session_factory(db_path)
    initialize_database(db_path)

    with session_factory() as session:
        project = ProjectRecord(
            name="Test Project",
            description="Test dataset",
            caption_mode="description",
        )
        session.add(project)
        session.flush()

        image1 = ImageRecord(project_id=project.id, filename="image1.jpg", original_blob=b"fake_image_data_1", working_blob=None, width=100, height=100, included=True)
        image2 = ImageRecord(project_id=project.id, filename="image2.jpg", original_blob=b"fake_image_data_2", working_blob=None, width=100, height=100, included=True)
        image3 = ImageRecord(project_id=project.id, filename="image3.jpg", original_blob=b"fake_image_data_3", working_blob=None, width=100, height=100, included=True)
        session.add_all([image1, image2, image3])
        session.flush()

        caption1 = CaptionRecord(image_id=image1.id, text="A red dog running in the park", is_active=True)
        caption2 = CaptionRecord(image_id=image2.id, text="A blue cat sitting on a chair", is_active=True)
        caption3 = CaptionRecord(image_id=image3.id, text="A dog playing with a ball", is_active=True)
        session.add_all([caption1, caption2, caption3])
        session.commit()

    return str(db_path)


@pytest.mark.skipif(not is_chromadb_available(), reason="ChromaDB not available")
def test_chromadb_rebuild_embeddings():
    """Test rebuilding embeddings for a project."""
    captions = [
        {"id": "1", "text": "A red dog running in the park"},
        {"id": "2", "text": "A blue cat sitting on a chair"},
        {"id": "3", "text": "A dog playing with a ball"},
    ]
    result = rag_service.rebuild_embeddings_for_project(
        project_path="/fake/project.db",
        captions=captions,
    )

    assert result.get("enabled") is True
    assert result.get("indexed", 0) >= 3, f"Expected at least 3 indexed captions, got {result.get('indexed', 0)}"


@pytest.mark.skipif(not is_chromadb_available(), reason="ChromaDB not available")
def test_chromadb_search_similar():
    """Test searching for similar captions."""
    captions = [
        {"id": "1", "text": "A red dog running in the park"},
        {"id": "2", "text": "A blue cat sitting on a chair"},
        {"id": "3", "text": "A dog playing with a ball"},
    ]
    project_path = "/fake/project.db"
    rag_service.rebuild_embeddings_for_project(project_path=project_path, captions=captions)

    similar = rag_service.get_similar_captions(
        project_path=project_path,
        query_text="A red dog",
        top_k=2,
    )

    assert len(similar) > 0, "Should find at least one similar caption"
    assert "dog" in similar[0].lower(), f"Expected caption with 'dog', got: {similar[0]}"


@pytest.mark.skipif(not is_chromadb_available(), reason="ChromaDB not available")
def test_chromadb_augmented_prompt():
    """Test building augmented system prompt with RAG examples."""
    base_prompt = "You are a caption generator."
    captions = [
        {"id": "1", "text": "A red dog running in the park"},
        {"id": "2", "text": "A blue cat sitting on a chair"},
        {"id": "3", "text": "A dog playing with a ball"},
    ]
    project_path = "/fake/project.db"
    rag_service.rebuild_embeddings_for_project(project_path=project_path, captions=captions)

    augmented = rag_service.build_augmented_system_prompt(
        base_system_prompt=base_prompt,
        project_path=project_path,
        current_caption="A cat",
        include_few_shot=True,
    )

    assert len(augmented) > len(base_prompt), "Augmented prompt should be longer"
    assert "Example similar captions" in augmented, "Should include few-shot examples"


def test_chromadb_graceful_degradation():
    """Test RAG service gracefully degrades when ChromaDB unavailable."""
    is_enabled = rag_service.is_enabled()
    if not is_enabled:
        similar = rag_service.get_similar_captions(
            project_path="/fake/path.db",
            query_text="test",
            top_k=3,
        )
        assert similar == [], "Should return empty list when RAG disabled"

        augmented = rag_service.build_augmented_system_prompt(
            base_system_prompt="test prompt",
            project_path="/fake/path.db",
            current_caption="test",
            include_few_shot=True,
        )
        assert augmented == "test prompt", "Should return base prompt when RAG disabled"


@pytest.mark.skipif(not is_chromadb_available(), reason="ChromaDB not available")
def test_rag_api_rebuild_embeddings():
    """Test RAG API endpoint for rebuilding embeddings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = str(Path(tmpdir) / "test_project.db")
        db_path = _create_project_db(project_path)

        client = TestClient(app)

        response = client.post(
            "/api/llm/rag/rebuild-embeddings",
            json={"project_path": db_path},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        payload = response.json()
        assert payload.get("result", {}).get("enabled") is True
        assert payload.get("result", {}).get("indexed", 0) >= 3, f"Expected at least 3 indexed captions, got {payload.get('result', {}).get('indexed', 0)}"


@pytest.mark.skipif(not is_chromadb_available(), reason="ChromaDB not available")
def test_rag_api_search():
    """Test RAG API endpoint for searching similar captions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = str(Path(tmpdir) / "test_project.db")
        db_path = _create_project_db(project_path)

        client = TestClient(app)

        client.post(
            "/api/llm/rag/rebuild-embeddings",
            json={"project_path": db_path},
        )

        response = client.post(
            "/api/llm/rag/search",
            json={"project_path": db_path, "query_text": "red dog", "top_k": 2},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        payload = response.json()
        assert payload.get("rag_enabled") is True
        similar = payload.get("similar_captions", [])
        assert len(similar) > 0, "Should find similar captions"


def test_rag_api_status():
    """Test RAG status API endpoint."""
    client = TestClient(app)

    response = client.get("/api/llm/rag/status")

    assert response.status_code == 200
    payload = response.json()
    assert "rag_enabled" in payload
    assert isinstance(payload["rag_enabled"], bool)
