"""
Integration tests for Arcana Unleashed sourcebook supplement.
Tests supplement registration, subclasses, Arcane Archer mechanics,
Arcana Domain Cleric, backgrounds, feats, spells, and API serialization.
"""

import pytest
from modules.supplement_manager import get_supplement_manager
from modules.data_loader import DataLoader
from modules.character_builder import CharacterBuilder


def test_au_supplement_metadata_and_counts():
    """Verify Arcana Unleashed supplement is registered and has expected entity counts."""
    sm = get_supplement_manager()
    sups = sm.list_supplements()
    au = next((s for s in sups if s["id"] == "arcana-unleashed"), None)
    assert au is not None, "Arcana Unleashed supplement not found"
    assert au["title"] == "Arcana Unleashed"

    counts = au.get("counts", {})
    assert counts.get("subclasses") == 8
    assert counts.get("backgrounds") == 10
    assert counts.get("feats") == 29
    assert counts.get("spells") == 33


def test_au_subclasses_available_in_data_loader():
    """Verify all 8 AU subclasses are accessible via DataLoader for active sources."""
    dl = DataLoader()
    active_sources = ["core-phb-2024", "arcana-unleashed"]

    fighter_sc = dl.get_subclasses_for_class("Fighter", active_sources)
    assert "Arcane Archer" in fighter_sc

    cleric_sc = dl.get_subclasses_for_class("Cleric", active_sources)
    assert "Arcana Domain" in cleric_sc

    monk_sc = dl.get_subclasses_for_class("Monk", active_sources)
    assert "Warrior of the Mystic Arts" in monk_sc

    warlock_sc = dl.get_subclasses_for_class("Warlock", active_sources)
    assert "Vestige Patron" in warlock_sc

    wizard_sc = dl.get_subclasses_for_class("Wizard", active_sources)
    assert "Conjurer" in wizard_sc
    assert "Enchanter" in wizard_sc
    assert "Necromancer" in wizard_sc
    assert "Transmuter" in wizard_sc


def test_arcane_archer_level_3_builder():
    """Verify Arcane Archer Fighter at Level 3 learns 2 Arcane Shots and has d6 die."""
    b = CharacterBuilder()
    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 3,
        "subclass": "Arcane Archer",
        "subclass_Arcane Shot": ["Banishing Shot", "Bursting Shot"],
    }
    applied = b.apply_choices(choices)
    assert applied is True

    assert b.character_data.get("subclass") == "Arcane Archer"
    assert b.character_data.get("arcane_shot_die") == "d6"
    assert set(b.character_data.get("arcane_shots_known", [])) == {"Banishing Shot", "Bursting Shot"}

    # Check feature display name formatting
    subclass_feats = b.character_data["features"]["subclass"]
    feat_names = [f["name"] for f in subclass_feats]
    assert any("Arcane Shot: Banishing Shot, Bursting Shot" in name for name in feat_names)


def test_arcane_archer_choice_key_alias():
    """Verify both 'arcane_shots' and 'subclass_Arcane Shot' resolve correctly."""
    b = CharacterBuilder()
    b.set_class("Fighter", 3)
    b.set_subclass("Arcane Archer")
    b.apply_choice("arcane_shots", ["Grasping Shot", "Piercing Shot"])

    assert set(b.character_data.get("arcane_shots_known", [])) == {"Grasping Shot", "Piercing Shot"}
    assert b.character_data.get("arcane_shot_die") == "d6"


def test_arcane_archer_die_scaling():
    """Verify Arcane Shot Die scales from d6 at level 3 to d12 at level 18."""
    levels_and_dice = [
        (3, "d6"),
        (7, "d6"),
        (10, "d8"),
        (15, "d10"),
        (18, "d12"),
    ]
    for lvl, expected_die in levels_and_dice:
        b = CharacterBuilder()
        b.set_class("Fighter", lvl)
        b.set_subclass("Arcane Archer")
        b.apply_choice("subclass_Arcane Shot", ["Banishing Shot", "Bursting Shot"])
        assert b.character_data.get("arcane_shot_die") == expected_die, (
            f"Expected {expected_die} at level {lvl}, got {b.character_data.get('arcane_shot_die')}"
        )


