"""HTTP client utilities for imageboard API requests."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, min_delay: float = 0.1):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum seconds between requests
        """
        self.min_delay = min_delay
        self.last_request_time = 0.0

    async def acquire(self) -> None:
        """Wait if necessary to enforce rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()


class ImageboardHTTPClient:
    """HTTP client with rate limiting, retries, and board-specific handling."""

    def __init__(
        self,
        board_id: str,
        user_agent: Optional[str] = None,
        min_delay: float = 0.1,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize HTTP client for imageboard.

        Args:
            board_id: Board identifier (e.g., "e621", "derpibooru")
            user_agent: Custom User-Agent string (required for some boards)
            min_delay: Minimum seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient errors
        """
        self.board_id = board_id
        self.user_agent = user_agent or f"DescribeIt/1.0 (+describe_it)"
        self.min_delay = min_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(min_delay)
        self._default_headers: dict[str, str] = {}

        # Create session with connection pooling
        self._session: Optional[httpx.AsyncClient] = None

    async def get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session."""
        if self._session is None:
            headers = {"User-Agent": self.user_agent}
            headers.update(self._default_headers)
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5),
                headers=headers,
            )
        return self._session

    def set_auth_header(self, auth_string: str) -> None:
        """
        Set authentication header for this client.

        Args:
            auth_string: Authorization header value (e.g., "Basic <base64>")
        """
        self._default_headers["Authorization"] = auth_string

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session is not None:
            await self._session.aclose()
            self._session = None

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make GET request with retries and rate limiting.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional httpx options

        Returns:
            Parsed JSON response

        Raises:
            ValueError: If all retries exhausted or response invalid
            httpx.HTTPError: For network errors
        """
        await self.rate_limiter.acquire()

        session = await self.get_session()
        merged_headers = {**(headers or {})}

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"[{self.board_id}] GET {url} (attempt {attempt}/{self.max_retries})"
                )
                response = await session.get(url, params=params, headers=merged_headers, **kwargs)

                # Handle Derpibooru 501 challenge (anti-bot middleware)
                if response.status_code == 501:
                    logger.warning(
                        f"[{self.board_id}] Received 501 challenge; waiting 5+ seconds"
                    )
                    await asyncio.sleep(5.0)
                    # Don't retry immediately; let next request wait appropriate time
                    if attempt < self.max_retries:
                        continue
                    raise ValueError("Derpibooru 501 challenge after multiple retries")

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", str(60))
                    wait_time = float(retry_after)
                    logger.warning(
                        f"[{self.board_id}] Rate limited; waiting {wait_time} seconds"
                    )
                    await asyncio.sleep(wait_time)
                    if attempt < self.max_retries:
                        continue
                    raise ValueError(f"Rate limited after {self.max_retries} retries")

                # Handle authentication errors
                if response.status_code in (401, 403):
                    raise ValueError(
                        f"Authentication error ({response.status_code}): check credentials"
                    )

                # Handle server errors (5xx) with exponential backoff
                if response.status_code >= 500:
                    backoff = 2 ** (attempt - 1)
                    logger.warning(
                        f"[{self.board_id}] Server error {response.status_code}; "
                        f"waiting {backoff}s before retry"
                    )
                    await asyncio.sleep(backoff)
                    if attempt < self.max_retries:
                        continue
                    raise ValueError(f"Server error {response.status_code} after {self.max_retries} retries")

                # Handle other client errors
                if response.status_code >= 400:
                    raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")

                # Success
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    logger.warning(f"[{self.board_id}] Timeout; waiting {backoff}s before retry")
                    await asyncio.sleep(backoff)
                    continue
                raise ValueError(f"Request timeout after {self.max_retries} retries") from e

            except (httpx.ConnectError, httpx.PoolTimeout) as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    logger.warning(f"[{self.board_id}] Connection error; waiting {backoff}s")
                    await asyncio.sleep(backoff)
                    continue
                raise ValueError(f"Connection error after {self.max_retries} retries") from e

        # If we get here, all retries exhausted
        if last_error:
            raise last_error
        raise ValueError(f"Request failed after {self.max_retries} retries")

    async def get_binary(self, url: str, **kwargs) -> bytes:
        """
        Download binary data (image, etc.).

        Args:
            url: Request URL
            **kwargs: Additional httpx options

        Returns:
            Binary content

        Raises:
            ValueError: If download fails
        """
        await self.rate_limiter.acquire()

        session = await self.get_session()
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"[{self.board_id}] GET_BINARY {url} (attempt {attempt})")
                response = await session.get(url, **kwargs)

                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = float(response.headers.get("Retry-After", "60"))
                    await asyncio.sleep(wait_time)
                    if attempt < self.max_retries:
                        continue

                # Handle errors
                if response.status_code >= 400:
                    raise ValueError(f"Download failed: HTTP {response.status_code}")

                response.raise_for_status()

                # Validate content length if available
                content_length = response.headers.get("content-length")
                if content_length:
                    expected_length = int(content_length)
                    actual_length = len(response.content)
                    if actual_length != expected_length:
                        logger.warning(
                            f"[{self.board_id}] Content length mismatch: "
                            f"expected {expected_length}, got {actual_length}"
                        )

                return response.content

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    await asyncio.sleep(backoff)
                    continue

        if last_error:
            raise last_error
        raise ValueError(f"Binary download failed after {self.max_retries} retries")

    def parse_rate_limit_headers(self, response: dict[str, str]) -> dict[str, Any]:
        """
        Parse rate limit information from response headers.

        Handles different formats per board:
        - Danbooru: x-ratelimit-remaining, x-ratelimit-limit, x-ratelimit-reset
        - Twibooru: X-RateLimit-Remaining, X-RateLimit-Limit, X-RateLimit-Reset
        - e621/Derpibooru: typically in response body or not exposed

        Args:
            response: Response headers dict

        Returns:
            Dict with remaining, limit, reset_timestamp, etc.
        """
        # Normalize header names (case-insensitive)
        headers = {k.lower(): v for k, v in response.items()}

        limit_info = {}

        # Danbooru-style headers
        if "x-ratelimit-remaining" in headers:
            limit_info["remaining"] = int(headers.get("x-ratelimit-remaining", 0))
            limit_info["limit"] = int(headers.get("x-ratelimit-limit", 0))
            limit_info["reset"] = int(headers.get("x-ratelimit-reset", 0))

        # Twibooru-style headers (different casing)
        if "x-rl-remaining" in headers:
            limit_info["remaining"] = int(headers.get("x-rl-remaining", 0))
            limit_info["limit"] = int(headers.get("x-rl-limit", 0))
            limit_info["reset"] = int(headers.get("x-rl-reset", 0))

        return limit_info


async def create_imageboard_client(
    board_id: str,
    user_agent: Optional[str] = None,
    timeout: float = 30.0,
) -> ImageboardHTTPClient:
    """
    Create HTTP client with board-specific defaults.

    Args:
        board_id: Board identifier
        user_agent: Custom User-Agent (required for some boards)
        timeout: Request timeout in seconds

    Returns:
        Configured ImageboardHTTPClient instance
    """
    # Board-specific defaults
    board_config = {
        "e621": {"min_delay": 1.0},  # Hard limit: 2/sec, play it safe
        "danbooru": {"min_delay": 0.1},  # 10/sec global limit
        "derpibooru": {"min_delay": 0.25},  # ~20-30 per 5-10 sec
        "twibooru": {"min_delay": 6.0},  # 10/min search limit (very restrictive)
        "tantabus": {"min_delay": 0.25},  # Same as Derpibooru (fork)
    }

    config = board_config.get(board_id, {"min_delay": 0.5})

    return ImageboardHTTPClient(
        board_id=board_id,
        user_agent=user_agent,
        min_delay=config["min_delay"],
        timeout=timeout,
    )
