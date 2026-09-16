"""
Unit and integration tests for equipment catalog, inventory management,
equipping / unequipping items, and stat calculations (AC, weapon attacks).
"""

import pytest
from modules.character_builder import CharacterBuilder


def test_catalog_equipment_endpoint(client):
    """Ensure GET /api/v1/catalog/equipment returns unified items catalog."""
    resp = client.get("/api/v1/catalog/equipment")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    items = data["items"]
    assert len(items) > 50

    names = {item["name"] for item in items}
    assert "Longsword" in names
    assert "Dagger" in names
    assert "Shield" in names
    assert "Chain Mail" in names

    # Check categories
    shield_item = next(i for i in items if i["name"] == "Shield")
    assert shield_item["category"] == "Shield"
    assert shield_item["ac_bonus"] == 2

    longsword_item = next(i for i in items if i["name"] == "Longsword")
    assert longsword_item["category"] == "Weapon"
    assert "damage" in longsword_item


def test_inventory_shield_equipping():
    """Verify that equipping a shield adds +2 AC, and magic bonus adds extra."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Fighter", 1)
    builder.set_background("Soldier")
    builder.set_abilities({
        "Strength": 16,
        "Dexterity": 14,
        "Constitution": 14,
        "Intelligence": 10,
        "Wisdom": 12,
        "Charisma": 8,
    })

    # Unarmored without shield: 10 + Dex (2) = 12
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {"id": "s1", "name": "Shield", "category": "Shield", "equipped": False, "quantity": 1}
        ]
    })
    char = builder.to_character()
    ac_options = char["ac_options"]
    assert ac_options[0]["ac"] == 12  # Unarmored, shield unequipped

    # Equip shield: 12 + 2 = 14
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {"id": "s1", "name": "Shield", "category": "Shield", "equipped": True, "quantity": 1}
        ]
    })
    char = builder.to_character()
    ac_options = char["ac_options"]
    assert ac_options[0]["ac"] == 14
    assert ac_options[0]["shield"] is True

    # Equip +1 Shield: 12 + 2 + 1 = 15
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {"id": "s1", "name": "+1 Shield", "base_item": "Shield", "category": "Shield", "ac_bonus": 1, "equipped": True, "quantity": 1}
        ]
    })
    char = builder.to_character()
    ac_options = char["ac_options"]
    assert ac_options[0]["ac"] == 15


def test_inventory_custom_weapon_equipping():
    """Verify that custom weapon bonuses (+1 attack/damage) apply when equipped, and disappear when unequipped."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Fighter", 1)
    builder.set_background("Soldier")
    builder.set_abilities({
        "Strength": 16,
        "Dexterity": 10,
        "Constitution": 14,
        "Intelligence": 10,
        "Wisdom": 12,
        "Charisma": 8,
    })

    # Standard Longsword: Prof (+2) + STR (+3) = +5 attack, 1d8 + 3 damage. Custom +1 gives +6 atk, 1d8 + 4 dmg.
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {
                "id": "w1",
                "name": "+1 Longsword",
                "base_item": "Longsword",
                "category": "Weapon",
                "attack_bonus": 1,
                "damage_bonus": 1,
                "equipped": True,
                "quantity": 1,
            }
        ]
    })
    char = builder.to_character()
    attacks = char["attacks"]
    # Unarmed Strike is always present, plus the equipped weapon
    weapon_attacks = [a for a in attacks if a["name"] == "+1 Longsword"]
    assert len(weapon_attacks) == 1
    wep = weapon_attacks[0]
    # Base +5 atk, +1 magic = +6 atk
    assert wep["attack_bonus"] == 6
    # Base +3 dmg, +1 magic = +4 dmg
    assert wep["damage_bonus"] == 4
    assert "1d8 + 4" in wep["damage"]
    assert any("+1 weapon bonus" in note for note in wep.get("damage_notes", []))

    # Unequip weapon: only Unarmed Strike should remain
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {
                "id": "w1",
                "name": "+1 Longsword",
                "base_item": "Longsword",
                "category": "Weapon",
                "attack_bonus": 1,
                "damage_bonus": 1,
                "equipped": False,
                "quantity": 1,
            }
        ]
    })
    char = builder.to_character()
    remaining_weapons = [a for a in char["attacks"] if a["name"] == "+1 Longsword"]
    assert len(remaining_weapons) == 0


def test_inventory_ring_of_protection():
    """Verify that equipping a non-armor item with ac_bonus (e.g. Ring of Protection) increases AC."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Fighter", 1)
    builder.set_background("Soldier")
    builder.set_abilities({
        "Strength": 10,
        "Dexterity": 14,
        "Constitution": 10,
        "Intelligence": 10,
        "Wisdom": 10,
        "Charisma": 10,
    })

    # Unarmored: 10 + 2 = 12
    # Equip Ring of Protection (+1 AC)
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {
                "id": "r1",
                "name": "Ring of Protection",
                "category": "Gear",
                "ac_bonus": 1,
                "equipped": True,
                "quantity": 1,
            }
        ]
    })
    char = builder.to_character()
    assert char["ac_options"][0]["ac"] == 13

    # Unequip Ring: AC back to 12
    builder.apply_choice("inventory", {
        "coins": {"gp": 10},
        "items": [
            {
                "id": "r1",
                "name": "Ring of Protection",
                "category": "Gear",
                "ac_bonus": 1,
                "equipped": False,
                "quantity": 1,
            }
        ]
    })
    char = builder.to_character()
    assert char["ac_options"][0]["ac"] == 12
