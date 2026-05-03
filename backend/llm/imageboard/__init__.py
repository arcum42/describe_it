"""Imageboard API client framework."""

from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.llm.imageboard.http_client import ImageboardHTTPClient, create_imageboard_client

__all__ = [
    "ImageboardClient",
    "ImageboardImage",
    "SearchResult",
    "ImageboardHTTPClient",
    "create_imageboard_client",
]
