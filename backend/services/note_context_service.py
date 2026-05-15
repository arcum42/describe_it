from __future__ import annotations

from backend.services.note_service import list_notes
from backend.services.global_note_service import list_global_notes


def _render_note_block(*, scope_label: str, title: str | None, tags: str | None, content: str) -> str:
    header = f"[{scope_label}: {title}]" if title else f"[{scope_label}]"
    if tags:
        header += f" (tags: {tags})"
    return f"{header}\n{content}"


def _select_notes(*, notes: list, selected_ids: list[int] | None) -> list:
    if selected_ids:
        id_set = set(selected_ids)
        return [note for note in notes if note.id in id_set]
    return [note for note in notes if not note.is_archived]


def _load_project_notes(*, project_path: str, log_entries: list[str]) -> list:
    try:
        return list_notes(project_path=project_path, include_archived=True)
    except Exception as exc:  # noqa: BLE001
        log_entries.append(f"Failed to load project notes: {exc}")
        return []


def _load_global_notes(*, log_entries: list[str]) -> list:
    try:
        return list_global_notes(include_archived=True)
    except Exception as exc:  # noqa: BLE001
        log_entries.append(f"Failed to load global notes: {exc}")
        return []


def _append_context_block(
    *,
    injected_parts: list[str],
    log_entries: list[str],
    section_title: str,
    scope_label: str,
    notes: list,
    selection_label: str,
) -> None:
    if not notes:
        return
    blocks = [
        _render_note_block(
            scope_label=scope_label,
            title=note.title,
            tags=note.tags,
            content=note.content,
        )
        for note in notes
    ]
    injected_parts.append(f"--- {section_title} ---\n" + "\n\n".join(blocks))
    log_entries.append(f"Included {len(notes)} {selection_label} note(s) as context")


def build_notes_context_parts(
    *,
    project_path: str | None = None,
    include_project_notes: bool = False,
    project_note_ids: list[int] | None = None,
    include_global_notes: bool = False,
    global_note_ids: list[int] | None = None,
) -> tuple[list[str], list[str]]:
    """Build injected context parts and log entries for selected notes.

    Args:
        project_path: Required when using project notes.
        include_project_notes: Include all non-archived project notes.
        project_note_ids: Specific project note IDs to include (overrides include_project_notes
            when provided; includes archived notes if explicitly listed).
        include_global_notes: Include all non-archived global notes.
        global_note_ids: Specific global note IDs to include.

    Returns:
        Tuple of (injected_parts, log_entries).
    """
    injected_parts: list[str] = []
    log_entries: list[str] = []

    if project_path and (include_project_notes or project_note_ids):
        all_notes = _load_project_notes(project_path=project_path, log_entries=log_entries)
        selected_project_notes = _select_notes(notes=all_notes, selected_ids=project_note_ids)
        _append_context_block(
            injected_parts=injected_parts,
            log_entries=log_entries,
            section_title="Project Notes Context",
            scope_label="Project Note",
            notes=selected_project_notes,
            selection_label="project",
        )

    if include_global_notes or global_note_ids:
        all_global_notes = _load_global_notes(log_entries=log_entries)
        selected_global_notes = _select_notes(notes=all_global_notes, selected_ids=global_note_ids)
        _append_context_block(
            injected_parts=injected_parts,
            log_entries=log_entries,
            section_title="Global Notes Context",
            scope_label="Global Note",
            notes=selected_global_notes,
            selection_label="global",
        )

    return injected_parts, log_entries
