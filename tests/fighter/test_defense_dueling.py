"""Tests for Defense and Dueling fighting styles."""

from modules.character_builder import CharacterBuilder


def test_defense_fighting_style_with_armor():
    """Test that Defense fighting style grants +1 AC when wearing armor."""
    # Create level 3 Fighter with Defense fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,  # +2 modifier
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Defense",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add armor to test AC bonus
    builder.character_data["equipment"] = {
        "weapons": [],
        "armor": [
            {
                "name": "Chain Mail",
                "properties": {
                    "category": "Heavy Armor",
                    "ac_base": 16,
                    "proficiency_required": "Heavy armor",
                },
            },
        ],
        "items": [],
        "gold": 0,
    }

    # Calculate AC options
    ac_options = builder.calculate_ac_options()

    # Find Chain Mail AC option
    chain_mail_ac = next(
        (opt for opt in ac_options if opt.get("equipped_armor") == "Chain Mail"),
        None,
    )

    assert chain_mail_ac is not None, "Chain Mail AC option should exist"
    # Base 16 + Defense +1 = 17
    assert chain_mail_ac["ac"] == 17, (
        f"Expected AC 17 (16 base + 1 Defense), got {chain_mail_ac['ac']}"
    )
    assert "Defense (+1)" in chain_mail_ac["formula"], (
        f"Expected Defense bonus in formula, got {chain_mail_ac['formula']}"
    )
    # Check that Defense is noted
    assert any("Defense" in note for note in chain_mail_ac.get("notes", [])), (
        "Defense bonus should be noted"
    )