def test_arcana_domain_cleric_builder():
    """Verify Arcana Domain Cleric gains domain spells and features."""
    b = CharacterBuilder()
    choices = {
        "species": "Elf",
        "class": "Cleric",
        "level": 3,
        "subclass": "Arcana Domain",
    }
    applied = b.apply_choices(choices)
    assert applied is True

    # Domain spells prepared
    always_prep = b.character_data.get("spells", {}).get("always_prepared", {})
    assert "Detect Magic" in always_prep
    assert "Magic Missile" in always_prep
    assert "Magic Weapon" in always_prep
    assert "Nystul's Magic Aura" in always_prep

    # Subclass features
    subclass_feat_names = [f["name"] for f in b.character_data["features"]["subclass"]]
    assert "Arcana Domain Spells" in subclass_feat_names
    assert "Student of Arcana" in subclass_feat_names


def test_au_background_and_origin_feat():
    """Verify AU backgrounds load correctly and grant their origin feats."""
    dl = DataLoader()
    active_sources = ["core-phb-2024", "arcana-unleashed"]
    backgrounds = dl.get_backgrounds(active_sources)

    assert "Agent of the Ninth Quill" in backgrounds
    bg = backgrounds["Agent of the Ninth Quill"]
    origin_feat_effect = next((e for e in bg.get("effects", []) if e.get("type") in ("grant_origin_feat", "grant_feat")), None)
    assert origin_feat_effect is not None
    assert origin_feat_effect.get("feat") == "Arcane Infiltrator"

    # Test building a character with this background
    b = CharacterBuilder()
    choices = {
        "species": "Human",
        "class": "Fighter",
        "level": 1,
        "background": "Agent of the Ninth Quill",
    }
    applied = b.apply_choices(choices)
    assert applied is True
    assert b.character_data.get("background") == "Agent of the Ninth Quill"

    # Feats list should have the background's feat
    feat_names = [f["name"] for f in b.character_data["features"]["feats"]]
    assert any("Arcane Infiltrator" in name for name in feat_names)


def test_au_character_api_build(client):
    """Test full API round-trip build for an Arcane Archer character."""
    payload = {
        "choices_made": {
            "character_name": "Eldrin the Bowmaster",
            "species": "Elf",
            "class": "Fighter",
            "level": 3,
            "subclass": "Arcane Archer",
            "background": "Agent of the Ninth Quill",
            "subclass_Arcane Shot": ["Banishing Shot", "Bursting Shot"],
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 14,
                "Wisdom": 12,
                "Charisma": 8,
            },
        }
    }
    response = client.post("/api/v1/character/build", json=payload)
    assert response.status_code == 200, f"Build failed: {response.get_json()}"
    char_data = response.get_json()["character"]
    assert char_data["name"] == "Eldrin the Bowmaster"
    assert char_data["class"] == "Fighter"
    assert char_data["subclass"] == "Arcane Archer"
    assert char_data["level"] == 3
    assert char_data["arcane_shot_die"] == "d6"
    assert set(char_data["arcane_shots_known"]) == {"Banishing Shot", "Bursting Shot"}


def test_warrior_of_mystic_arts_monk():
    """Test Warrior of the Mystic Arts Monk subclass from AU."""
    builder = CharacterBuilder()
    choices = {
        "class": "Monk",
        "level": 3,
        "subclass": "Warrior of the Mystic Arts",
        "species": "Human",
        "background": "Familiar Trainer",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
    }
    applied = builder.apply_choices(choices)
    assert applied is True
    assert builder.character_data.get("subclass") == "Warrior of the Mystic Arts"
    subclass_features = [f["name"] for f in builder.character_data["features"]["subclass"]]
    assert any("Spellcasting" in f for f in subclass_features)


def test_vestige_patron_warlock():
    """Test Vestige Patron Warlock subclass from AU."""
    builder = CharacterBuilder()
    choices = {
        "class": "Warlock",
        "level": 3,
        "subclass": "Vestige Patron",
        "species": "Human",
        "background": "Covenant of the Grave Recruit",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
    }
    applied = builder.apply_choices(choices)
    assert applied is True
    assert builder.character_data.get("subclass") == "Vestige Patron"
    subclass_features = [f["name"] for f in builder.character_data["features"]["subclass"]]
    assert any("Vestige Spells" in f for f in subclass_features)
    assert any("Vestige Companion" in f for f in subclass_features)


def test_wizard_specialist_subclasses():
    """Test the four Wizard schools added in AU: Conjurer, Enchanter, Necromancer, Transmuter."""
    for sub in ["Conjurer", "Enchanter", "Necromancer", "Transmuter"]:
        b = CharacterBuilder()
        choices = {
            "class": "Wizard",
            "level": 3,
            "subclass": sub,
            "species": "Human",
            "background": "Agent of the Ninth Quill",
            "active_sources": ["core-phb-2024", "arcana-unleashed"],
        }
        applied = b.apply_choices(choices)
        assert applied is True
        assert b.character_data.get("subclass") == sub
        subclass_features = b.character_data["features"]["subclass"]
        assert len(subclass_features) >= 1, f"Expected features for {sub}"


