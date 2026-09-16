"""
Regression test for audit D0-4a — `grant_spell` colon typos.

`Power Word: Heal` / `Power Word: Kill` were the spell names used by the
Bard's level-20 "Words of Creation" feature. The spell definition files are
`power_word_heal.json` / `power_word_kill.json` (no colon), so the lookup
silently fell back to a level=0 placeholder with no real metadata.

After the fix, the colonless names resolve to the real definitions and the
character's `always_prepared` map carries the correct spell level (9th).
"""

from __future__ import annotations

import pytest

from modules.character_builder import CharacterBuilder


@pytest.fixture
def bard20() -> CharacterBuilder:
    builder = CharacterBuilder()
    builder.apply_choices(
        {
            "species": "Human",
            "class": "Bard",
            "level": 20,
            "subclass": "College of Lore",
            "background": "Sage",
            "ability_scores": {
                "Strength": 8,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 12,
                "Wisdom": 10,
                "Charisma": 15,
            },
        }
    )
    return builder


@pytest.mark.parametrize(
    "spell_name,expected_level",
    [
        ("Power Word Heal", 9),
        ("Power Word Kill", 9),
    ],
)
def test_words_of_creation_spell_metadata_resolves(
    bard20: CharacterBuilder, spell_name: str, expected_level: int
) -> None:
    char = bard20.to_character()
    always_prepared = char["spells"]["always_prepared"]
    assert spell_name in always_prepared, (
        f"{spell_name} should be granted by Words of Creation at level 20. "
        f"Present keys: {sorted(always_prepared)}"
    )
    entry = always_prepared[spell_name]
    assert entry["level"] == expected_level, (
        f"Spell metadata for {spell_name} resolved to level {entry['level']} "
        "— this is the placeholder fallback, which means the grant_spell "
        "reference does not match the real spell definition filename. "
        "Check for stray colons in the spell name (audit D0-4a)."
    )
