"""Service for managing imageboard API credentials."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from backend.config import get_settings
from backend.db.models import ImageboardCredential
from backend.db.session import create_sqlite_session_factory


IMAGEBOARD_BOARDS = {
    "e621": {
        "display_name": "e621",
        "base_url": "https://e621.net",
        "requires_auth": True,
        "requires_username": True,
    },
    "derpibooru": {
        "display_name": "Derpibooru",
        "base_url": "https://derpibooru.org",
        "requires_auth": False,
        "requires_username": False,
    },
    "danbooru": {
        "display_name": "Danbooru",
        "base_url": "https://danbooru.donmai.us",
        "requires_auth": True,
        "requires_username": True,
    },
    "twibooru": {
        "display_name": "Twibooru",
        "base_url": "https://twibooru.org",
        "requires_auth": False,
        "requires_username": False,
    },
    "tantabus": {
        "display_name": "Tantabus",
        "base_url": "https://tantabus.ai",
        "requires_auth": False,
        "requires_username": False,
    },
}


class ImageboardCredentialsService:
    """Manage imageboard API credentials."""

    def __init__(self) -> None:
        settings = get_settings()
        self.app_db = settings.state_dir / "app_state.db"
        self.session_factory = create_sqlite_session_factory(self.app_db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure imageboard_credentials table exists in the database."""
        try:
            connection = sqlite3.connect(self.app_db)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS imageboard_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id VARCHAR(50) UNIQUE NOT NULL,
                    api_key TEXT,
                    username VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()
            connection.close()
        except Exception as e:
            # Log but don't fail; SQLAlchemy will handle errors when actually using the table
            pass

    def get_credentials(self, board_id: str) -> Optional[dict]:
        """
        Retrieve credentials for a board (internal use only).

        Args:
            board_id: The board identifier (e.g., "e621", "derpibooru")

        Returns:
            Dict with "api_key" and "username" if found, None otherwise
        """
        if board_id not in IMAGEBOARD_BOARDS:
            return None

        with self.session_factory() as session:
            cred = session.scalar(select(ImageboardCredential).where(ImageboardCredential.board_id == board_id))
            if cred is None:
                return None
            return {"api_key": cred.api_key, "username": cred.username}

    def get_all_credentials_summary(self) -> list[dict]:
        """
        Get masked summary of all stored credentials for UI display.

        Returns:
            List of dicts with board_id, display_name, has_key, masked_key, username, created_at
        """
        with self.session_factory() as session:
            creds = session.scalars(select(ImageboardCredential)).all()

        result = []
        for board_id, board_info in IMAGEBOARD_BOARDS.items():
            cred = next((c for c in creds if c.board_id == board_id), None)
            if cred is None:
                result.append(
                    {
                        "board_id": board_id,
                        "display_name": board_info["display_name"],
                        "has_key": False,
                        "masked_key": None,
                        "username": None,
                        "created_at": None,
                    }
                )
            else:
                masked_key = None
                if cred.api_key:
                    if len(cred.api_key) > 4:
                        masked_key = "****" + cred.api_key[-4:]
                    else:
                        masked_key = "****"
                result.append(
                    {
                        "board_id": board_id,
                        "display_name": board_info["display_name"],
                        "has_key": cred.api_key is not None,
                        "masked_key": masked_key,
                        "username": cred.username,
                        "created_at": cred.created_at.isoformat() if cred.created_at else None,
                    }
                )
        return result

    def save_credentials(self, board_id: str, api_key: str, username: Optional[str] = None) -> dict:
        """
        Save or update credentials for a board.

        Args:
            board_id: The board identifier
            api_key: The API key (required)
            username: Optional username for boards that need it

        Returns:
            Dict with success status and board_id

        Raises:
            ValueError: If board_id is invalid or api_key is empty
        """
        if board_id not in IMAGEBOARD_BOARDS:
            raise ValueError(f"Unknown board: {board_id}")

        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        with self.session_factory() as session:
            cred = session.scalar(select(ImageboardCredential).where(ImageboardCredential.board_id == board_id))

            if cred is None:
                cred = ImageboardCredential(
                    board_id=board_id,
                    api_key=api_key.strip(),
                    username=username.strip() if username else None,
                )
                session.add(cred)
            else:
                cred.api_key = api_key.strip()
                cred.username = username.strip() if username else None

            session.commit()

        return {"success": True, "board_id": board_id}

    def delete_credentials(self, board_id: str) -> dict:
        """
        Remove credentials for a board.

        Args:
            board_id: The board identifier

        Returns:
            Dict with success status and board_id
        """
        if board_id not in IMAGEBOARD_BOARDS:
            raise ValueError(f"Unknown board: {board_id}")

        with self.session_factory() as session:
            cred = session.scalar(select(ImageboardCredential).where(ImageboardCredential.board_id == board_id))

            if cred is not None:
                session.delete(cred)
                session.commit()

        return {"success": True, "board_id": board_id}

    def get_available_boards(self) -> list[dict]:
        """
        Get list of available boards with metadata.

        Returns:
            List of dicts with board_id, display_name, requires_auth, requires_username
        """
        result = []
        for board_id, board_info in IMAGEBOARD_BOARDS.items():
            result.append(
                {
                    "board_id": board_id,
                    "display_name": board_info["display_name"],
                    "base_url": board_info["base_url"],
                    "requires_auth": board_info["requires_auth"],
                    "requires_username": board_info["requires_username"],
                }
            )
        return result


# Singleton instance
_credentials_service: Optional[ImageboardCredentialsService] = None


def get_imageboard_credentials_service() -> ImageboardCredentialsService:
    """Get or create the singleton credentials service."""
    global _credentials_service
    if _credentials_service is None:
        _credentials_service = ImageboardCredentialsService()
    return _credentials_service