def test_au_feats_loading():
    """Verify all 29 AU feats are discoverable and loadable."""
    from modules.data_loader import DataLoader
    dl = DataLoader()
    feats = dl.get_feats(active_sources=["core-phb-2024", "arcana-unleashed"])
    au_feats = {k: v for k, v in feats.items() if v.get("source") == "Arcana Unleashed"}
    assert len(au_feats) == 29
    # Verify both Origin and General feats exist
    origin_feats = [f for f in au_feats.values() if f.get("category") == "Origin"]
    general_feats = [f for f in au_feats.values() if f.get("category") in ("General", "Fighting Style", "Epic Boon")]
    assert len(origin_feats) == 10
    assert len(general_feats) == 19


def test_arcane_archer_preview_step_and_subclass_lore_choices(client):
    """Verify preview-step and full build for Arcane Archer lore and shot choices."""
    # 1. Preview step test
    preview_payload = {
        "choices_made": {
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "subclass": "Arcane Archer",
            "background": "Soldier",
            "active_sources": ["core-phb-2024", "arcana-unleashed"],
        },
        "step": "class",
    }
    preview_res = client.post("/api/v1/character/preview-step", json=preview_payload)
    assert preview_res.status_code == 200, f"Preview failed: {preview_res.get_json()}"
    nested = preview_res.get_json().get("nested_choices", [])
    choice_keys = [c.get("choices_made_key") or c.get("choice_key") for c in nested]
    assert "subclass_Arcane Archer Lore_cantrip" in choice_keys
    assert "subclass_Arcane Archer Lore_skill1" in choice_keys
    assert "subclass_Arcane Archer Lore_skill2" in choice_keys
    assert "arcane_shots" in choice_keys or "subclass_Arcane Shot" in choice_keys

    # 2. Build test with canonical choices_made_key
    build_payload = {
        "choices_made": {
            "character_name": "Robin the Arcane",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "subclass": "Arcane Archer",
            "background": "Soldier",
            "active_sources": ["core-phb-2024", "arcana-unleashed"],
            "fighting_style": "Archery",
            "subclass_Arcane Archer Lore_cantrip": "Druidcraft",
            "subclass_Arcane Archer Lore_skill1": "Arcana",
            "subclass_Arcane Archer Lore_skill2": "Nature",
            "subclass_Arcane Shot": ["Banishing Shot", "Bursting Shot"],
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 14,
                "Wisdom": 12,
                "Charisma": 8,
            },
        }
    }
    build_res = client.post("/api/v1/character/build", json=build_payload)
    assert build_res.status_code == 200, f"Build failed: {build_res.get_json()}"
    char = build_res.get_json()["character"]
    assert char["subclass"] == "Arcane Archer"
    assert "Druidcraft" in char.get("spells", {}).get("always_prepared", {})
    assert "Arcana" in char.get("proficiencies", {}).get("skills", [])
    assert "Nature" in char.get("proficiencies", {}).get("skills", [])
    assert set(char.get("arcane_shots_known", [])) == {"Banishing Shot", "Bursting Shot"}

    # 3. Build test with short choice_key
    build_payload_short = {
        "choices_made": {
            "character_name": "Robin Short Keys",
            "species": "Human",
            "class": "Fighter",
            "level": 3,
            "subclass": "Arcane Archer",
            "background": "Soldier",
            "active_sources": ["core-phb-2024", "arcana-unleashed"],
            "fighting_style": "Archery",
            "cantrip": "Prestidigitation",
            "skill1": "Arcana",
            "skill2": "Nature",
            "arcane_shots": ["Piercing Shot", "Seeking Shot"],
            "ability_scores": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 14,
                "Wisdom": 12,
                "Charisma": 8,
            },
        }
    }
    build_res_short = client.post("/api/v1/character/build", json=build_payload_short)
    assert build_res_short.status_code == 200, f"Short build failed: {build_res_short.get_json()}"
    char_short = build_res_short.get_json()["character"]
    assert "Prestidigitation" in char_short.get("spells", {}).get("always_prepared", {})
    assert set(char_short.get("arcane_shots_known", [])) == {"Piercing Shot", "Seeking Shot"}


