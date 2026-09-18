"""Unit tests for Artificer class mechanics, Tinker's Magic, subclass spells, and Replicate Magic Item."""

import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_replicate_magic_item_view


def test_artificer_level_1_tinkers_magic():
    """Level 1 Artificer gains Prestidigitation and Mending via Tinker's Magic and tool proficiencies."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 1)
    char = builder.to_character()

    always_prepared = char.get("spells", {}).get("always_prepared", {})
    assert "Prestidigitation" in always_prepared
    assert "Mending" in always_prepared

    cantrip_names = [c["name"] for c in char.get("spells", {}).get("cantrips", [])]
    assert "Prestidigitation" in cantrip_names
    assert "Mending" in cantrip_names

    tools = char.get("proficiencies", {}).get("tools", [])
    assert any("Thieves" in t for t in tools)
    assert any("Tinker" in t for t in tools)

    assert "artificer_replications" not in char
    rep_stats = builder.calculate_artificer_replications_stats()
    assert rep_stats.get("has_replications") is False
    assert rep_stats.get("max_plans") == 0
    assert rep_stats.get("max_active") == 0


def test_artificer_level_2_replicate_magic_item():
    """Level 2 Artificer gains 4 plans known and 2 active items limit."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 2)
    builder.apply_choice(
        "artificer_replicate_plans",
        ["Alchemy Jug", "Bag of Holding", "Cap of Water Breathing", "Goggles of Night"],
    )
    builder.apply_choice("artificer_active_replications", ["Alchemy Jug", "Bag of Holding"])
    char = builder.to_character()

    rep = char.get("artificer_replications", {})
    assert rep.get("has_replications") is True
    assert rep.get("max_plans") == 4
    assert rep.get("max_active") == 2
    assert rep.get("known_plans") == [
        "Alchemy Jug",
        "Bag of Holding",
        "Cap of Water Breathing",
        "Goggles of Night",
    ]
    assert rep.get("active_items") == ["Alchemy Jug", "Bag of Holding"]
    assert len(rep.get("known_plans_details", [])) == 4
    assert len(rep.get("active_items_details", [])) == 2

    # Verify choices_made serialization
    choices = char.get("choices_made", {})
    assert choices.get("artificer_replicate_plans") == [
        "Alchemy Jug",
        "Bag of Holding",
        "Cap of Water Breathing",
        "Goggles of Night",
    ]
    assert choices.get("artificer_active_replications") == ["Alchemy Jug", "Bag of Holding"]

    # Test derived view
    derived = build_replicate_magic_item_view(builder)
    assert derived.get("has_replications") is True
    assert derived.get("max_plans") == 4
    assert derived.get("max_active") == 2


def test_artificer_level_3_cartographer():
    """Level 3 Cartographer gains Faerie Fire, Guiding Bolt, Healing Word, and Cartographer's Tools."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Cartographer")
    char = builder.to_character()

    always_prepared = char.get("spells", {}).get("always_prepared", {})
    assert "Faerie Fire" in always_prepared
    assert "Guiding Bolt" in always_prepared
    assert "Healing Word" in always_prepared

    level_1_names = [s["name"] for s in char.get("spells", {}).get("level_1", [])]
    assert "Faerie Fire" in level_1_names
    assert "Guiding Bolt" in level_1_names
    assert "Healing Word" in level_1_names

    tools = char.get("proficiencies", {}).get("tools", [])
    assert any("Cartographer" in t for t in tools)


def test_artificer_level_3_armorer():
    """Level 3 Armorer gains Magic Missile, Thunderwave, and Heavy armor proficiency."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Armorer")
    char = builder.to_character()

    always_prepared = char.get("spells", {}).get("always_prepared", {})
    assert "Magic Missile" in always_prepared
    assert "Thunderwave" in always_prepared

    armor = char.get("proficiencies", {}).get("armor", [])
    assert any("Heavy" in a for a in armor)


def test_artificer_level_3_battle_smith():
    """Level 3 Battle Smith gains Heroism, Shield, and Martial weapons proficiency."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 3)
    builder.apply_choice("subclass", "Battle Smith")
    char = builder.to_character()

    always_prepared = char.get("spells", {}).get("always_prepared", {})
    assert "Heroism" in always_prepared
    assert "Shield" in always_prepared

    weapons = char.get("proficiencies", {}).get("weapons", [])
    assert any("Martial" in w for w in weapons)


def test_artificer_level_9_armorer_improved():
    """Level 9 Armorer gets 5 active replications (3 base + 2 Improved Armorer)."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 9)
    builder.apply_choice("subclass", "Armorer")
    char = builder.to_character()

    rep = char.get("artificer_replications", {})
    assert rep.get("max_plans") == 6
    assert rep.get("max_active") == 5


def test_artificer_level_14_advanced_artifice():
    """Level 14 Artificer gets 11 plans known (10 base + 1 Advanced Artifice) and 5 active items."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Artificer")
    builder.apply_choice("level", 14)
    char = builder.to_character()

    rep = char.get("artificer_replications", {})
    assert rep.get("max_plans") == 11
    assert rep.get("max_active") == 5

    # Should have tier 14 items available
    available = rep.get("available_plans", [])
    assert any(p["name"] == "Amulet of Health" for p in available)
    assert any(p["name"] == "Boots of Speed" for p in available)


def test_non_artificer_replications():
    """Non-artificer character has no replications and raising ValueError in derived view."""
    builder = CharacterBuilder()
    builder.apply_choice("species", "Human")
    builder.apply_choice("class", "Wizard")
    builder.apply_choice("level", 5)
    char = builder.to_character()

    assert "artificer_replications" not in char
    rep_stats = builder.calculate_artificer_replications_stats()
    assert rep_stats.get("has_replications") is False

    with pytest.raises(ValueError, match="Character does not have Replicate Magic Item"):
        build_replicate_magic_item_view(builder)


def test_artificer_apply_choices_strict_mode():
    """Applying choices dictionary with replicate plans and active loadout in strict mode must succeed."""
    builder = CharacterBuilder()
    success = builder.apply_choices(
        {
            "species": "Human",
            "class": "Artificer",
            "level": 2,
            "artificer_replicate_plans": ["Bag of Holding", "Goggles of Night"],
            "artificer_active_replications": ["Bag of Holding"],
        },
        fail_on_error=True,
    )
    assert success is True
    char = builder.to_character()
    rep = char.get("artificer_replications", {})
    assert rep.get("has_replications") is True
    assert rep.get("known_plans") == ["Bag of Holding", "Goggles of Night"]
    assert rep.get("active_items") == ["Bag of Holding"]


def test_artificer_api_validation_and_derived():
    """Validate and derived endpoints must accept artificer choices without unknown key error."""
    import app

    client = app.app.test_client()
    payload = {
        "choices_made": {
            "classes": [{"class_name": "Artificer", "level": 2}],
            "class": "Artificer",
            "level": 2,
            "artificer_replicate_plans": ["Bag of Holding"],
            "artificer_active_replications": ["Bag of Holding"],
        }
    }

    # Validate
    res = client.post("/api/v1/character/validate", json=payload)
    assert res.status_code == 200

    # Derived
    res = client.post(
        "/api/v1/character/derived",
        json={**payload, "view": "replicate_magic_item_management"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("applicable") is True
    assert data["data"]["active_items"] == ["Bag of Holding"]

    # Preview step
    res = client.post(
        "/api/v1/character/preview-step",
        json={"step": "class", "choices_made": payload["choices_made"]},
    )
    assert res.status_code == 200

