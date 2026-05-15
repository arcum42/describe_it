"""Derpibooru imageboard API client."""

from __future__ import annotations

import logging
from typing import Optional

from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.llm.imageboard.http_client import create_imageboard_client

logger = logging.getLogger(__name__)


class DerpibooruClient(ImageboardClient):
    """Client for Derpibooru API (Philomena framework)."""

    board_name = "derpibooru"
    board_display_name = "Derpibooru"
    base_url = "https://derpibooru.org"
    supports_galleries = True
    supports_pools = False
    available_sorts = [
        "score",
        "wilson_score",
        "upvotes",
        "downvotes",
        "first_seen_at",
        "random",
        "faves",
        "tag_count",
        "relevance",
    ]

    def __init__(self, api_key: Optional[str] = None, username: Optional[str] = None):
        """
        Initialize Derpibooru client.

        Args:
            api_key: Optional API key for higher rate limits
            username: Optional username (not typically used)
        """
        self.api_key = api_key
        self.username = username
        self.http_client = None

    async def _ensure_http_client(self) -> None:
        """Initialize HTTP client if not already done."""
        if self.http_client is None:
            # Derpibooru optional auth; use simple User-Agent
            user_agent = (
                f"DescribeIt/1.0 (by {self.username})"
                if self.username
                else "DescribeIt/1.0 (+describe_it)"
            )
            self.http_client = await create_imageboard_client("derpibooru", user_agent=user_agent)

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
        Search Derpibooru for images.

        Args:
            query: Search terms (comma-separated, supports negation with -)
            sort_by: Sort field from available_sorts
            sort_direction: "asc" or "desc"
            page: Page number (1-indexed)
            per_page: Results per page (max 50)
            **kwargs: Additional options

        Returns:
            SearchResult with images and pagination info
        """
        await self._ensure_http_client()

        if sort_by not in self.available_sorts:
            sort_by = "relevance"

        params = {
            "q": query,
            "sf": sort_by,
            "sd": sort_direction,
            "page": page,
            "per_page": min(per_page, 50),
        }

        if self.api_key:
            params["key"] = self.api_key

        try:
            response = await self.http_client.get(f"{self.base_url}/api/v1/json/search/images", params=params)

            images = []
            for img_data in response.get("images", []):
                image = ImageboardImage(
                    id=img_data.get("id"),
                    title=img_data.get("name", f"image_{img_data.get('id')}"),
                    image_url=img_data.get("representations", {}).get("full", ""),
                    source_url=f"{self.base_url}/images/{img_data.get('id')}",
                    tags=self._extract_tags(img_data),
                    rating=self._extract_rating(img_data),
                )
                images.append(image)

            return SearchResult(
                images=images,
                total_count=response.get("total", len(images)),
                page=page,
                has_next_page=len(images) >= per_page,
            )

        except Exception as e:
            logger.error(f"Derpibooru search failed: {e}")
            raise

    async def get_image_details(self, image_id: str | int) -> ImageboardImage:
        """
        Fetch detailed information about a specific image.

        Args:
            image_id: Derpibooru image ID

        Returns:
            ImageboardImage with full details
        """
        await self._ensure_http_client()

        try:
            response = await self.http_client.get(f"{self.base_url}/api/v1/json/images/{image_id}")
            img_data = response.get("image", {})

            return ImageboardImage(
                id=img_data.get("id"),
                title=img_data.get("name", f"image_{image_id}"),
                image_url=img_data.get("representations", {}).get("full", ""),
                source_url=f"{self.base_url}/images/{image_id}",
                tags=self._extract_tags(img_data),
                rating=self._extract_rating(img_data),
            )

        except Exception as e:
            logger.error(f"Failed to fetch Derpibooru image {image_id}: {e}")
            raise

    def normalize_tags(self, raw_tags: list[str]) -> list[str]:
        """
        Normalize Derpibooru tags for consistent captions.

        Args:
            raw_tags: Raw tags from API response

        Returns:
            Normalized tag list
        """
        skip_tags = {
            "safe",
            "suggestive",
            "explicit",
            "grimdark",
            "semi-grimdark",
            "grotesque",
            "no characters",
            "safe for work",
            "not safe for work",
            "extended description",
            "derpibooru exclusive",
            "requires cropping",
        }

        normalized = []
        for tag in raw_tags:
            tag = tag.lower().strip()
            if not tag or tag in skip_tags:
                continue
            normalized.append(tag)

        return sorted(normalized)

    async def close(self) -> None:
        """Close HTTP session."""
        if self.http_client:
            await self.http_client.close()

    @staticmethod
    def _extract_tags(img_data: dict) -> list[str]:
        """Extract tags from Derpibooru image response."""
        tags = []
        for tag_obj in img_data.get("tags", []):
            if isinstance(tag_obj, dict):
                tags.append(tag_obj.get("name", ""))
            else:
                tags.append(str(tag_obj))
        return [t for t in tags if t]

    @staticmethod
    def _extract_rating(img_data: dict) -> Optional[str]:
        """Extract rating from Derpibooru image response."""
        rating = img_data.get("rating")
        if rating in ("safe", "suggestive", "explicit"):
            return rating

        # Some responses expose rating only as a tag; fall back to tag scan.
        raw_tags = DerpibooruClient._extract_tags(img_data)
        tag_set = {t.lower().strip() for t in raw_tags}
        if "explicit" in tag_set:
            return "explicit"
        if "suggestive" in tag_set:
            return "suggestive"
        if "safe" in tag_set:
            return "safe"
        return None
