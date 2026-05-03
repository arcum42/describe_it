"""
Tag management service for caption analysis and manipulation.
Provides parsing, categorization, and batch operations on tag-mode captions.
"""

import json
import re
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory


class TagService:
    """Service for managing tags in tag-mode datasets."""

    # Danbooru taxonomy color mapping
    TAG_CATEGORIES = {
        "character": {"color": "#FF6B9D", "order": 1},  # Pink
        "general": {"color": "#4ECDC4", "order": 2},  # Teal
        "species": {"color": "#95E1D3", "order": 3},  # Light teal
        "artist": {"color": "#F38181", "order": 4},  # Salmon
        "meta": {"color": "#AA96DA", "order": 5},  # Lavender
        "rating": {"color": "#FCBAD3", "order": 6},  # Light pink
        "unknown": {"color": "#B8B8B8", "order": 99},  # Gray
    }

    @staticmethod
    def parse_tags(caption_text: str) -> list[str]:
        """
        Parse comma-separated tags from caption text.
        Strips whitespace and filters empty tags.
        """
        if not caption_text or not isinstance(caption_text, str):
            return []
        
        tags = [tag.strip() for tag in caption_text.split(",")]
        return [tag for tag in tags if tag]

    @staticmethod
    def tags_to_text(tags: list[str]) -> str:
        """Convert list of tags to comma-separated text."""
        return ", ".join(tag.strip() for tag in tags if tag)

    @staticmethod
    def categorize_tag(tag: str) -> str:
        """
        Attempt to categorize a tag using simple heuristics.
        Returns one of: character, general, species, artist, meta, rating, unknown
        """
        if not tag:
            return "unknown"
        
        tag_lower = tag.lower()

        # Meta indicators (parentheses, underscores, hyphens, brackets)
        if any(c in tag for c in ["(", ")", "[", "]", "_"]):
            if "requested" in tag_lower or "commission" in tag_lower or "oc" in tag_lower:
                return "meta"

        # Artist indicators
        if "by " in tag_lower or "artist" in tag_lower or " artist" in tag_lower:
            return "artist"

        # Rating indicators
        if tag_lower in ["safe", "questionable", "explicit", "q-rating", "e-rating", "s-rating"]:
            return "rating"

        # Species indicators
        if any(word in tag_lower for word in ["furry", "feline", "canine", "elf", "human", "animal", "creature"]):
            return "species"

        # Character indicators (single capitalized words or known character prefixes)
        if len(tag.split()) == 1 and tag[0].isupper() and len(tag) > 2:
            return "character"

        # Default to general
        return "general"

    @staticmethod
    def get_tag_info(tag: str) -> dict:
        """Get display info for a tag (category, color, etc.)."""
        category = TagService.categorize_tag(tag)
        category_info = TagService.TAG_CATEGORIES.get(category, TagService.TAG_CATEGORIES["unknown"])
        
        return {
            "tag": tag,
            "category": category,
            "color": category_info["color"],
            "order": category_info["order"],
        }

    @staticmethod
    def get_all_tags_for_caption(caption: CaptionRecord) -> list[dict]:
        """Get parsed tags from a caption with categorization info."""
        tags = TagService.parse_tags(caption.text)
        return [TagService.get_tag_info(tag) for tag in tags]

    @staticmethod
    def update_caption_tags(
        session: Session,
        caption: CaptionRecord,
        tags: list[str],
    ) -> CaptionRecord:
        """Update a caption's text with new tags."""
        caption.text = TagService.tags_to_text(tags)
        session.add(caption)
        return caption

    @staticmethod
    def add_tags_to_captions(
        session: Session,
        captions: list[CaptionRecord],
        tags_to_add: list[str],
        position: str = "append",  # 'append' or 'prepend'
    ) -> list[CaptionRecord]:
        """
        Add tags to multiple captions.
        Position controls whether new tags are added before or after existing ones.
        Prevents duplicate tags.
        """
        updated = []
        for caption in captions:
            existing_tags = TagService.parse_tags(caption.text)
            
            # Filter out duplicates
            new_tags = [tag for tag in tags_to_add if tag.lower() not in [t.lower() for t in existing_tags]]
            
            if new_tags:
                if position == "prepend":
                    combined = new_tags + existing_tags
                else:
                    combined = existing_tags + new_tags
                
                caption.text = TagService.tags_to_text(combined)
                session.add(caption)
                updated.append(caption)
        
        return updated

    @staticmethod
    def remove_tags_from_captions(
        session: Session,
        captions: list[CaptionRecord],
        tags_to_remove: list[str],
    ) -> list[CaptionRecord]:
        """Remove specified tags from multiple captions (case-insensitive)."""
        updated = []
        tags_to_remove_lower = [tag.lower() for tag in tags_to_remove]
        
        for caption in captions:
            existing_tags = TagService.parse_tags(caption.text)
            filtered_tags = [
                tag for tag in existing_tags
                if tag.lower() not in tags_to_remove_lower
            ]
            
            if len(filtered_tags) < len(existing_tags):
                caption.text = TagService.tags_to_text(filtered_tags)
                session.add(caption)
                updated.append(caption)
        
        return updated

    @staticmethod
    def clear_all_tags(
        session: Session,
        captions: list[CaptionRecord],
    ) -> list[CaptionRecord]:
        """Clear all tags from multiple captions."""
        updated = []
        for caption in captions:
            if caption.text.strip():
                caption.text = ""
                session.add(caption)
                updated.append(caption)
        return updated

    @staticmethod
    def reorder_tags_for_caption(
        session: Session,
        caption: CaptionRecord,
        tag_order: list[str],
    ) -> CaptionRecord:
        """Reorder tags in a caption to match the provided order."""
        existing_tags = TagService.parse_tags(caption.text)
        
        # Ensure tag_order only contains existing tags, in provided order
        reordered = [
            tag for tag in tag_order
            if tag.lower() in [t.lower() for t in existing_tags]
        ]
        
        caption.text = TagService.tags_to_text(reordered)
        session.add(caption)
        return caption

    @staticmethod
    def get_tag_statistics(session: Session, project_id: int) -> dict:
        """Get tag usage statistics for a project."""
        # Fetch all captions for the project's included images
        captions = (
            session.query(CaptionRecord)
            .join(ImageRecord, CaptionRecord.image_id == ImageRecord.id)
            .filter(
                ImageRecord.project_id == project_id,
                ImageRecord.included == True,
            )
            .all()
        )

        tag_counts = {}
        tag_category_map = {}

        for caption in captions:
            tags = TagService.parse_tags(caption.text)
            for tag in tags:
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
                if tag_lower not in tag_category_map:
                    tag_category_map[tag_lower] = TagService.categorize_tag(tag)

        # Sort by frequency
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_tags": len(tag_counts),
            "total_occurrences": sum(tag_counts.values()),
            "top_tags": [
                {
                    "tag": tag,
                    "count": count,
                    "category": tag_category_map.get(tag, "unknown"),
                }
                for tag, count in sorted_tags[:50]
            ],
            "tag_frequency": {tag: count for tag, count in sorted_tags},
        }


