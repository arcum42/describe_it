"""Tantabus imageboard API client (Derpibooru fork)."""

from __future__ import annotations

import logging
from typing import Optional

from backend.llm.imageboard.derpibooru import DerpibooruClient

logger = logging.getLogger(__name__)


class TantabusClient(DerpibooruClient):
    """Client for Tantabus API (Derpibooru fork with nearly identical API)."""

    board_name = "tantabus"
    board_display_name = "Tantabus"
    base_url = "https://tantabus.ai"
    # Inherits all other properties and methods from Derpibooru

    def __init__(self, api_key: Optional[str] = None, username: Optional[str] = None):
        """
        Initialize Tantabus client.

        Args:
            api_key: Optional API key for higher rate limits
            username: Optional username (not typically used)
        """
        self.api_key = api_key
        self.username = username
        self.http_client = None
