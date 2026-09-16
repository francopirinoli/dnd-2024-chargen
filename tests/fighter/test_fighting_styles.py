"""Tests for Fighter fighting styles and their effects."""

from modules.character_builder import CharacterBuilder


def test_archery_fighting_style_bonus():
    """Test that Archery fighting style grants +2 to ranged weapon attacks."""
    # Create level 3 Fighter with Archery fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 14,
            "Dexterity": 16,  # +3 modifier
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Archery",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add a longbow to test ranged weapon
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Longbow",
                "properties": {
                    "category": "Martial Ranged",
                    "properties": ["Ammunition (range 150/600)", "Heavy", "Two-Handed"],
                    "damage": "1d8",
                    "damage_type": "Piercing",
                    "proficiency_required": "Martial weapons",  # Must match proficiency name
                },
            },
            {
                "name": "Longsword",
                "properties": {
                    "category": "Martial Melee",
                    "properties": ["Versatile (1d10)"],
                    "damage": "1d8",
                    "damage_type": "Slashing",
                    "proficiency_required": "Martial weapons",  # Must match proficiency name
                },
            },
        ]
    }

    # Get full character data (which calculates attacks with all bonuses)
    char_data = builder.to_character()
    attacks = char_data["attacks"]

    # Find longbow and longsword
    longbow = next(a for a in attacks if a["name"] == "Longbow")
    longsword = next(a for a in attacks if a["name"] == "Longsword")

    # Longbow should have +7 to hit (DEX 3 + Prof 2 + Archery 2)
    assert longbow["attack_bonus"] == 7, f"Expected +7, got +{longbow['attack_bonus']}"

    # Longsword should have +4 to hit (STR 2 + Prof 2, NO Archery bonus)
    assert longsword["attack_bonus"] == 4, (
        f"Expected +4, got +{longsword['attack_bonus']}"
    )


def test_archery_persists_across_serialization():
    """Test that Archery bonus persists when builder is saved/loaded from JSON."""
    # Create Fighter with Archery
    builder = CharacterBuilder()

    choices = {
        "species": "Elf",
        "lineage": "Wood Elf",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 14,
            "Dexterity": 16,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Archery",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add weapons
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Longbow",
                "properties": {
                    "category": "Martial Ranged",
                    "properties": ["Ammunition (range 150/600)", "Heavy", "Two-Handed"],
                    "damage": "1d8",
                    "damage_type": "Piercing",
                    "proficiency_required": "Martial weapons",  # Must match proficiency name
                },
            }
        ]
    }

    # Serialize to JSON
    char_json = builder.to_json()

    # Create new builder and load from JSON
    builder2 = CharacterBuilder()
    builder2.from_json(char_json)

    # Get character data with calculated attacks
    char_data = builder2.to_character()
    attacks = char_data["attacks"]
    longbow = next(a for a in attacks if a["name"] == "Longbow")

    # Should still have +7 (DEX 3 + Prof 2 + Archery 2)
    assert longbow["attack_bonus"] == 7, (
        f"Archery bonus not preserved across serialization: "
        f"expected +7, got +{longbow['attack_bonus']}"
    )


def test_defense_fighting_style():
    """Test that Defense fighting style is tracked in effects (implementation TBD)."""
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Defense",
    }

    builder.apply_choices(choices)

    # Check that Defense effect is tracked
    defense_effects = [
        e for e in builder.applied_effects if e.get("source") == "Defense"
    ]

    assert len(defense_effects) > 0, "Defense fighting style should create an effect"
    assert defense_effects[0]["type"] == "bonus_ac", (
        "Defense effect should be type 'bonus_ac'"
    )


def _build_fighter_with_style(style_name, *, use_normalized_key=False):
    """Helper: build a level 1 Fighter with the given fighting style.

    Args:
        style_name: The fighting style to select.
        use_normalized_key: When True, uses the wizard-style normalized key
            ``"fighting_style"`` instead of the display name ``"Fighting Style"``.
            This exercises the second elif branch in _apply_choice_effects().
    """
    choice_key = "fighting_style" if use_normalized_key else "Fighting Style"
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        choice_key: style_name,
    })
    return builder


def test_blind_fighting_style():
    """Test that Blind Fighting style is recorded as a class feature."""
    builder = _build_fighter_with_style("Blind Fighting")
    character = builder.to_character()

    class_feature_names = [f["name"] for f in character["features"]["class"]]
    assert any("Blind Fighting" in n for n in class_feature_names), (
        "Blind Fighting should appear in class features"
    )


def test_interception_fighting_style():
    """Test that Interception style is recorded as a class feature."""
    builder = _build_fighter_with_style("Interception")
    character = builder.to_character()

    class_feature_names = [f["name"] for f in character["features"]["class"]]
    assert any("Interception" in n for n in class_feature_names), (
        "Interception should appear in class features"
    )


def test_protection_fighting_style():
    """Test that Protection style is recorded as a class feature."""
    builder = _build_fighter_with_style("Protection")
    character = builder.to_character()

    class_feature_names = [f["name"] for f in character["features"]["class"]]
    assert any("Protection" in n for n in class_feature_names), (
        "Protection should appear in class features"
    )


# ---------------------------------------------------------------------------
# Regression tests: wizard-path uses the normalized key "fighting_style"
# (choices.name value) instead of "Fighting Style" (feature display name).
# These guard against the key-matching bug in _apply_choice_effects() where
# the second elif branch (matching by choices.name) previously fell through to
# _load_feat_data() and silently did nothing for external-file choices.
# ---------------------------------------------------------------------------

