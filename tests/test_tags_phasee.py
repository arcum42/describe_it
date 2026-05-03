"""
Regression tests for Phase E: Advanced Tag Management
Tests tag parsing, categorization, and batch operations.
"""

import pytest
from pathlib import Path

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory, initialize_database
from backend.services.tag_service import TagService


@pytest.fixture
def test_project_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    initialize_database(db_path)
    session_factory = create_sqlite_session_factory(db_path)

    with session_factory() as session:
        # Create test project
        project = ProjectRecord(
            name="Test Project",
            caption_mode="tags",
        )
        session.add(project)
        session.flush()

        # Create test images
        img1 = ImageRecord(project_id=project.id, filename="image1.jpg", included=True)
        img2 = ImageRecord(project_id=project.id, filename="image2.jpg", included=True)
        session.add_all([img1, img2])
        session.flush()

        # Create test captions
        cap1 = CaptionRecord(image_id=img1.id, text="red, blue, cat", is_active=True)
        cap2 = CaptionRecord(image_id=img2.id, text="dog, yellow, happy", is_active=True)
        session.add_all([cap1, cap2])
        session.commit()

        project_id = project.id
        img1_id = img1.id
        img2_id = img2.id
        cap1_id = cap1.id
        cap2_id = cap2.id

    yield db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id


def test_parse_tags():
    """Test tag parsing from comma-separated text."""
    text1 = "red, blue, cat"
    tags1 = TagService.parse_tags(text1)
    assert tags1 == ["red", "blue", "cat"]

    text2 = "dog,yellow,happy"  # No spaces
    tags2 = TagService.parse_tags(text2)
    assert tags2 == ["dog", "yellow", "happy"]

    text3 = ""
    tags3 = TagService.parse_tags(text3)
    assert tags3 == []

    text4 = "single"
    tags4 = TagService.parse_tags(text4)
    assert tags4 == ["single"]


def test_tags_to_text():
    """Test conversion of tag list to comma-separated text."""
    tags = ["red", "blue", "cat"]
    text = TagService.tags_to_text(tags)
    assert text == "red, blue, cat"

    empty_tags = []
    empty_text = TagService.tags_to_text(empty_tags)
    assert empty_text == ""


def test_categorize_tag():
    """Test tag categorization using heuristics."""
    # Artist indicators
    assert TagService.categorize_tag("by artist") == "artist"

    # Meta indicators
    assert TagService.categorize_tag("requested_(character)") == "meta"

    # Rating indicators
    assert TagService.categorize_tag("explicit") == "rating"

    # Species indicators
    assert TagService.categorize_tag("furry") == "species"

    # Character (capitalized)
    assert TagService.categorize_tag("Alice") == "character"

    # General (default)
    assert TagService.categorize_tag("red") == "general"


def test_get_all_tags_for_caption(test_project_db):
    """Test retrieving tags with categorization info from a caption."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        tags_info = TagService.get_all_tags_for_caption(cap)

        assert len(tags_info) == 3
        assert all("tag" in tag_info and "category" in tag_info for tag_info in tags_info)
        assert all("color" in tag_info for tag_info in tags_info)


def test_update_caption_tags(test_project_db):
    """Test updating tags in a caption."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()

        new_tags = ["green", "purple", "dog"]
        TagService.update_caption_tags(session, cap, new_tags)
        session.commit()

        # Verify update
        updated_cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        assert updated_cap.text == "green, purple, dog"


def test_add_tags_to_captions(test_project_db):
    """Test adding tags to multiple captions without duplicates."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap1 = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        cap2 = session.query(CaptionRecord).filter(CaptionRecord.id == cap2_id).first()

        captions = [cap1, cap2]
        tags_to_add = ["new_tag", "shiny"]

        updated = TagService.add_tags_to_captions(session, captions, tags_to_add, position="append")
        session.commit()

        assert len(updated) == 2
        cap1_updated = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        assert "new_tag" in cap1_updated.text
        assert "shiny" in cap1_updated.text


def test_add_tags_prepend(test_project_db):
    """Test adding tags at the beginning of a caption."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()

        tags_to_add = ["important"]
        TagService.add_tags_to_captions(session, [cap], tags_to_add, position="prepend")
        session.commit()

        updated_cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        # Should start with "important"
        assert updated_cap.text.startswith("important")


def test_remove_tags_from_captions(test_project_db):
    """Test removing tags from multiple captions."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap1 = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        cap2 = session.query(CaptionRecord).filter(CaptionRecord.id == cap2_id).first()

        captions = [cap1, cap2]
        tags_to_remove = ["red", "dog"]

        updated = TagService.remove_tags_from_captions(session, captions, tags_to_remove)
        session.commit()

        assert len(updated) == 2

        cap1_updated = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        assert "red" not in cap1_updated.text

        cap2_updated = session.query(CaptionRecord).filter(CaptionRecord.id == cap2_id).first()
        assert "dog" not in cap2_updated.text


def test_clear_all_tags(test_project_db):
    """Test clearing all tags from captions."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap1 = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        cap2 = session.query(CaptionRecord).filter(CaptionRecord.id == cap2_id).first()

        captions = [cap1, cap2]
        updated = TagService.clear_all_tags(session, captions)
        session.commit()

        assert len(updated) == 2

        cap1_cleared = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        assert cap1_cleared.text == ""

        cap2_cleared = session.query(CaptionRecord).filter(CaptionRecord.id == cap2_id).first()
        assert cap2_cleared.text == ""


def test_reorder_tags_for_caption(test_project_db):
    """Test reordering tags in a caption."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()

        new_order = ["blue", "cat", "red"]  # Reverse original order
        TagService.reorder_tags_for_caption(session, cap, new_order)
        session.commit()

        updated_cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        tags = TagService.parse_tags(updated_cap.text)
        assert tags == ["blue", "cat", "red"]


def test_get_tag_statistics(test_project_db):
    """Test tag usage statistics calculation."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        stats = TagService.get_tag_statistics(session, project_id)

        assert "total_tags" in stats
        assert "total_occurrences" in stats
        assert "top_tags" in stats
        assert "tag_frequency" in stats

        # Verify counts
        assert stats["total_tags"] == 6  # red, blue, cat, dog, yellow, happy
        assert stats["total_occurrences"] == 6


def test_duplicate_tag_prevention(test_project_db):
    """Test that duplicate tags are not added."""
    db_path, session_factory, project_id, img1_id, img2_id, cap1_id, cap2_id = test_project_db

    with session_factory() as session:
        cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()

        # Original: red, blue, cat
        tags_to_add = ["red", "blue", "new"]

        updated = TagService.add_tags_to_captions(session, [cap], tags_to_add)
        session.commit()

        assert len(updated) == 1

        updated_cap = session.query(CaptionRecord).filter(CaptionRecord.id == cap1_id).first()
        tags = TagService.parse_tags(updated_cap.text)

        # Count occurrences of "red" and "blue"
        red_count = sum(1 for tag in tags if tag.lower() == "red")
        blue_count = sum(1 for tag in tags if tag.lower() == "blue")

        assert red_count == 1
        assert blue_count == 1
        assert "new" in tags
