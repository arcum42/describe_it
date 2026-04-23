from __future__ import annotations

from backend.services.chromadb_service import chromadb_service, is_chromadb_available


class RAGService:
    """Retrieve-Augment-Generate service for caption-aware prompts."""

    def is_enabled(self) -> bool:
        """Check if RAG is enabled (ChromaDB available)."""
        return is_chromadb_available() and chromadb_service.enabled

    def get_similar_captions(
        self,
        *,
        project_path: str,
        query_text: str,
        top_k: int = 2,
    ) -> list[str]:
        """Retrieve similar captions for a query."""
        if not self.is_enabled():
            return []

        similar = chromadb_service.search_similar(
            project_path=project_path,
            query_text=query_text,
            top_k=top_k,
        )
        return [item["text"] for item in similar if item.get("text")]

    def build_augmented_system_prompt(
        self,
        *,
        base_system_prompt: str,
        project_path: str,
        current_caption: str,
        include_few_shot: bool = True,
    ) -> str:
        """Build system prompt with optional few-shot examples from RAG."""
        if not include_few_shot or not self.is_enabled():
            return base_system_prompt

        similar = self.get_similar_captions(
            project_path=project_path,
            query_text=current_caption,
            top_k=2,
        )

        if not similar:
            return base_system_prompt

        few_shot_section = "\n\nExample similar captions from this dataset:\n"
        for i, caption in enumerate(similar, 1):
            few_shot_section += f"  {i}. {caption}\n"

        return base_system_prompt + few_shot_section

    def rebuild_embeddings_for_project(
        self,
        *,
        project_path: str,
        captions: list[dict[str, object]],
    ) -> dict[str, object]:
        """Rebuild embeddings for a project."""
        if not self.is_enabled():
            return {"rag_enabled": False}

        return chromadb_service.rebuild_embeddings(project_path=project_path, captions=captions)

    # ------------------------------------------------------------------
    # Note indexing
    # ------------------------------------------------------------------

    def upsert_project_note(
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
        """Index or re-index a project note embedding."""
        if not self.is_enabled():
            return
        chromadb_service.upsert_note(
            project_path=project_path,
            note_id=note_id,
            title=title,
            content=content,
            tags=tags,
            format=format,
            updated_at=updated_at,
        )

    def delete_project_note(self, *, project_path: str, note_id: int) -> None:
        """Remove a project note from the index."""
        if not self.is_enabled():
            return
        chromadb_service.delete_note_embedding(project_path=project_path, note_id=note_id)

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
        """Index or re-index a global note embedding."""
        if not self.is_enabled():
            return
        chromadb_service.upsert_global_note(
            note_id=note_id,
            title=title,
            content=content,
            tags=tags,
            format=format,
            updated_at=updated_at,
        )

    def delete_global_note(self, *, note_id: int) -> None:
        """Remove a global note from the index."""
        if not self.is_enabled():
            return
        chromadb_service.delete_global_note_embedding(note_id=note_id)

    def get_similar_project_notes(
        self,
        *,
        project_path: str,
        query_text: str,
        top_k: int = 3,
    ) -> list[dict[str, object]]:
        """Retrieve similar project notes for a query."""
        if not self.is_enabled():
            return []
        return chromadb_service.search_notes(
            project_path=project_path,
            query_text=query_text,
            top_k=top_k,
            include_captions=False,
        )

    def get_similar_global_notes(self, *, query_text: str, top_k: int = 3) -> list[dict[str, object]]:
        """Retrieve similar global notes for a query."""
        if not self.is_enabled():
            return []
        return chromadb_service.search_global_notes(query_text=query_text, top_k=top_k)

    def rebuild_notes_for_project(
        self,
        *,
        project_path: str,
        notes: list[dict[str, object]],
    ) -> dict[str, object]:
        """Re-index all project notes (e.g., on project open).

        Args:
            project_path: Path to project database.
            notes: List of dicts with keys: id, title, content, tags, format, updated_at.
        """
        if not self.is_enabled():
            return {"rag_enabled": False}

        indexed = 0
        for note in notes:
            note_id = note.get("id")
            if note_id is None:
                continue
            chromadb_service.upsert_note(
                project_path=project_path,
                note_id=int(note_id),
                title=str(note.get("title") or ""),
                content=str(note.get("content") or ""),
                tags=str(note.get("tags") or ""),
                format=str(note.get("format") or "text"),
                updated_at=str(note.get("updated_at") or ""),
            )
            indexed += 1

        return {"rag_enabled": True, "indexed_notes": indexed, "project_path": project_path}


rag_service = RAGService()
