from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.config import get_settings


def is_chromadb_available() -> bool:
    """Check if ChromaDB is installed and available."""
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


class ChromaDBService:
    """Manage ChromaDB embeddings for project captions."""

    def __init__(self) -> None:
        if not is_chromadb_available():
            self.client = None
            self.enabled = False
            return

        import chromadb

        self.enabled = True
        settings = get_settings()
        chroma_dir = settings.state_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        persist_directory = str(chroma_dir)
        self.client = chromadb.PersistentClient(path=persist_directory)

    def _collection_name(self, project_path: str) -> str:
        """Generate a collection name from project path."""
        safe_name = Path(project_path).stem.replace("-", "_").replace(".", "_")
        return f"captions_{safe_name}"

    def get_collection(self, project_path: str) -> Any:
        """Get or create a collection for the project."""
        if not self.enabled or self.client is None:
            return None
        collection_name = self._collection_name(project_path)
        return self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    def rebuild_embeddings(
        self,
        *,
        project_path: str,
        captions: list[dict[str, object]],
    ) -> dict[str, object]:
        """Rebuild embeddings for all captions in a project.

        Args:
            project_path: Path to project database.
            captions: List of dicts with 'id', 'text' keys.

        Returns:
            Summary of rebuild operation.
        """
        if not self.enabled or self.client is None:
            return {"enabled": False, "indexed": 0}

        collection_name = self._collection_name(project_path)
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:  # noqa: BLE001
            pass

        collection = self.get_collection(project_path)
        if collection is None:
            return {"enabled": False, "indexed": 0}

        indexed = 0
        for caption in captions:
            caption_id = str(caption.get("id", ""))
            caption_text = str(caption.get("text", "")).strip()
            if not caption_id or not caption_text:
                continue

            collection.add(ids=[caption_id], documents=[caption_text], metadatas=[{"project": project_path}])
            indexed += 1

        return {
            "enabled": True,
            "indexed": indexed,
            "project_path": project_path,
            "collection": collection.name,
        }

    def search_similar(
        self,
        *,
        project_path: str,
        query_text: str,
        top_k: int = 3,
    ) -> list[dict[str, object]]:
        """Search for similar captions in a project.

        Args:
            project_path: Path to project database.
            query_text: Query text.
            top_k: Number of results.

        Returns:
            List of similar captions with scores.
        """
        if not self.enabled or self.client is None:
            return []

        collection = self.get_collection(project_path)
        if collection is None:
            return []

        query_text = str(query_text).strip()
        if not query_text:
            return []

        try:
            results = collection.query(query_texts=[query_text], n_results=top_k)
        except Exception:  # noqa: BLE001
            return []

        similar = []
        if results and results.get("documents") and results["documents"]:
            docs = results["documents"][0]
            distances = results.get("distances", [[]])[0] if results.get("distances") else []

            for i, doc in enumerate(docs):
                distance = distances[i] if i < len(distances) else 0.0
                similarity = max(0.0, 1.0 - float(distance))
                similar.append(
                    {
                        "text": doc,
                        "similarity": similarity,
                    }
                )

        return similar

    def delete_collection(self, project_path: str) -> dict[str, object]:
        """Delete embeddings collection for a project."""
        if not self.enabled or self.client is None:
            return {"enabled": False}

        collection_name = self._collection_name(project_path)
        try:
            self.client.delete_collection(name=collection_name)
            return {"enabled": True, "deleted": collection_name}
        except Exception:  # noqa: BLE001
            return {"enabled": True, "deleted": None}


chromadb_service = ChromaDBService()
