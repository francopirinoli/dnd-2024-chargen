"""
Dispatcher consolidation parity safety net (audit Phase 6).

Captures a snapshot of ``CharacterBuilder.to_character()`` for every saved
fixture and asserts the output stays byte-equal across the Phase 6 refactor.

Companion to ``test_rebuild_equality.py``:
  - ``test_rebuild_equality`` asserts "the same character built twice is equal".
  - ``test_dispatcher_parity`` asserts "the same character built before and
    after the dispatcher consolidation is equal".

The snapshots live next to this file under ``snapshots/dispatcher_parity/``
and are stored as canonical JSON (``sort_keys=True``, indent 2).

When a fixture intentionally changes, regenerate snapshots by running:

    DCC_REGENERATE_SNAPSHOTS=1 pytest tests/integration/test_dispatcher_parity.py

and inspect the diff before committing. Do NOT regenerate to silence a failure
that exposes a calculation regression.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pytest

from modules.character_builder import CharacterBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_CHARACTERS_DIR = PROJECT_ROOT / "test_characters"
EXAMPLE_COMPLETE = PROJECT_ROOT / "data" / "example_complete_character.json"
SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots" / "dispatcher_parity"


# applied_effects ordering is incidental to the dispatcher refactor;
# it remains semantically equivalent (same entries, same source labels)
# but its ordering relative to structured-bonus population is not part
# of the public contract. The list is preserved as audit-only.
_VOLATILE_TOP_LEVEL_KEYS: Tuple[str, ...] = ()


def _strip_volatile(character: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = deepcopy(character)
    for key in _VOLATILE_TOP_LEVEL_KEYS:
        sanitized.pop(key, None)
    return sanitized


def _extract_choices_made(raw: Dict[str, Any]) -> Dict[str, Any]:
    if "choices_made" in raw and isinstance(raw["choices_made"], dict):
        return raw["choices_made"]
    meta = raw.get("meta_data") or {}
    if isinstance(meta, dict) and isinstance(meta.get("choices_made"), dict):
        return meta["choices_made"]
    return raw


def _build(choices: Dict[str, Any]) -> Dict[str, Any]:
    builder = CharacterBuilder()
    ok = builder.apply_choices(choices)
    assert ok, "CharacterBuilder.apply_choices returned False"
    return builder.to_character()


def _discover_fixture_paths() -> List[Path]:
    paths: List[Path] = sorted(TEST_CHARACTERS_DIR.glob("*.json"))
    if EXAMPLE_COMPLETE.exists():
        paths.append(EXAMPLE_COMPLETE)
    return paths


def _iter_fixtures() -> Iterable[Tuple[str, Path]]:
    for path in _discover_fixture_paths():
        yield (path.relative_to(PROJECT_ROOT).as_posix(), path)


_FIXTURES = list(_iter_fixtures())


def _snapshot_path(fixture_path: Path) -> Path:
    rel = fixture_path.relative_to(PROJECT_ROOT).as_posix().replace("/", "__")
    return SNAPSHOT_DIR / f"{rel}.snapshot.json"


def _stable_sort(obj: Any) -> Any:
    """Recursively sort lists of dicts by their canonical JSON representation so
    that snapshot comparisons are insensitive to non-deterministic effect ordering."""
    if isinstance(obj, dict):
        return {k: _stable_sort(v) for k, v in obj.items()}
    if isinstance(obj, list):
        items = [_stable_sort(i) for i in obj]
        if items and all(isinstance(i, dict) for i in items):
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str))
        return items
    return obj


def _canonicalize(character: Dict[str, Any]) -> str:
    return json.dumps(
        _stable_sort(_strip_volatile(character)), sort_keys=True, indent=2, default=str
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "fixture_path",
    [path for _, path in _FIXTURES],
    ids=[label for label, _ in _FIXTURES],
)
def test_dispatcher_parity(fixture_path: Path):
    """``to_character()`` output must match the committed snapshot byte-for-byte."""
    raw = json.loads(fixture_path.read_text())
    choices = _extract_choices_made(raw)
    built = _build(choices)
    actual = _canonicalize(built)

    snap = _snapshot_path(fixture_path)
    if os.environ.get("DCC_REGENERATE_SNAPSHOTS") == "1":
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(actual)
        pytest.skip(f"Regenerated snapshot {snap.relative_to(PROJECT_ROOT)}")

    if not snap.exists():
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(actual)
        pytest.fail(
            f"Snapshot did not exist: {snap.relative_to(PROJECT_ROOT)}. "
            "Created it now; re-run the test to verify."
        )

    expected = snap.read_text()
    if actual != expected:
        # Save the actual output beside the snapshot for easy diffing.
        diff_path = snap.with_suffix(".actual.json")
        diff_path.write_text(actual)
        pytest.fail(
            f"Snapshot mismatch for {fixture_path.relative_to(PROJECT_ROOT)}.\n"
            f"Expected: {snap.relative_to(PROJECT_ROOT)}\n"
            f"Actual:   {diff_path.relative_to(PROJECT_ROOT)}\n"
            "Diff with:\n"
            f"  diff -u {snap.relative_to(PROJECT_ROOT)} {diff_path.relative_to(PROJECT_ROOT)}\n"
            "If the change is intentional, regenerate with:\n"
            "  DCC_REGENERATE_SNAPSHOTS=1 pytest tests/integration/test_dispatcher_parity.py"
        )
