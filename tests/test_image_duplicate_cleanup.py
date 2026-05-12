from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db.models import CaptionRecord, ImageRecord, ProjectRecord
from backend.db.session import create_sqlite_session_factory
from backend.main import app

client = TestClient(app)


def _create_duplicate_project(tmp_path: Path) -> tuple[str, dict[str, int]]:
    project_path = str(tmp_path / 'duplicate_cleanup.db')
    create_resp = client.post(
        '/api/projects/create',
        json={"path": project_path, "name": "Duplicate Cleanup", "description": "", "caption_mode": "description"},
    )
    assert create_resp.status_code == 200, create_resp.text

    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        project = session.scalar(select(ProjectRecord).limit(1))
        assert project is not None

        kept = ImageRecord(
            project_id=project.id,
            filename='kept.png',
            original_blob=b'same-bytes',
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        duplicate = ImageRecord(
            project_id=project.id,
            filename='duplicate.png',
            original_blob=b'same-bytes',
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        unique = ImageRecord(
            project_id=project.id,
            filename='unique.png',
            original_blob=b'unique-bytes',
            working_blob=None,
            width=32,
            height=32,
            included=True,
        )
        session.add_all([kept, duplicate, unique])
        session.flush()

        session.add_all(
            [
                CaptionRecord(image_id=kept.id, text='shared caption', is_active=True, source='manual'),
                CaptionRecord(image_id=duplicate.id, text='shared caption', is_active=True, source='manual'),
                CaptionRecord(image_id=duplicate.id, text='new caption', is_active=False, source='manual'),
                CaptionRecord(image_id=unique.id, text='unique image caption', is_active=True, source='manual'),
            ]
        )
        session.commit()

        return project_path, {'kept_id': kept.id, 'duplicate_id': duplicate.id, 'unique_id': unique.id}


def test_duplicate_preview_reports_exact_hash_groups(tmp_path: Path) -> None:
    project_path, ids = _create_duplicate_project(tmp_path)

    response = client.get('/api/images/duplicates', params={'project_path': project_path})
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload['duplicate_group_count'] == 1
    assert payload['removable_image_count'] == 1
    assert len(payload['groups']) == 1
    group = payload['groups'][0]
    assert group['kept_image']['id'] == ids['kept_id']
    assert group['duplicate_images'][0]['id'] == ids['duplicate_id']


def test_duplicate_cleanup_soft_deletes_duplicates_and_merges_unique_captions(tmp_path: Path) -> None:
    project_path, ids = _create_duplicate_project(tmp_path)

    response = client.post(
        '/api/images/duplicates/cleanup',
        json={'project_path': project_path, 'mode': 'soft'},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['duplicate_group_count'] == 1
    assert payload['removed_image_count'] == 1
    assert payload['removed_image_ids'] == [ids['duplicate_id']]
    assert payload['captions_merged'] == 1
    assert payload['captions_skipped'] == 1

    list_resp = client.get('/api/images/list', params={'project_path': project_path})
    assert list_resp.status_code == 200, list_resp.text
    remaining_ids = [image['id'] for image in list_resp.json()['images']]
    assert ids['duplicate_id'] not in remaining_ids
    assert ids['kept_id'] in remaining_ids
    assert ids['unique_id'] in remaining_ids

    detail_resp = client.get(f"/api/images/{ids['kept_id']}", params={'project_path': project_path})
    assert detail_resp.status_code == 200, detail_resp.text
    captions = detail_resp.json()['image']['captions']
    caption_texts = [caption['text'] for caption in captions]
    assert caption_texts.count('shared caption') == 1
    assert 'new caption' in caption_texts
    active_captions = [caption for caption in captions if caption['is_active']]
    assert len(active_captions) == 1
    assert active_captions[0]['text'] == 'shared caption'


def test_duplicate_cleanup_hard_requires_confirmation(tmp_path: Path) -> None:
    project_path, _ = _create_duplicate_project(tmp_path)

    response = client.post(
        '/api/images/duplicates/cleanup',
        json={'project_path': project_path, 'mode': 'hard', 'confirm_hard_delete': False},
    )
    assert response.status_code == 400
    assert 'confirm_hard_delete' in response.text


def test_duplicate_cleanup_hard_deletes_duplicate_rows(tmp_path: Path) -> None:
    project_path, ids = _create_duplicate_project(tmp_path)

    response = client.post(
        '/api/images/duplicates/cleanup',
        json={'project_path': project_path, 'mode': 'hard', 'confirm_hard_delete': True},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['mode'] == 'hard'
    assert payload['removed_image_count'] == 1
    assert payload['removed_image_ids'] == [ids['duplicate_id']]

    session_factory = create_sqlite_session_factory(project_path)
    with session_factory() as session:
        duplicate_row = session.scalar(select(ImageRecord).where(ImageRecord.id == ids['duplicate_id']))
        assert duplicate_row is None