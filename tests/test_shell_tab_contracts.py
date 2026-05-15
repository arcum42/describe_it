from __future__ import annotations

from pathlib import Path


def _read(rel_path: str) -> str:
    return (Path(__file__).resolve().parent.parent / rel_path).read_text(encoding="utf-8")


def test_index_loads_ui_shell_feature_before_app() -> None:
    index_html = _read("frontend/index.html")

    ui_shell_tag = '<script defer src="/static/js/features/ui-shell.js?v=20260503a"></script>'
    app_tag = '<script defer src="/static/app.js?v=20260503d"></script>'

    assert ui_shell_tag in index_html
    assert app_tag in index_html
    assert index_html.find(ui_shell_tag) < index_html.find(app_tag)


def test_content_host_renders_settings_tab_header_before_panels() -> None:
    content_host = _read("frontend/fragments/shell/content_host.html")

    header_marker = 'data-fragment="settings/tab_header"'
    presets_marker = 'data-fragment="settings/presets"'
    general_marker = 'data-fragment="settings/general"'
    imageboards_marker = 'data-fragment="settings/imageboards"'

    assert header_marker in content_host
    assert presets_marker in content_host
    assert general_marker in content_host
    assert imageboards_marker in content_host

    header_index = content_host.find(header_marker)
    assert header_index < content_host.find(presets_marker)
    assert header_index < content_host.find(general_marker)
    assert header_index < content_host.find(imageboards_marker)
