from __future__ import annotations

from pathlib import Path


def _editor_fragment_text() -> str:
    fragment_path = Path(__file__).resolve().parent.parent / "frontend" / "fragments" / "workspace" / "editor.html"
    return fragment_path.read_text(encoding="utf-8")


def test_tag_mode_editor_exposes_both_caption_and_tag_sections() -> None:
    editor_html = _editor_fragment_text()

    assert 'template x-if="editorView.subTab === \'caption\'"' in editor_html
    assert 'x-show="editorView.subTab === \'caption\'" class="order-1 rounded-2xl border border-stone-800 bg-stone-950/70 p-4"' in editor_html
    assert 'template x-if="isTagMode() && editorView.subTab === \'caption\'"' in editor_html
    assert 'label class="block text-sm font-medium text-stone-300">Active Tags</label>' in editor_html
    assert 'label class="block text-sm font-medium text-stone-300">Active Caption</label>' in editor_html

    assert '!isTagMode() && editorView.subTab === \'caption\'' not in editor_html
    assert 'editorView.subTab === \'caption\' && !isTagMode()' not in editor_html