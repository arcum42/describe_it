"""Imageboard API client framework."""

from backend.llm.imageboard.base import ImageboardClient, ImageboardImage, SearchResult
from backend.llm.imageboard.danbooru import DanbooruClient
from backend.llm.imageboard.derpibooru import DerpibooruClient
from backend.llm.imageboard.e621 import E621Client
from backend.llm.imageboard.http_client import ImageboardHTTPClient, create_imageboard_client
from backend.llm.imageboard.tantabus import TantabusClient
from backend.llm.imageboard.twibooru import TwibooruClient

__all__ = [
    "ImageboardClient",
    "ImageboardImage",
    "SearchResult",
    "ImageboardHTTPClient",
    "create_imageboard_client",
    "DerpibooruClient",
    "TantabusClient",
    "DanbooruClient",
    "E621Client",
    "TwibooruClient",
]
