"""Service for orchestrating imageboard imports into projects."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.llm.imageboard import (
    DanbooruClient,
    DerpibooruClient,
    E621Client,
    ImageboardClient,
    SearchResult,
    TantabusClient,
    TwibooruClient,
)
from backend.services.imageboard_credentials_service import get_imageboard_credentials_service
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ImportPreview:
    """Preview of images available for import."""

    board_id: str
    query: str
    sort_by: str
    total_available: int
    preview_images: list[dict]


@dataclass
class ImportResult:
    """Result of an import operation."""

    board_id: str
    imported_count: int
    failed_count: int
    skipped_count: int
    errors: list[str]


class ImageboardImportService:
    """Service for importing images from imageboards into projects."""

    def __init__(self):
        """Initialize the import service."""
        self.credentials_service = get_imageboard_credentials_service()

    async def get_client(self, board_id: str) -> Optional[ImageboardClient]:
        """
        Get an imageboard client for the specified board.

        Args:
            board_id: Board identifier (e.g., "e621", "derpibooru")

        Returns:
            Initialized client or None if board unsupported

        Raises:
            ValueError: If credentials are missing for boards that require auth
        """
        creds = self.credentials_service.get_credentials(board_id)
        api_key = creds.get("api_key") if creds else None
        username = creds.get("username") if creds else None

        if board_id == "derpibooru":
            return DerpibooruClient(api_key=api_key, username=username)
        elif board_id == "tantabus":
            return TantabusClient(api_key=api_key, username=username)
        elif board_id == "danbooru":
            if not (username and api_key):
                raise ValueError("Danbooru requires both username and API key")
            return DanbooruClient(api_key=api_key, username=username)
        elif board_id == "e621":
            if not (username and api_key):
                raise ValueError("e621 requires both username and API key")
            return E621Client(api_key=api_key, username=username)
        elif board_id == "twibooru":
            return TwibooruClient(api_key=api_key, username=username)
        else:
            raise ValueError(f"Unknown board: {board_id}")

    async def search(
        self,
        board_id: str,
        query: str,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """
        Search an imageboard.

        Args:
            board_id: Board identifier
            query: Search terms
            sort_by: Sort field
            sort_direction: "asc" or "desc"
            page: Page number (1-indexed)
            per_page: Results per page

        Returns:
            SearchResult with images and pagination info

        Raises:
            ValueError: If board invalid or credentials missing
        """
        client = await self.get_client(board_id)
        if not client:
            raise ValueError(f"Board not supported: {board_id}")

        try:
            result = await client.search(
                query=query,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page=page,
                per_page=per_page,
            )
            return result
        finally:
            await client.close()

    async def get_import_preview(
        self,
        board_id: str,
        query: str,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        preview_count: int = 5,
    ) -> ImportPreview:
        """
        Get preview of images available for import.

        Args:
            board_id: Board identifier
            query: Search terms
            sort_by: Sort field
            sort_direction: "asc" or "desc"
            preview_count: Number of preview images to return

        Returns:
            ImportPreview with sample images and total count

        Raises:
            ValueError: If board invalid or credentials missing
        """
        search_result = await self.search(
            board_id=board_id,
            query=query,
            sort_by=sort_by,
            sort_direction=sort_direction,
            page=1,
            per_page=preview_count,
        )

        preview_images = []
        for img in search_result.images[:preview_count]:
            preview_images.append(
                {
                    "id": img.id,
                    "title": img.title,
                    "url": img.image_url,
                    "source_url": img.source_url,
                    "tags": img.tags,
                    "rating": img.rating,
                }
            )

        return ImportPreview(
            board_id=board_id,
            query=query,
            sort_by=sort_by,
            total_available=search_result.total_count,
            preview_images=preview_images,
        )

    async def import_images(
        self,
        project_path: str,
        board_id: str,
        query: str,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        import_count: int = 10,
        include_tags_in_caption: bool = True,
    ) -> ImportResult:
        """
        Import images from imageboard into project.

        Args:
            project_path: Path to project database
            board_id: Board identifier
            query: Search terms
            sort_by: Sort field
            sort_direction: "asc" or "desc"
            import_count: Number of images to import
            include_tags_in_caption: Whether to create captions from tags

        Returns:
            ImportResult with counts and any errors

        Raises:
            ValueError: If project path invalid or board unsupported
        """
        result = ImportResult(
            board_id=board_id,
            imported_count=0,
            failed_count=0,
            skipped_count=0,
            errors=[],
        )

        try:
            # Get client and perform search
            client = await self.get_client(board_id)
            if not client:
                raise ValueError(f"Board not supported: {board_id}")

            search_result = await client.search(
                query=query,
                sort_by=sort_by,
                sort_direction=sort_direction,
                page=1,
                per_page=import_count,
            )

            # Open project database
            session_factory = create_sqlite_session_factory(project_path)

            # Import each image
            for image_data in search_result.images[:import_count]:
                try:
                    await self._import_single_image(
                        session_factory=session_factory,
                        client=client,
                        image_data=image_data,
                        board_id=board_id,
                        include_tags=include_tags_in_caption,
                    )
                    result.imported_count += 1

                except Exception as e:
                    logger.error(f"Failed to import image {image_data.id}: {e}")
                    result.failed_count += 1
                    result.errors.append(f"Image {image_data.id}: {str(e)}")

            return result

        except Exception as e:
            logger.error(f"Import operation failed: {e}")
            result.errors.append(str(e))
            raise
        finally:
            await client.close()

    async def _import_single_image(
        self,
        session_factory,
        client: ImageboardClient,
        image_data,
        board_id: str,
        include_tags: bool = True,
    ) -> None:
        """
        Import a single image into the project database.

        Args:
            session_factory: SQLAlchemy session factory for project
            client: ImageboardClient instance
            image_data: ImageboardImage from search result
            board_id: Board identifier for source tracking
            include_tags: Whether to create caption from tags

        Raises:
            Exception: If download or database operations fail
        """
        # Download image bytes
        image_bytes = await client.fetch_image_bytes(image_data.image_url)

        if not image_bytes:
            raise ValueError("Failed to download image")

        # Derive file extension from URL; fall back to .jpg
        url_path = image_data.image_url.split("?")[0]
        ext = url_path.rsplit(".", 1)[-1].lower() if "." in url_path else "jpg"
        if ext not in {"jpg", "jpeg", "png", "gif", "webp"}:
            ext = "jpg"
        filename = f"{board_id}_{image_data.id}.{ext}"

        # Create image record
        with session_factory() as session:
            project = session.scalar(select(ProjectRecord).limit(1))
            if project is None:
                raise ValueError("No project record found in database")

            image_record = ImageRecord(
                project_id=project.id,
                filename=filename,
                original_blob=image_bytes,
                working_blob=None,
                width=None,
                height=None,
                included=True,
            )
            session.add(image_record)
            session.flush()  # Get the ID

            # Create caption from tags if requested
            if include_tags and image_data.tags:
                # Normalize tags for the board
                normalized_tags = client.normalize_tags(image_data.tags)
                caption_text = ", ".join(normalized_tags)

                # Include rating if available
                if image_data.rating:
                    caption_text = f"[{image_data.rating}] {caption_text}"

                caption_record = CaptionRecord(
                    image_id=image_record.id,
                    text=caption_text,
                    source=f"imageboard:{board_id}",
                )
                session.add(caption_record)

            session.commit()

    async def batch_search(
        self,
        boards: list[str],
        query: str,
        per_board_count: int = 5,
    ) -> dict[str, SearchResult]:
        """
        Search multiple boards in parallel.

        Args:
            boards: List of board IDs to search
            query: Search query
            per_board_count: Results per board

        Returns:
            Dict mapping board_id to SearchResult

        Raises:
            ValueError: If any board invalid or credentials missing
        """
        tasks = [
            self.search(board_id=board, query=query, per_page=per_board_count)
            for board in boards
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for board_id, result in zip(boards, results):
            if isinstance(result, Exception):
                logger.error(f"Search failed for {board_id}: {result}")
                output[board_id] = None
            else:
                output[board_id] = result

        return output


# Singleton instance
_import_service: Optional[ImageboardImportService] = None


def get_imageboard_import_service() -> ImageboardImportService:
    """Get or create the singleton import service."""
    global _import_service
    if _import_service is None:
        _import_service = ImageboardImportService()
    return _import_service
