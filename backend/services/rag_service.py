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
        """Retrieve similar captions for a query.

        Args:
            project_path: Path to project database.
            query_text: Query or current caption.
            top_k: Number of results.

        Returns:
            List of similar caption texts, sorted by similarity.
        """
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
        """Build system prompt with optional few-shot examples from RAG.

        Args:
            base_system_prompt: Base system prompt.
            project_path: Path to project database.
            current_caption: Current caption (used for similarity search).
            include_few_shot: Whether to include few-shot examples.

        Returns:
            Enhanced system prompt.
        """
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
        """Rebuild embeddings for a project.

        Args:
            project_path: Path to project database.
            captions: List of dicts with 'id', 'text' keys.

        Returns:
            Summary of rebuild operation.
        """
        if not self.is_enabled():
            return {"rag_enabled": False}

        return chromadb_service.rebuild_embeddings(project_path=project_path, captions=captions)


rag_service = RAGService()
