"""e621 imageboard API client."""

from __future__ import annotations

import base64
import logging
from typing import Optional

from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.llm.imageboard.http_client import create_imageboard_client

logger = logging.getLogger(__name__)


class E621Client(ImageboardClient):
    """Client for e621 API (Danbooru fork with strict User-Agent requirement)."""

    board_name = "e621"
    board_display_name = "e621"
    base_url = "https://e621.net"
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
        Initialize e621 client.

        Args:
            api_key: API key (required for e621)
            username: Username (required for e621 authentication)
        """
        self.api_key = api_key
        self.username = username
        self.http_client = None

    async def _ensure_http_client(self) -> None:
        """Initialize HTTP client with authentication and custom User-Agent."""
        if self.http_client is None:
            # e621 REQUIRES a custom User-Agent with username
            # Default UA will result in 403 Forbidden
            if self.username:
                user_agent = f"DescribeIt/1.0 (by {self.username} on e621)"
            else:
                user_agent = "DescribeIt/1.0"
            
            self.http_client = await create_imageboard_client("e621", user_agent=user_agent)
            
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
        Search e621 for images.

        Args:
            query: Search terms (space-separated, supports negation with -)
            sort_by: Sort field from available_sorts
            sort_direction: "asc" or "desc"
            page: Page number (1-indexed)
            per_page: Results per page (max 320)
            **kwargs: Additional options

        Returns:
            SearchResult with images and pagination info
        """
        await self._ensure_http_client()

        if sort_by not in self.available_sorts:
            sort_by = "date"

        params = {
            "tags": query,
            "limit": min(per_page, 320),
            "page": page,
        }

        # Add order parameter
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
            for img_data in response.get("posts", []):
                image = ImageboardImage(
                    id=img_data.get("id"),
                    title=img_data.get("source", [None])[0] if img_data.get("source") else f"post_{img_data.get('id')}",
                    image_url=self._extract_image_url(img_data),
                    source_url=f"{self.base_url}/posts/{img_data.get('id')}",
                    tags=self._extract_tags(img_data),
                    creator_tags=self._extract_creator_tags(img_data),
                    rating=self._extract_rating(img_data),
                )
                images.append(image)

            # e621 post search omits total count; attempt a tag-based lookup.
            total_count = response.get("count") if isinstance(response, dict) else None
            if not isinstance(total_count, int):
                total_count = await self._fetch_total_count(query)
            if not isinstance(total_count, int):
                total_count = len(images) * page

            return SearchResult(
                images=images,
                total_count=total_count,
                page=page,
                has_next_page=len(images) >= per_page,
            )

        except Exception as e:
            logger.error(f"e621 search failed: {e}")
            raise

    async def _fetch_total_count(self, query: str) -> Optional[int]:
        """Fetch approximate total count for simple e621 queries.

        e621 does not provide a general total count in /posts.json responses.
        For single-tag queries, we can query /tags.json and use post_count.
        """
        tokens = [t for t in query.split() if t]
        positive_tokens = [t for t in tokens if not t.startswith("-")]
        content_tokens = [t for t in positive_tokens if not t.startswith("rating:")]

        # Reliable only for one direct tag token.
        if len(content_tokens) != 1:
            return None

        tag_name = content_tokens[0]

        try:
            response = await self.http_client.get(
                f"{self.base_url}/tags.json",
                params={"search[name_matches]": tag_name, "limit": 1},
            )

            if not isinstance(response, list) or not response:
                return None

            top = response[0]
            if not isinstance(top, dict):
                return None
            if top.get("name") != tag_name:
                return None

            posts_count = top.get("post_count")
            if isinstance(posts_count, int):
                return posts_count
            if isinstance(posts_count, str):
                try:
                    return int(posts_count)
                except ValueError:
                    return None
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch e621 total count for query '{query}': {e}")
            return None

    async def get_image_details(self, image_id: str | int) -> ImageboardImage:
        """
        Fetch detailed information about a specific image.

        Args:
            image_id: e621 post ID

        Returns:
            ImageboardImage with full details
        """
        await self._ensure_http_client()

        try:
            response = await self.http_client.get(f"{self.base_url}/posts/{image_id}.json")
            post_data = response.get("post", response)

            return ImageboardImage(
                id=post_data.get("id"),
                title=post_data.get("source", [None])[0] if post_data.get("source") else f"post_{image_id}",
                image_url=self._extract_image_url(post_data),
                source_url=f"{self.base_url}/posts/{image_id}",
                tags=self._extract_tags(post_data),
                creator_tags=self._extract_creator_tags(post_data),
                rating=self._extract_rating(post_data),
            )

        except Exception as e:
            logger.error(f"Failed to fetch e621 post {image_id}: {e}")
            raise

    def normalize_tags(self, raw_tags: list[str]) -> list[str]:
        """
        Normalize e621 tags for consistent captions.

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
        }

        normalized = []
        for tag in raw_tags:
            tag = tag.lower().strip()
            if not tag or tag in skip_tags:
                continue
            # e621 uses underscores; replace with spaces for readability
            tag = tag.replace("_", " ")
            normalized.append(tag)

        return sorted(normalized)

    async def close(self) -> None:
        """Close HTTP session."""
        if self.http_client:
            await self.http_client.close()

    @staticmethod
    def _extract_image_url(post_data: dict) -> str:
        """Extract image URL from e621 post response."""
        # e621 includes file URL in the file object
        if "file" in post_data and post_data["file"].get("url"):
            return post_data["file"]["url"]
        if "sample" in post_data and post_data["sample"].get("url"):
            return post_data["sample"]["url"]
        return ""

    @staticmethod
    def _extract_tags(post_data: dict) -> list[str]:
        """Extract tags from e621 post response."""
        tags = []
        
        # e621 organizes tags by category in the tags object
        if "tags" in post_data:
            tags_obj = post_data["tags"]
            if isinstance(tags_obj, dict):
                # Combine non-creator categories only; creator tags are preserved separately.
                for category in ["general", "species", "character", "copyright", "meta"]:
                    if category in tags_obj:
                        tags.extend(tags_obj[category])
            elif isinstance(tags_obj, list):
                tags.extend(tags_obj)
        
        return [t for t in tags if t]

    @staticmethod
    def _extract_creator_tags(post_data: dict) -> list[str]:
        """Extract creator names from e621 post response."""
        if "tags" not in post_data:
            return []

        tags_obj = post_data["tags"]
        if not isinstance(tags_obj, dict):
            return []

        artists = tags_obj.get("artist", [])
        if not isinstance(artists, list):
            return []
        return [tag for tag in artists if tag]

    @staticmethod
    def _extract_rating(post_data: dict) -> Optional[str]:
        """Extract rating from e621 post response."""
        rating = post_data.get("rating")
        # e621 uses single letters: s (safe), q (questionable), e (explicit)
        rating_map = {
            "s": "safe",
            "q": "questionable",
            "e": "explicit",
        }
        return rating_map.get(rating)
