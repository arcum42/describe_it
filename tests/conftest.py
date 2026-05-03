"""
Shared pytest configuration.

Redirects the app state directory (recent_projects.json, app_state.db) to a
temporary folder for the duration of the test session so that running tests
does not pollute .describe_it/ with fake project entries.

pytest_configure runs before any test modules are imported, which ensures that
module-level singletons (e.g. BatchService) pick up the temp state dir from
the start rather than after their __init__ has already run.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def _cleanup_enabled() -> bool:
    """Return True when session-end artifact cleanup should run."""
    raw = os.environ.get("DESCRIBE_IT_TEST_CLEANUP", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _cleanup_test_artifacts() -> None:
    """Remove known repo-root artifacts created by test runs."""
    repo_root = Path(__file__).resolve().parent.parent

    # Explicit test-only paths plus a scoped prefix for root-level temp dirs.
    explicit_paths = [
        repo_root / ".pytest_cache",
        repo_root / "tmp_batch_input",
    ]
    for path in explicit_paths:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)

    for path in repo_root.glob(".tmp_*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)


def pytest_configure(config: object) -> None:
    """Set DESCRIBE_IT_STATE_DIR to a fresh temp dir before any imports happen."""
    state_dir = tempfile.mkdtemp(prefix="describe_it_test_state_")
    os.environ["DESCRIBE_IT_STATE_DIR"] = state_dir
    # Store for cleanup in pytest_unconfigure
    config._describe_it_test_state_dir = state_dir  # type: ignore[attr-defined]


def pytest_unconfigure(config: object) -> None:
    """Remove the temp state dir and clean up the env var."""
    state_dir = getattr(config, "_describe_it_test_state_dir", None)
    if state_dir:
        shutil.rmtree(state_dir, ignore_errors=True)
    if _cleanup_enabled():
        _cleanup_test_artifacts()
    os.environ.pop("DESCRIBE_IT_STATE_DIR", None)