def test_necromancy_adept_feat_level_4_asi_and_spells():
    """Verify Necromancy Adept feat grants +1 ASI and school spells at level 4."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Valeros",
        "species": "Human",
        "class": "Wizard",
        "level": 4,
        "subclass": "Evoker",
        "background": "Sage",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "ability_scores": {
            "Strength": 10, "Dexterity": 12, "Constitution": 14,
            "Intelligence": 15, "Wisdom": 12, "Charisma": 8
        },
        "class_feat_4": "Necromancy Adept",
        "class_feat_4_ability": "Intelligence",
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    # Processed abilities: INT should be 15 + 1 = 16
    scores = builder.calculate_processed_ability_scores()
    assert scores["intelligence"]["score"] == 16
    assert scores["intelligence"]["modifier"] == 3

    # Spell grants: Inflict Wounds (min_level 1) and Ray of Enfeeblement (min_level 3)
    # should be prepared for a level 4 character.
    always_prep = builder.character_data.get("spells", {}).get("always_prepared", {})
    assert "Inflict Wounds" in always_prep
    assert "Ray of Enfeeblement" in always_prep
    # Vampiric Touch (min_level 5) should NOT yet be prepared at level 4
    assert "Vampiric Touch" not in always_prep


def test_mystic_arts_monk_spellcasting_progression():
    """Verify Warrior of the Mystic Arts Monk has 1/3 caster progression and slots."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Zenith",
        "species": "Human",
        "class": "Monk",
        "level": 3,
        "subclass": "Warrior of the Mystic Arts",
        "background": "Familiar Trainer",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "ability_scores": {
            "Strength": 10, "Dexterity": 16, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 16, "Charisma": 8
        },
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    char = builder.to_character()
    slots = char.get("spell_slots", {})
    # Level 3 1/3 caster has 2 level-1 spell slots
    assert slots.get("1st") == 2


def test_vestige_patron_domain_spells():
    """Verify Vestige Patron Warlock domain spell choice grants domain spells."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Malakor",
        "species": "Human",
        "class": "Warlock",
        "level": 3,
        "subclass": "Vestige Patron",
        "background": "Covenant of the Grave Recruit",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "subclass_Vestige Spells_domain": "Life Domain",
        "ability_scores": {
            "Strength": 10, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 10, "Charisma": 16
        },
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    always_prep = builder.character_data.get("spells", {}).get("always_prepared", {})
    assert "Aid" in always_prep
    assert "Bless" in always_prep
    assert "Cure Wounds" in always_prep
    assert "Lesser Restoration" in always_prep


def test_enchanter_conversationalist_skills():
    """Verify Enchanter Wizard gains 2 chosen skills from Enchanting Conversationalist."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Seraphina",
        "species": "Human",
        "class": "Wizard",
        "level": 3,
        "subclass": "Enchanter",
        "background": "Sage",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "subclass_Enchanting Conversationalist_skills": ["Deception", "Persuasion"],
        "ability_scores": {
            "Strength": 10, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 16, "Wisdom": 10, "Charisma": 12
        },
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    skills = builder.character_data.get("proficiencies", {}).get("skills", [])
    assert "Deception" in skills
    assert "Persuasion" in skills


def test_spell_resistant_and_portal_jumper_resistances():
    """Verify damage resistance selection on Spell Resistant and Portal Jumper."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Aegis",
        "species": "Human",
        "class": "Fighter",
        "level": 4,
        "background": "Horizon Weaver Initiate",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "feat_Portal Jumper_damage_resistance": "Radiant",
        "class_feat_4": "Spell Resistant",
        "class_feat_4_ability": "Constitution",
        "class_feat_4_damage_resistance": "Psychic",
        "ability_scores": {
            "Strength": 16, "Dexterity": 12, "Constitution": 14,
            "Intelligence": 10, "Wisdom": 12, "Charisma": 8
        },
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    resistances = builder.character_data.get("resistances", [])
    assert "Psychic" in resistances


def test_epic_boon_asi_above_20():
    """Verify Epic Boons can increase ability scores up to 30."""
    builder = CharacterBuilder()
    choices = {
        "character_name": "Archmage",
        "species": "Human",
        "class": "Wizard",
        "level": 19,
        "subclass": "Evoker",
        "background": "Sage",
        "active_sources": ["core-phb-2024", "arcana-unleashed"],
        "ability_scores": {
            "Strength": 10, "Dexterity": 14, "Constitution": 14,
            "Intelligence": 20, "Wisdom": 10, "Charisma": 10
        },
        "class_feat_19": "Boon of Erupting Spellpower",
        "class_feat_19_ability": "Intelligence",
    }
    applied = builder.apply_choices(choices)
    assert applied is True

    scores = builder.calculate_processed_ability_scores()
    assert scores["intelligence"]["score"] == 21
    assert scores["intelligence"]["modifier"] == 5