def test_defense_without_armor():
    """Test that Defense fighting style doesn't apply when not wearing armor."""
    # Create level 3 Fighter with Defense fighting style but no armor
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,  # +2 modifier
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Defense",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # No equipment (unarmored)
    builder.character_data["equipment"] = {
        "weapons": [],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    # Calculate AC options
    ac_options = builder.calculate_ac_options()

    # Should only have unarmored AC option: 10 + DEX (2) = 12
    assert len(ac_options) == 1, "Should only have unarmored AC option"
    assert ac_options[0]["ac"] == 12, (
        f"Expected unarmored AC 12, got {ac_options[0]['ac']}"
    )
    assert ac_options[0]["equipped_armor"] is None, "Should be unarmored"

    # Defense should NOT apply to unarmored AC
    assert not any("Defense" in note for note in ac_options[0].get("notes", [])), (
        "Defense should not apply to unarmored AC"
    )


def test_dueling_one_handed_melee():
    """Test that Dueling grants +2 damage with one-handed melee weapon."""
    # Create level 3 Fighter with Dueling fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,  # +3 modifier
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Dueling",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add a single one-handed melee weapon
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

    # Calculate weapon attacks
    weapon_data = builder.calculate_weapon_attacks()
    attacks = weapon_data.get("attacks", [])

    # Filter out unarmed strike
    weapon_attacks = [a for a in attacks if a["name"] != "Unarmed Strike"]
    assert len(weapon_attacks) == 1, "Should have 1 weapon attack (plus unarmed)"
    longsword = weapon_attacks[0]

    # Check damage: 1d8 + STR (3) + Dueling (2) = 1d8 + 5
    assert "1d8 + 5" in longsword["damage"], (
        f"Expected '1d8 + 5' damage, got '{longsword['damage']}'"
    )

    # Check that Dueling is noted
    assert any("Dueling" in note for note in longsword.get("damage_notes", [])), (
        "Dueling bonus should be noted"
    )

    # Check average damage calculation includes the bonus
    # 1d8 avg = 4.5, +3 STR, +2 Dueling = 9.5
    assert longsword["avg_damage"] == 9.5, (
        f"Expected average damage 9.5, got {longsword['avg_damage']}"
    )


def test_dueling_doesnt_apply_with_two_weapons():
    """Test that Dueling shows normal damage but also dual-wield damage without Dueling."""
    # Create level 3 Fighter with Dueling fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,  # +3 modifier
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Dueling",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add TWO weapons (dual wielding)
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Shortsword",
                "properties": {
                    "category": "Martial Melee",
                    "properties": ["Light", "Finesse"],
                    "damage": "1d6",
                    "damage_type": "Piercing",
                    "proficiency_required": "Martial weapons",
                },
            },
            {
                "name": "Dagger",
                "properties": {
                    "category": "Simple Melee",
                    "properties": ["Light", "Finesse", "Thrown (range 20/60)"],
                    "damage": "1d4",
                    "damage_type": "Piercing",
                    "proficiency_required": "Simple weapons",
                },
            },
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    # Calculate weapon attacks
    weapon_data = builder.calculate_weapon_attacks()
    attacks = weapon_data.get("attacks", [])
    combinations = weapon_data.get("combinations", [])

    # Filter out unarmed strike
    weapon_attacks = [a for a in attacks if a["name"] != "Unarmed Strike"]
    assert len(weapon_attacks) == 2, (
        "Should have 2 individual weapon attacks (plus unarmed)"
    )
    assert len(combinations) == 1, "Should have 1 combination (Shortsword & Dagger)"

    shortsword = next(atk for atk in weapon_attacks if atk["name"] == "Shortsword")

    # Normal damage INCLUDES Dueling (assuming used alone)
    assert "1d6 + 5" in shortsword["damage"], (
        f"Expected '1d6 + 5' normal damage (with Dueling), got '{shortsword['damage']}'"
    )
    assert any("Dueling" in note for note in shortsword.get("damage_notes", [])), (
        "Dueling should be noted in normal damage"
    )

    # Check combination card
    combo = combinations[0]
    assert "Shortsword" in combo["name"] and "Dagger" in combo["name"], (
        f"Expected combination with both weapons, got '{combo['name']}'"
    )

    # Mainhand in combination: no Dueling bonus
    if "Shortsword" in combo["mainhand"]["name"]:
        assert "1d6 + 3" in combo["mainhand"]["damage"], (
            f"Expected combo mainhand '1d6 + 3' (no Dueling), got '{combo['mainhand']['damage']}'"
        )

    # Offhand in combination: dice only
    if "Dagger" in combo["offhand"]["name"]:
        assert combo["offhand"]["damage"] == "1d4", (
            f"Expected combo offhand '1d4', got '{combo['offhand']['damage']}'"
        )

    # Should have note about Dueling not applying
    assert any("Dueling" in note for note in combo.get("notes", [])), (
        "Combination should note that Dueling doesn't apply"
    )


