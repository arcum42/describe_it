"""Abstract base class for imageboard API clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ImageboardImage:
    """Represents one image from imageboard search result."""

    id: str | int
    title: str
    image_url: str
    source_url: str | None = None
    tags: list[str] = field(default_factory=list)
    rating: str | None = None


@dataclass
class SearchResult:
    """Standardized search result from imageboard."""

    images: list[ImageboardImage]
    total_count: int
    page: int
    has_next_page: bool


class ImageboardClient(ABC):
    """Abstract base for imageboard API clients."""

    board_name: str = ""  # "derpibooru", "danbooru", etc.
    board_display_name: str = ""
    base_url: str = ""
    supports_galleries: bool = False
    supports_pools: bool = False
    available_sorts: list[str] = []

    @abstractmethod
    async def search(
        self,
        query: str,
        sort_by: str = "relevance",
        sort_direction: str = "desc",
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> SearchResult:
        """
        Execute search query.

        Args:
            query: Search terms (board-specific syntax may apply)
            sort_by: Sort field; must be in available_sorts
            sort_direction: "asc" or "desc"
            page: Page number (1-indexed)
            per_page: Results per page
            **kwargs: Board-specific options

        Returns:
            SearchResult with images and pagination info
        """

    @abstractmethod
    async def get_image_details(self, image_id: str | int) -> ImageboardImage:
        """
        Fetch detailed information about a specific image.

        Args:
            image_id: Board-specific image ID

        Returns:
            ImageboardImage with full details
        """

    @abstractmethod
    def normalize_tags(self, raw_tags: list[str]) -> list[str]:
        """
        Normalize board-specific tags for consistent captions.

        Args:
            raw_tags: Raw tags from API response

        Returns:
            Normalized tag list (lowercase, filtered, etc.)
        """

    @abstractmethod
    async def fetch_image_bytes(self, image_url: str) -> bytes:
        """
        Download image data from URL.

        Args:
            image_url: Direct URL to image file

        Returns:
            Image file contents as bytes

        Raises:
            ValueError: If download fails or content is invalid
        """

    async def get_gallery_or_pool(self, gallery_id: int) -> SearchResult:
        """
        Fetch images from a specific gallery/pool (optional).

        Args:
            gallery_id: Gallery/pool ID

        Returns:
            SearchResult with all images from gallery

        Raises:
            NotImplementedError: If board doesn't support galleries/pools
        """
        if not self.supports_galleries and not self.supports_pools:
            raise NotImplementedError(f"{self.board_name} does not support galleries/pools")
        raise NotImplementedError("Subclass must implement get_gallery_or_pool")