# Public API functions that handle database sessions


def get_tags_for_caption(project_path: str, caption_id: int) -> dict:
    """Get parsed tags from a specific caption with categorization info."""
    session_factory = create_sqlite_session_factory(Path(project_path))
    
    with session_factory() as session:
        caption = session.query(CaptionRecord).filter(CaptionRecord.id == caption_id).first()
        
        if not caption:
            raise ValueError(f"Caption {caption_id} not found")
        
        tags = TagService.get_all_tags_for_caption(caption)
        return {"tags": tags, "text": caption.text}


def update_tags_for_caption(project_path: str, caption_id: int, tags: list[str]) -> dict:
    """Update tags for a specific caption."""
    session_factory = create_sqlite_session_factory(Path(project_path))
    
    with session_factory() as session:
        caption = session.query(CaptionRecord).filter(CaptionRecord.id == caption_id).first()
        
        if not caption:
            raise ValueError(f"Caption {caption_id} not found")
        
        TagService.update_caption_tags(session, caption, tags)
        session.commit()
        
        return {
            "caption_id": caption.id,
            "text": caption.text,
            "tags": TagService.get_all_tags_for_caption(caption),
        }


def batch_tag_operation(
    project_path: str,
    image_ids: list[int],
    operation: str,
    tags: list[str] | None = None,
    tag_order: list[str] | None = None,
) -> dict:
    """
    Perform batch tag operations on multiple images' active captions.
    Operations: add, remove, clear, reorder
    """
    if operation not in ["add", "remove", "clear", "reorder"]:
        raise ValueError(f"Invalid operation: {operation}")
    
    session_factory = create_sqlite_session_factory(Path(project_path))
    
    with session_factory() as session:
        # Get active captions for the specified images
        captions = (
            session.query(CaptionRecord)
            .join(ImageRecord, CaptionRecord.image_id == ImageRecord.id)
            .filter(
                ImageRecord.id.in_(image_ids),
                CaptionRecord.is_active == True,
            )
            .all()
        )
        
        if not captions:
            raise ValueError("No active captions found for the specified images")
        
        updated = []
        
        if operation == "add":
            if not tags:
                raise ValueError("Tags required for add operation")
            updated = TagService.add_tags_to_captions(session, captions, tags, position="append")
        
        elif operation == "remove":
            if not tags:
                raise ValueError("Tags required for remove operation")
            updated = TagService.remove_tags_from_captions(session, captions, tags)
        
        elif operation == "clear":
            updated = TagService.clear_all_tags(session, captions)
        
        elif operation == "reorder":
            if not tag_order:
                raise ValueError("Tag order required for reorder operation")
            # For batch reorder, apply the same order to all captions
            for caption in captions:
                TagService.reorder_tags_for_caption(session, caption, tag_order)
                updated.append(caption)
        
        session.commit()
        
        return {
            "operation": operation,
            "affected_captions": len(updated),
            "updated_captions": [
                {
                    "id": cap.id,
                    "text": cap.text,
                    "tags": TagService.get_all_tags_for_caption(cap),
                }
                for cap in updated
            ],
        }


def get_tag_statistics_for_project(project_path: str) -> dict:
    """Get tag usage statistics for a project (top 50 tags, frequency distribution)."""
    session_factory = create_sqlite_session_factory(Path(project_path))
    
    with session_factory() as session:
        project = session.query(ProjectRecord).first()
        
        if not project:
            raise ValueError("Project not found")
        
        return TagService.get_tag_statistics(session, project.id)