def test_dueling_doesnt_apply_to_two_handed():
    """Test that Dueling doesn't apply to two-handed weapons."""
    # Create level 3 Fighter with Dueling fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,  # +3 modifier
            "Dexterity": 14,
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Dueling",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add a two-handed weapon
    builder.character_data["equipment"] = {
        "weapons": [
            {
                "name": "Greatsword",
                "properties": {
                    "category": "Martial Melee",
                    "properties": ["Heavy", "Two-Handed"],
                    "damage": "2d6",
                    "damage_type": "Slashing",
                    "proficiency_required": "Martial weapons",
                },
            },
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    # Calculate weapon attacks
    weapon_data = builder.calculate_weapon_attacks()
    attacks = weapon_data.get("attacks", [])

    # Filter out unarmed strike
    weapon_attacks = [a for a in attacks if a["name"] != "Unarmed Strike"]
    assert len(weapon_attacks) == 1, "Should have 1 weapon attack (plus unarmed)"
    greatsword = weapon_attacks[0]

    # Check damage: 2d6 + STR (3), NO Dueling
    assert "2d6 + 3" in greatsword["damage"], (
        f"Expected '2d6 + 3' damage (no Dueling), got '{greatsword['damage']}'"
    )

    # Check that Dueling is NOT noted
    assert not any("Dueling" in note for note in greatsword.get("damage_notes", [])), (
        "Dueling should not apply to two-handed weapons"
    )


def test_dueling_doesnt_apply_to_ranged():
    """Test that Dueling doesn't apply to ranged weapons."""
    # Create level 3 Fighter with Dueling fighting style
    builder = CharacterBuilder()

    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier",
        "ability_scores": {
            "Strength": 16,
            "Dexterity": 14,  # +2 modifier
            "Constitution": 14,
            "Intelligence": 10,
            "Wisdom": 12,
            "Charisma": 8,
        },
        "Fighting Style": "Dueling",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add a ranged weapon
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
        ],
        "armor": [],
        "items": [],
        "gold": 0,
    }

    # Calculate weapon attacks
    weapon_data = builder.calculate_weapon_attacks()
    attacks = weapon_data.get("attacks", [])

    # Filter out unarmed strike
    weapon_attacks = [a for a in attacks if a["name"] != "Unarmed Strike"]
    assert len(weapon_attacks) == 1, "Should have 1 weapon attack (plus unarmed)"
    longbow = weapon_attacks[0]

    # Check damage: 1d8 + DEX (2), NO Dueling
    assert "1d8 + 2" in longbow["damage"], (
        f"Expected '1d8 + 2' damage (no Dueling), got '{longbow['damage']}'"
    )

    # Check that Dueling is NOT noted
    assert not any("Dueling" in note for note in longbow.get("damage_notes", [])), (
        "Dueling should not apply to ranged weapons"
    )


def test_defense_serialization():
    """Test that Defense fighting style persists across serialization."""
    # Create character with Defense
    builder = CharacterBuilder()

    choices = {
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
        "Fighting Style": "Defense",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add armor
    builder.character_data["equipment"] = {
        "weapons": [],
        "armor": [
            {
                "name": "Chain Mail",
                "properties": {
                    "category": "Heavy Armor",
                    "ac_base": 16,
                    "proficiency_required": "Heavy armor",
                },
            },
        ],
        "items": [],
        "gold": 0,
    }

    # Serialize to JSON
    json_data = builder.to_json()

    # Create new builder and load from JSON
    new_builder = CharacterBuilder()
    new_builder.from_json(json_data)

    # Check that Defense is still applied
    ac_options = new_builder.calculate_ac_options()
    chain_mail_ac = next(
        (opt for opt in ac_options if opt.get("equipped_armor") == "Chain Mail"),
        None,
    )

    assert chain_mail_ac is not None, (
        "Chain Mail AC option should exist after deserialization"
    )
    assert chain_mail_ac["ac"] == 17, (
        f"Expected AC 17 after deserialization, got {chain_mail_ac['ac']}"
    )
    assert any("Defense" in note for note in chain_mail_ac.get("notes", [])), (
        "Defense bonus should be noted after deserialization"
    )


def test_dueling_serialization():
    """Test that Dueling fighting style persists across serialization."""
    # Create character with Dueling
    builder = CharacterBuilder()

    choices = {
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
        "Fighting Style": "Dueling",
        "subclass": "Champion",
    }

    builder.apply_choices(choices)

    # Add weapon
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

    # Serialize to JSON
    json_data = builder.to_json()

    # Create new builder and load from JSON
    new_builder = CharacterBuilder()
    new_builder.from_json(json_data)

    # Check that Dueling is still applied
    weapon_data = new_builder.calculate_weapon_attacks()
    attacks = weapon_data.get("attacks", [])
    longsword = attacks[0]

    assert "1d8 + 5" in longsword["damage"], (
        f"Expected '1d8 + 5' damage after deserialization, got '{longsword['damage']}'"
    )
    assert any("Dueling" in note for note in longsword.get("damage_notes", [])), (
        "Dueling bonus should be noted after deserialization"
    )
