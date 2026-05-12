from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NativePickerResult:
    available: bool
    selected_path: str | None
    reason: str | None = None
    backend: str | None = None


def _has_gui_session() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    # On macOS/Windows, assume GUI if process is running locally.
    return True


def _normalize_start_path(start_path: str | None) -> Path | None:
    if not start_path:
        return None
    try:
        candidate = Path(start_path).expanduser().resolve()
        if candidate.exists():
            return candidate
        for parent in candidate.parents:
            if parent.exists():
                return parent
    except Exception:
        return None
    return None


def _run_picker_command(args: list[str]) -> str | None:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    selected = completed.stdout.strip()
    if not selected:
        return None
    return str(Path(selected).expanduser().resolve())


def _pick_with_zenity(*, kind: str, title: str, start_path: Path | None) -> str | None:
    command = ["zenity", "--file-selection", "--title", title]
    if kind == "directory":
        command.append("--directory")
    elif kind == "db_file":
        command.extend(["--file-filter", "SQLite DB files | *.db *.sqlite *.sqlite3"])

    if start_path is not None:
        filename_arg = str(start_path)
        if start_path.is_dir():
            filename_arg = f"{filename_arg}/"
        command.extend(["--filename", filename_arg])

    return _run_picker_command(command)


def _pick_with_kdialog(*, kind: str, title: str, start_path: Path | None) -> str | None:
    if kind == "directory":
        command = ["kdialog", "--getexistingdirectory"]
        if start_path is not None:
            command.append(str(start_path if start_path.is_dir() else start_path.parent))
        command.append("--title")
        command.append(title)
        return _run_picker_command(command)

    file_filter = "*"
    if kind == "db_file":
        file_filter = "*.db *.sqlite *.sqlite3"

    command = ["kdialog", "--getopenfilename"]
    if start_path is not None:
        command.append(str(start_path if start_path.is_dir() else start_path.parent))
    else:
        command.append(str(Path.home()))
    command.append(file_filter)
    command.append("--title")
    command.append(title)
    return _run_picker_command(command)


def _pick_with_tkinter(*, kind: str, title: str, start_path: Path | None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    initial_dir = str(Path.home())
    initial_file = ""
    if start_path is not None:
        if start_path.is_dir():
            initial_dir = str(start_path)
        else:
            initial_dir = str(start_path.parent)
            initial_file = start_path.name

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    try:
        if kind == "directory":
            selected = filedialog.askdirectory(title=title, initialdir=initial_dir)
        else:
            filetypes: list[tuple[str, str]] = [("All files", "*")]
            if kind == "db_file":
                filetypes = [
                    ("SQLite DB files", "*.db *.sqlite *.sqlite3"),
                    ("All files", "*"),
                ]
            selected = filedialog.askopenfilename(
                title=title,
                initialdir=initial_dir,
                initialfile=initial_file,
                filetypes=filetypes,
            )
    finally:
        root.destroy()

    if not selected:
        return None
    return str(Path(selected).expanduser().resolve())


def open_native_path_picker(*, kind: str, title: str, start_path: str | None = None) -> NativePickerResult:
    normalized_kind = kind.strip().lower()
    if normalized_kind not in {"directory", "file", "db_file"}:
        return NativePickerResult(available=False, selected_path=None, reason=f"Unsupported picker kind: {kind}")

    if not _has_gui_session():
        return NativePickerResult(
            available=False,
            selected_path=None,
            reason="No GUI session detected for native file dialogs.",
        )

    normalized_title = title.strip() or "Select a path"
    normalized_start = _normalize_start_path(start_path)

    if sys.platform.startswith("linux"):
        if shutil.which("zenity"):
            selected = _pick_with_zenity(kind=normalized_kind, title=normalized_title, start_path=normalized_start)
            return NativePickerResult(available=True, selected_path=selected, backend="zenity")
        if shutil.which("kdialog"):
            selected = _pick_with_kdialog(kind=normalized_kind, title=normalized_title, start_path=normalized_start)
            return NativePickerResult(available=True, selected_path=selected, backend="kdialog")
        if os.environ.get("DESCRIBE_IT_ENABLE_TKINTER_PICKER", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return NativePickerResult(
                available=False,
                selected_path=None,
                reason="No Linux native picker backend found (install zenity or kdialog).",
            )

    selected = _pick_with_tkinter(kind=normalized_kind, title=normalized_title, start_path=normalized_start)
    if selected is not None:
        return NativePickerResult(available=True, selected_path=selected, backend="tkinter")

    return NativePickerResult(
        available=False,
        selected_path=None,
        reason="No supported native file picker backend is available.",
    )
