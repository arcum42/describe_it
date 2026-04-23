from __future__ import annotations

from backend.services.note_service import list_notes
from backend.services.global_note_service import list_global_notes


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

    # --- Project notes ---
    if project_path and (include_project_notes or project_note_ids):
        try:
            all_notes = list_notes(project_path=project_path, include_archived=True)
        except Exception as exc:  # noqa: BLE001
            log_entries.append(f"Failed to load project notes: {exc}")
            all_notes = []

        if project_note_ids:
            id_set = set(project_note_ids)
            selected = [n for n in all_notes if n.id in id_set]
        else:
            selected = [n for n in all_notes if not n.is_archived]

        if selected:
            blocks: list[str] = []
            for note in selected:
                header = f"[Project Note: {note.title}]" if note.title else "[Project Note]"
                if note.tags:
                    header += f" (tags: {note.tags})"
                blocks.append(f"{header}\n{note.content}")
            injected_parts.append("--- Project Notes Context ---\n" + "\n\n".join(blocks))
            log_entries.append(f"Included {len(selected)} project note(s) as context")

    # --- Global notes ---
    if include_global_notes or global_note_ids:
        try:
            all_global = list_global_notes(include_archived=True)
        except Exception as exc:  # noqa: BLE001
            log_entries.append(f"Failed to load global notes: {exc}")
            all_global = []

        if global_note_ids:
            id_set = set(global_note_ids)
            selected_global = [n for n in all_global if n.id in id_set]
        else:
            selected_global = [n for n in all_global if not n.is_archived]

        if selected_global:
            blocks = []
            for note in selected_global:
                header = f"[Global Note: {note.title}]" if note.title else "[Global Note]"
                if note.tags:
                    header += f" (tags: {note.tags})"
                blocks.append(f"{header}\n{note.content}")
            injected_parts.append("--- Global Notes Context ---\n" + "\n\n".join(blocks))
            log_entries.append(f"Included {len(selected_global)} global note(s) as context")

    return injected_parts, log_entries
