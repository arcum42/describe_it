"""Danbooru imageboard API client."""

from __future__ import annotations

import base64
import logging
from typing import Optional

from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.llm.imageboard.http_client import create_imageboard_client

logger = logging.getLogger(__name__)


class DanbooruClient(ImageboardClient):
    """Client for Danbooru API (Rails Booru framework)."""

    board_name = "danbooru"
    board_display_name = "Danbooru"
    base_url = "https://danbooru.donmai.us"
    supports_galleries = False
    supports_pools = True
    available_sorts = [
        "date",
        "score",
        "popular",
        "rank",
    ]

    def __init__(self, api_key: Optional[str] = None, username: Optional[str] = None):
        """
        Initialize Danbooru client.

        Args:
            api_key: API key (required for Danbooru)
            username: Username (required for Danbooru authentication)
        """
        self.api_key = api_key
        self.username = username
        self.http_client = None

    async def _ensure_http_client(self) -> None:
        """Initialize HTTP client with authentication."""
        if self.http_client is None:
            user_agent = "DescribeIt/1.0 (+describe_it)"
            self.http_client = await create_imageboard_client("danbooru", user_agent=user_agent)
            
            # Set up authentication if credentials available
            if self.username and self.api_key:
                auth_string = f"{self.username}:{self.api_key}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                self.http_client.set_auth_header(f"Basic {encoded_auth}")

    async def search(
        self,
        query: str,
        sort_by: str = "date",
        sort_direction: str = "desc",
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> SearchResult:
        """
        Search Danbooru for images.

        Args:
            query: Search terms (space-separated, supports negation with -)
            sort_by: Sort field from available_sorts
            sort_direction: "asc" or "desc" (ignored; Danbooru controls direction)
            page: Page number (1-indexed)
            per_page: Results per page
            **kwargs: Additional options

        Returns:
            SearchResult with images and pagination info
        """
        await self._ensure_http_client()

        if sort_by not in self.available_sorts:
            sort_by = "date"

        params = {
            "tags": query,
            "limit": min(per_page, 200),
            "page": page,
        }

        # Add order parameter if available
        order_map = {
            "date": "id_desc" if sort_direction == "desc" else "id_asc",
            "score": "score_desc" if sort_direction == "desc" else "score_asc",
            "popular": "score_desc",
            "rank": "rank",
        }
        if sort_by in order_map:
            params["order"] = order_map[sort_by]

        try:
            response = await self.http_client.get(f"{self.base_url}/posts.json", params=params)

            images = []
            for img_data in response if isinstance(response, list) else response.get("posts", []):
                image = ImageboardImage(
                    id=img_data.get("id"),
                    title=img_data.get("source", f"post_{img_data.get('id')}"),
                    image_url=self._extract_image_url(img_data),
                    source_url=f"{self.base_url}/posts/{img_data.get('id')}",
                    tags=self._extract_tags(img_data),
                    rating=self._extract_rating(img_data),
                )
                images.append(image)

            return SearchResult(
                images=images,
                total_count=len(images) * page,  # Estimate; Danbooru doesn't provide total
                page=page,
                has_next_page=len(images) >= per_page,
            )

        except Exception as e:
            logger.error(f"Danbooru search failed: {e}")
            raise

    async def get_image_details(self, image_id: str | int) -> ImageboardImage:
        """
        Fetch detailed information about a specific image.

        Args:
            image_id: Danbooru post ID

        Returns:
            ImageboardImage with full details
        """
        await self._ensure_http_client()

        try:
            response = await self.http_client.get(f"{self.base_url}/posts/{image_id}.json")

            return ImageboardImage(
                id=response.get("id"),
                title=response.get("source", f"post_{image_id}"),
                image_url=self._extract_image_url(response),
                source_url=f"{self.base_url}/posts/{image_id}",
                tags=self._extract_tags(response),
                rating=self._extract_rating(response),
            )

        except Exception as e:
            logger.error(f"Failed to fetch Danbooru post {image_id}: {e}")
            raise

    def normalize_tags(self, raw_tags: list[str]) -> list[str]:
        """
        Normalize Danbooru tags for consistent captions.

        Args:
            raw_tags: Raw tags from API response

        Returns:
            Normalized tag list
        """
        skip_tags = {
            "safe",
            "questionable",
            "explicit",
            "translated",
            "uncensored",
            "text",
        }

        normalized = []
        for tag in raw_tags:
            tag = tag.lower().strip()
            if not tag or tag in skip_tags:
                continue
            # Danbooru uses underscores; replace with spaces for readability
            tag = tag.replace("_", " ")
            normalized.append(tag)

        return sorted(normalized)

    async def fetch_image_bytes(self, image_url: str) -> bytes:
        """
        Download image data from URL.

        Args:
            image_url: Direct URL to image file

        Returns:
            Image file contents as bytes
        """
        await self._ensure_http_client()
        return await self.http_client.get_binary(image_url)

    async def close(self) -> None:
        """Close HTTP session."""
        if self.http_client:
            await self.http_client.close()

    @staticmethod
    def _extract_image_url(post_data: dict) -> str:
        """Extract image URL from Danbooru post response."""
        # Prefer full URL, fall back to sample
        if "file" in post_data and post_data["file"].get("url"):
            return post_data["file"]["url"]
        if "sample" in post_data and post_data["sample"].get("url"):
            return post_data["sample"]["url"]
        return ""

    @staticmethod
    def _extract_tags(post_data: dict) -> list[str]:
        """Extract tags from Danbooru post response."""
        tags = []
        
        # Danbooru splits tags by category
        tag_fields = [
            "tag_string_general",
            "tag_string_artist",
            "tag_string_character",
            "tag_string_copyright",
            "tag_string_meta",
        ]
        
        for field in tag_fields:
            tag_string = post_data.get(field, "")
            if tag_string:
                tags.extend(tag_string.split())
        
        return [t for t in tags if t]

    @staticmethod
    def _extract_rating(post_data: dict) -> Optional[str]:
        """Extract rating from Danbooru post response."""
        rating = post_data.get("rating")
        # Danbooru uses single letters: s (safe), q (questionable), e (explicit)
        rating_map = {
            "s": "safe",
            "q": "questionable",
            "e": "explicit",
        }
        return rating_map.get(rating)