def test_archery_via_normalized_key():
    """Regression: Archery via normalized key 'fighting_style' applies +2 ranged attack bonus."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 14,
            "Dexterity": 16,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "fighting_style": "Archery",
        "subclass": "Champion",
    })
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Longbow",
                "properties": {
                    "category": "Martial Ranged",
                    "properties": ["Ammunition (range 150/600)", "Heavy", "Two-Handed"],
                    "damage": "1d8",
                    "damage_type": "Piercing",
                    "proficiency_required": "Martial weapons",
                },
            },
            {
                "name": "Longsword",
                "properties": {
                    "category": "Martial Melee",
                    "properties": ["Versatile (1d10)"],
                    "damage": "1d8",
                    "damage_type": "Slashing",
                    "proficiency_required": "Martial weapons",
                },
            },
        ]
    }
    char_data = builder.to_character()
    attacks = char_data["attacks"]

    longbow = next(a for a in attacks if a["name"] == "Longbow")
    longsword = next(a for a in attacks if a["name"] == "Longsword")

    # Longbow: DEX+3 + Prof+2 + Archery+2 = +7
    assert longbow["attack_bonus"] == 7, (
        f"Archery (normalized key): expected +7 ranged attack, got +{longbow['attack_bonus']}"
    )
    # Longsword: STR+2 + Prof+2, no Archery = +4
    assert longsword["attack_bonus"] == 4, (
        f"Archery (normalized key): longsword should be +4, got +{longsword['attack_bonus']}"
    )


def test_defense_via_normalized_key():
    """Regression: Defense via normalized key 'fighting_style' grants +1 AC."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "fighting_style": "Defense",
    })

    defense_effects = [
        e for e in builder.applied_effects if e.get("source") == "Defense"
    ]
    assert len(defense_effects) > 0, (
        "Defense (normalized key): effect should be applied"
    )
    assert defense_effects[0]["type"] == "bonus_ac", (
        "Defense (normalized key): effect should be type 'bonus_ac'"
    )


def test_dueling_via_normalized_key():
    """Regression: Dueling via normalized key 'fighting_style' grants +2 damage."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "fighting_style": "Dueling",
        "subclass": "Champion",
    })
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Longsword",
                "properties": {
                    "category": "Martial Melee",
                    "properties": ["Versatile (1d10)"],
                    "damage": "1d8",
                    "damage_type": "Slashing",
                    "proficiency_required": "Martial weapons",
                },
            },
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }
    weapon_data = builder.calculate_weapon_attacks()
    longsword = next(
        (a for a in weapon_data.get("attacks", []) if a["name"] == "Longsword"), None
    )
    assert longsword is not None, "Longsword attack should exist"
    # 1d8 + STR(+3) + Dueling(+2) = 1d8 + 5
    assert "1d8 + 5" in longsword["damage"], (
        f"Dueling (normalized key): expected '1d8 + 5', got '{longsword['damage']}'"
    )


def test_great_weapon_fighting_via_normalized_key():
    """Regression: GWF via normalized key 'fighting_style' raises average damage."""
    builder_gwf = CharacterBuilder()
    builder_gwf.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 10,
        },
        "fighting_style": "Great Weapon Fighting",
        "equipment_selections": {"class_equipment": "option_a"},
    })

    builder_none = CharacterBuilder()
    builder_none.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 10,
        },
        "fighting_style": "Defense",
        "equipment_selections": {"class_equipment": "option_a"},
    })

    attacks_gwf = builder_gwf.calculate_weapon_attacks().get("attacks", [])
    attacks_none = builder_none.calculate_weapon_attacks().get("attacks", [])

    gs_gwf = next((a for a in attacks_gwf if a["name"] == "Greatsword"), None)
    gs_none = next((a for a in attacks_none if a["name"] == "Greatsword"), None)

    assert gs_gwf is not None and gs_none is not None, "Greatsword should exist"
    assert gs_gwf["avg_damage"] > gs_none["avg_damage"], (
        "GWF (normalized key): should increase average damage vs no GWF"
    )


def test_two_weapon_fighting_via_normalized_key():
    """Regression: Two-Weapon Fighting via normalized key adds ability mod to offhand."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 14,
            "Dexterity": 16,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 10,
        },
        "fighting_style": "Two-Weapon Fighting",
        "equipment_selections": {"class_equipment": "option_b"},
    })

    weapon_data = builder.calculate_weapon_attacks()
    combinations = weapon_data.get("combinations", [])

    assert len(combinations) >= 1, "Should have at least one dual-wield combination"
    offhand_dmg = combinations[0]["offhand"]["damage"]
    assert "+" in offhand_dmg, (
        f"Two-Weapon Fighting (normalized key): offhand should include ability mod, got '{offhand_dmg}'"
    )


def test_unarmed_fighting_via_normalized_key():
    """Regression: Unarmed Fighting via normalized key uses 1d8 die (no weapons equipped)."""
    builder = CharacterBuilder()
    builder.apply_choices({
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "fighting_style": "Unarmed Fighting",
    })

    # No weapons equipped → Unarmed Fighting gives 1d8
    builder.character_data["equipment"] = {
        "weapons": [],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    weapon_data = builder.calculate_weapon_attacks()
    unarmed = next(
        (a for a in weapon_data.get("attacks", []) if a["name"] == "Unarmed Strike"),
        None,
    )
    assert unarmed is not None, "Unarmed Strike attack should exist"
    assert "1d8" in unarmed["damage"], (
        f"Unarmed Fighting (normalized key): expected '1d8' die with no weapons, got '{unarmed['damage']}'"
    )
