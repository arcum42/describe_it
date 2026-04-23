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

    # ------------------------------------------------------------------
    # Note embeddings (project notes stored in same collection as captions
    # using prefixed IDs "note_{id}"; global notes in dedicated collection)
    # ------------------------------------------------------------------

    def _global_notes_collection_name(self) -> str:
        return "global_notes"

    def _note_doc_id(self, note_id: int) -> str:
        return f"note_{note_id}"

    def upsert_note(
        self,
        *,
        project_path: str,
        note_id: int,
        title: str,
        content: str,
        tags: str,
        format: str,
        updated_at: str,
    ) -> None:
        """Upsert a project note embedding into the project collection."""
        if not self.enabled or self.client is None:
            return
        text = f"{title}\n{content}".strip()
        if not text:
            return
        collection = self.get_collection(project_path)
        if collection is None:
            return
        doc_id = self._note_doc_id(note_id)
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[{
                "doc_type": "project_note",
                "note_id": str(note_id),
                "project_path": project_path,
                "title": title or "",
                "format": format or "text",
                "tags": tags or "",
                "updated_at": updated_at or "",
            }],
        )

    def delete_note_embedding(self, *, project_path: str, note_id: int) -> None:
        """Remove a project note embedding from the project collection."""
        if not self.enabled or self.client is None:
            return
        collection = self.get_collection(project_path)
        if collection is None:
            return
        try:
            collection.delete(ids=[self._note_doc_id(note_id)])
        except Exception:  # noqa: BLE001
            pass

    def search_notes(
        self,
        *,
        project_path: str,
        query_text: str,
        top_k: int = 3,
        include_captions: bool = False,
    ) -> list[dict[str, object]]:
        """Search project notes (and optionally captions) in the project collection."""
        if not self.enabled or self.client is None:
            return []
        collection = self.get_collection(project_path)
        if collection is None:
            return []
        query_text = str(query_text).strip()
        if not query_text:
            return []
        where = None if include_captions else {"doc_type": {"$eq": "project_note"}}
        try:
            kwargs: dict[str, object] = {"query_texts": [query_text], "n_results": top_k}
            if where is not None:
                kwargs["where"] = where
            results = collection.query(**kwargs)
        except Exception:  # noqa: BLE001
            return []
        similar = []
        if results and results.get("documents") and results["documents"]:
            docs = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            for i, doc in enumerate(docs):
                distance = distances[i] if i < len(distances) else 0.0
                similarity = max(0.0, 1.0 - float(distance))
                meta = metadatas[i] if i < len(metadatas) else {}
                similar.append({"text": doc, "similarity": similarity, "metadata": meta})
        return similar

    # Global notes

    def upsert_global_note(
        self,
        *,
        note_id: int,
        title: str,
        content: str,
        tags: str,
        format: str,
        updated_at: str,
    ) -> None:
        """Upsert a global note embedding into the global notes collection."""
        if not self.enabled or self.client is None:
            return
        text = f"{title}\n{content}".strip()
        if not text:
            return
        try:
            collection = self.client.get_or_create_collection(
                name=self._global_notes_collection_name(),
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:  # noqa: BLE001
            return
        doc_id = self._note_doc_id(note_id)
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[{
                "doc_type": "global_note",
                "note_id": str(note_id),
                "title": title or "",
                "format": format or "text",
                "tags": tags or "",
                "updated_at": updated_at or "",
            }],
        )

    def delete_global_note_embedding(self, *, note_id: int) -> None:
        """Remove a global note embedding from the global notes collection."""
        if not self.enabled or self.client is None:
            return
        try:
            collection = self.client.get_or_create_collection(
                name=self._global_notes_collection_name(),
                metadata={"hnsw:space": "cosine"},
            )
            collection.delete(ids=[self._note_doc_id(note_id)])
        except Exception:  # noqa: BLE001
            pass

    def search_global_notes(self, *, query_text: str, top_k: int = 3) -> list[dict[str, object]]:
        """Search global notes collection."""
        if not self.enabled or self.client is None:
            return []
        query_text = str(query_text).strip()
        if not query_text:
            return []
        try:
            collection = self.client.get_or_create_collection(
                name=self._global_notes_collection_name(),
                metadata={"hnsw:space": "cosine"},
            )
            results = collection.query(query_texts=[query_text], n_results=top_k)
        except Exception:  # noqa: BLE001
            return []
        similar = []
        if results and results.get("documents") and results["documents"]:
            docs = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            for i, doc in enumerate(docs):
                distance = distances[i] if i < len(distances) else 0.0
                similarity = max(0.0, 1.0 - float(distance))
                meta = metadatas[i] if i < len(metadatas) else {}
                similar.append({"text": doc, "similarity": similarity, "metadata": meta})
        return similar


chromadb_service = ChromaDBService()
