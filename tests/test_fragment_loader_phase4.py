from __future__ import annotations

import re
from pathlib import Path

FRAGMENT_ATTR_PATTERN = re.compile(r'data-fragment="([^"]+)"')
MAX_PASSES_PATTERN = re.compile(r"const maxPasses = (\d+);")
MAX_PASSES_WARNING = "Fragment loader exceeded maximum passes; check for cyclic fragment placeholders."


def _frontend_root() -> Path:
    return Path(__file__).resolve().parent.parent / "frontend"


def _load_loader_max_passes(frontend_root: Path) -> int:
    loader_text = (frontend_root / "js" / "core" / "fragments.js").read_text(encoding="utf-8")
    match = MAX_PASSES_PATTERN.search(loader_text)
    assert match is not None, "Expected maxPasses constant in fragment loader"
    return int(match.group(1))


def _load_loader_text(frontend_root: Path) -> str:
    return (frontend_root / "js" / "core" / "fragments.js").read_text(encoding="utf-8")


def _simulate_unresolved(children: dict[str, set[str]], roots: set[str], passes: int) -> set[str]:
    unresolved = set(roots)
    for _ in range(passes):
        if not unresolved:
            break
        next_unresolved = set()
        for name in unresolved:
            next_unresolved.update(children.get(name, set()))
        unresolved = next_unresolved
    return unresolved


def _collect_fragment_children(frontend_root: Path) -> dict[str, set[str]]:
    fragments_root = frontend_root / "fragments"
    children: dict[str, set[str]] = {}

    for fragment_file in sorted(fragments_root.rglob("*.html")):
        name = fragment_file.relative_to(fragments_root).as_posix().removesuffix(".html")
        html = fragment_file.read_text(encoding="utf-8")
        children[name] = set(FRAGMENT_ATTR_PATTERN.findall(html))

    return children


def test_nested_fragment_placeholders_resolve_within_loader_max_passes() -> None:
    """Nested fragment placeholders should resolve under bounded multi-pass loading."""
    frontend_root = _frontend_root()
    index_html = (frontend_root / "index.html").read_text(encoding="utf-8")

    root_placeholders = set(FRAGMENT_ATTR_PATTERN.findall(index_html))
    assert root_placeholders, "Expected root fragment placeholders in frontend/index.html"

    children = _collect_fragment_children(frontend_root)
    missing_root = sorted(root_placeholders - set(children.keys()))
    assert not missing_root, f"Missing fragment files for root placeholders: {missing_root}"

    one_pass_remaining = set()
    for name in root_placeholders:
        one_pass_remaining.update(children.get(name, set()))

    # Ensure this regression test actually exercises nested resolution (pass > 1).
    assert one_pass_remaining, "Expected nested placeholders to remain after one pass"

    max_passes = _load_loader_max_passes(frontend_root)
    unresolved = set(root_placeholders)

    for _ in range(max_passes):
        if not unresolved:
            break

        missing_current = sorted(unresolved - set(children.keys()))
        assert not missing_current, f"Missing fragment files for nested placeholders: {missing_current}"

        next_unresolved = set()
        for name in unresolved:
            next_unresolved.update(children[name])
        unresolved = next_unresolved

    assert not unresolved, (
        "Nested fragment placeholders did not resolve within loader max passes; "
        f"remaining: {sorted(unresolved)}"
    )


def test_loader_max_pass_saturation_guardrail_warns_on_overflow_topology() -> None:
    """A synthetic over-deep fragment chain should still be unresolved after maxPasses."""
    frontend_root = _frontend_root()
    max_passes = _load_loader_max_passes(frontend_root)
    loader_text = _load_loader_text(frontend_root)

    assert MAX_PASSES_WARNING in loader_text

    # Build a chain that requires max_passes + 1 passes to fully resolve.
    children: dict[str, set[str]] = {}
    for i in range(max_passes + 1):
        current = f"node_{i}"
        nxt = f"node_{i + 1}"
        children[current] = {nxt}
    children[f"node_{max_passes + 1}"] = set()

    unresolved = _simulate_unresolved(children, {"node_0"}, max_passes)
    assert unresolved, "Expected unresolved placeholders when resolution depth exceeds maxPasses"
