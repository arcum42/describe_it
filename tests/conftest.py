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
    os.environ.pop("DESCRIBE_IT_STATE_DIR", None)
