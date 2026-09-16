"""
Round-trip equality safety net (audit P0-2).

For every saved sample character, build it via ``CharacterBuilder.apply_choices``,
export the resulting ``choices_made``, build a *fresh* ``CharacterBuilder`` from
that exported ``choices_made``, and assert the two ``to_character()`` dicts are
byte-equal under ``json.dumps(..., sort_keys=True)`` after stripping volatile
fields.

This is the mechanical safety net every subsequent refactor in the
2026-05 audit fix plan verifies against. If a fixture fails round-trip
equality here, that is a real defect — do **not** weaken the assertion or
massage the fixture to make it pass.

Discovery is by glob so any new archetype dropped into
``test_characters/`` is automatically covered.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pytest

from modules.character_builder import CharacterBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_CHARACTERS_DIR = PROJECT_ROOT / "test_characters"
EXAMPLE_COMPLETE = PROJECT_ROOT / "data" / "example_complete_character.json"


# ---------------------------------------------------------------------------
# Volatile-field stripper
# ---------------------------------------------------------------------------
#
# A round-trip is allowed to differ on fields that are intrinsically
# non-deterministic (e.g. timestamps, generated UUIDs). Empirically,
# ``CharacterBuilder.to_character()`` does not produce any such fields today —
# no ``datetime``/``uuid``/``time`` call sites exist under ``modules/`` — so
# the stripper is currently a no-op. The hook is kept so future parity tests
# (and any future timestamping in the builder) have one place to extend.
#
# Add to ``_VOLATILE_TOP_LEVEL_KEYS`` ONLY when you can demonstrate the field
# is non-deterministic across two builds from the same ``choices_made``. Never
# strip semantically meaningful fields to silence a failure.

_VOLATILE_TOP_LEVEL_KEYS: Tuple[str, ...] = ()


def strip_volatile(character: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of ``character`` with volatile fields removed.

    Volatile = non-deterministic across two builds from the same input.
    """
    sanitized = deepcopy(character)
    for key in _VOLATILE_TOP_LEVEL_KEYS:
        sanitized.pop(key, None)
    return sanitized


# ---------------------------------------------------------------------------
# Fixture discovery
# ---------------------------------------------------------------------------


def _discover_fixture_paths() -> List[Path]:
    paths: List[Path] = sorted(TEST_CHARACTERS_DIR.glob("*.json"))
    if EXAMPLE_COMPLETE.exists():
        paths.append(EXAMPLE_COMPLETE)
    return paths


def _extract_choices_made(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Pull ``choices_made`` from a saved character file.

    Saved characters under ``test_characters/`` wrap ``choices_made`` at the
    top level. ``data/example_complete_character.json`` is a built-character
    sheet that nests its choices under ``meta_data.choices_made``. Fall back
    to the document itself if neither is present.
    """
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


def _iter_fixtures() -> Iterable[Tuple[str, Path]]:
    for path in _discover_fixture_paths():
        yield (path.relative_to(PROJECT_ROOT).as_posix(), path)


_FIXTURES = list(_iter_fixtures())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fixtures_discovered():
    """Guardrail: glob discovery must find at least the known fixtures."""
    found = {label for label, _ in _FIXTURES}
    assert any(label.startswith("test_characters/") for label in found), (
        f"No fixtures discovered under test_characters/. Found: {found}"
    )
    if EXAMPLE_COMPLETE.exists():
        assert "data/example_complete_character.json" in found, (
            f"data/example_complete_character.json not picked up. Found: {found}"
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "fixture_path",
    [path for _, path in _FIXTURES],
    ids=[label for label, _ in _FIXTURES],
)
def test_character_rebuild_equality(fixture_path: Path):
    """Build → export choices_made → rebuild → assert byte-equal."""
    raw = json.loads(fixture_path.read_text())
    choices = _extract_choices_made(raw)

    first = _build(choices)
    exported_choices = first.get("choices_made")
    assert isinstance(exported_choices, dict), (
        f"to_character() did not produce a choices_made dict for {fixture_path}"
    )

    second = _build(exported_choices)

    s1 = json.dumps(strip_volatile(first), sort_keys=True, default=str)
    s2 = json.dumps(strip_volatile(second), sort_keys=True, default=str)

    if s1 != s2:
        # Produce a compact diff hint to make defect reports actionable.
        diff = _first_diff(
            json.loads(s1), json.loads(s2), path=""
        )
        pytest.fail(
            f"Round-trip mismatch for {fixture_path.relative_to(PROJECT_ROOT)}\n"
            f"First divergence: {diff}"
        )


# ---------------------------------------------------------------------------
# Diff helper (only used on failure to make reports useful)
# ---------------------------------------------------------------------------


def _first_diff(a: Any, b: Any, path: str) -> str:
    if type(a) is not type(b):
        return f"{path or '<root>'}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        keys_a, keys_b = set(a), set(b)
        only_a = sorted(keys_a - keys_b)
        only_b = sorted(keys_b - keys_a)
        if only_a or only_b:
            return f"{path or '<root>'}: keys only_in_first={only_a} only_in_second={only_b}"
        for k in sorted(keys_a):
            if a[k] != b[k]:
                return _first_diff(a[k], b[k], f"{path}.{k}" if path else k)
        return f"{path or '<root>'}: dicts equal (unexpected)"
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path or '<root>'}: list length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return _first_diff(x, y, f"{path}[{i}]")
        return f"{path or '<root>'}: lists equal (unexpected)"
    return f"{path or '<root>'}: {a!r} != {b!r}"
