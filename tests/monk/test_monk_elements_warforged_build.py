import pytest
from modules.character_builder import CharacterBuilder


def test_monk_elements_warforged_genie_touched_build():
    """
    Validates user's specific build:
    Level 6 Monk (Warrior of the Elements)
    Warforged
    Genie Touched background with Magic Initiate (Wizard)
    """
    builder = CharacterBuilder()
    builder.set_class("Monk", 6)
    builder.set_subclass("Warrior of the Elements")
    builder.set_species("Warforged")
    builder.set_background("Genie Touched")
    
    # Abilities: Dex 16 (+3), Wis 16 (+3), Con 14 (+2), Int 10 (+0), Str 10 (+0), Cha 10 (+0)
    builder.set_abilities({
        "Strength": 10,
        "Dexterity": 16,
        "Constitution": 14,
        "Intelligence": 10,
        "Wisdom": 16,
        "Charisma": 10,
    })
    
    # Apply choices made in wizard
    builder.apply_choices({
        "species_trait_Specialized Design (Skill)": "Athletics",
        "species_trait_Specialized Design (Tool)": "Tinker's Tools",
        "feat_Magic Initiate (Wizard)_spellcasting_ability": "Intelligence",
        "feat_Magic Initiate (Wizard)_cantrips": ["Mage Hand", "Minor Illusion"],
        "feat_Magic Initiate (Wizard)_1st_level_spell": "Shield",
    })
    
    # Weapons
    spear = {
        "name": "Spear",
        "quantity": 1,
        "properties": {
            "category": "Simple Melee",
            "damage": "1d6",
            "damage_type": "Piercing",
            "properties": ["Thrown (range 20/60)", "Versatile (1d8)"],
            "range": "20/60",
        },
    }
    dagger = {
        "name": "Dagger",
        "quantity": 1,
        "properties": {
            "category": "Simple Melee",
            "damage": "1d4",
            "damage_type": "Piercing",
            "properties": ["Finesse", "Light", "Thrown (range 20/60)"],
            "range": "20/60",
        },
    }
    builder.character_data["equipment"] = {
        "weapons": [spear, dagger],
        "armor": [],
        "items": [],
        "gold": 0,
    }
    
    char = builder.to_character()
    
    # 1. AC Verification: Unarmored Defense (10 + Dex 3 + Wis 3 = 16) + Warforged Integrated Protection (+1) = 17
    best_ac = char["ac_options"][0]
    assert best_ac["ac"] == 17
    assert "+1 from Integrated Protection" in best_ac["notes"]
    assert "Integrated Protection (+1)" in best_ac["formula"]
    
    # 2. Saving Throw Advantage: Construct Resilience against Poisoned
    save_advs = char.get("save_advantages", [])
    assert any("Poisoned" in adv.get("condition", "") or "Construct Resilience" in adv.get("source", "") for adv in save_advs)
    
    # 3. Proficiencies: Warforged Specialized Design
    skills = char.get("skill_proficiencies", [])
    assert "Athletics" in skills
    tools = char.get("tool_proficiencies", [])
    assert "Tinker's Tools" in tools
    
    # 4. Weapon Attacks: Monk Martial Arts die at level 6 is 1d8.
    # Base Spear (1d6) scales to 1d8. Dagger (1d4) scales to 1d8. Both use DEX (+3) and have effective_ability == 'DEX'.
    attacks_by_name = {a["name"]: a for a in char["attacks"]}
    
    assert "Unarmed Strike" in attacks_by_name
    unarmed = attacks_by_name["Unarmed Strike"]
    assert unarmed["damage"] == "1d8 + 3"
    assert unarmed["effective_ability"] == "DEX"
    assert unarmed["attack_bonus"] == 6  # PB 3 + Dex 3
    
    assert "Spear" in attacks_by_name
    spear_atk = attacks_by_name["Spear"]
    assert spear_atk["damage"] == "1d8 + 3"
    assert spear_atk["damage_one_handed"] == "1d8 + 3"
    assert spear_atk["damage_two_handed"] == "1d8 + 3"
    assert spear_atk["effective_ability"] == "DEX"
    assert spear_atk["attack_bonus"] == 6
    
    assert "Dagger" in attacks_by_name
    dagger_atk = attacks_by_name["Dagger"]
    assert dagger_atk["damage"] == "1d8 + 3"
    assert dagger_atk["throw_damage"] == "1d8 + 3"
    assert dagger_atk["effective_ability"] == "DEX"
    assert dagger_atk["attack_bonus"] == 6
    
    # 5. Spells & Magic: Spells by level
    spells_by_lvl = char["spells_by_level"]
    cantrips = {s["name"]: s for s in (spells_by_lvl.get(0) or spells_by_lvl.get("0") or [])}
    lvl1 = {s["name"]: s for s in (spells_by_lvl.get(1) or spells_by_lvl.get("1") or [])}
    
    # Ensure ability names are NEVER present as spells
    for ab_name in ("Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"):
        assert ab_name not in cantrips, f"{ab_name} should not be in cantrips"
        assert ab_name not in lvl1, f"{ab_name} should not be in level 1 spells"

    # Elementalism from Manipulate Elements (Wisdom)
    assert "Elementalism" in cantrips
    elem = cantrips["Elementalism"]
    assert elem["spellcasting_ability"] == "Wisdom"
    assert elem["spell_save_dc"] == 14  # 8 + PB 3 + Wis 3
    assert elem["spell_attack_bonus"] == 6  # PB 3 + Wis 3
    
    # Magic Initiate (Wizard) spells with chosen ability Intelligence
    assert "Mage Hand" in cantrips
    mh = cantrips["Mage Hand"]
    assert mh["spellcasting_ability"] == "Intelligence"
    assert mh["spell_save_dc"] == 11  # 8 + PB 3 + Int 0
    assert mh["spell_attack_bonus"] == 3  # PB 3 + Int 0
    
    assert "Minor Illusion" in cantrips
    assert "Shield" in lvl1
    shield = lvl1["Shield"]
    assert shield["spellcasting_ability"] == "Intelligence"
    assert shield["spell_save_dc"] == 11
    assert shield["once_per_day"] is True or shield.get("once_per_long_rest") is True


def test_monk_magic_initiate_wizard_with_wisdom_ability():
    """
    Validates that selecting Wisdom as the spellcasting ability for Magic Initiate (Wizard)
    correctly applies Wisdom as the spellcasting ability for all feat spells, calculates
    the correct save DC (14) and attack bonus (+6), and NEVER creates a spell named 'Wisdom'.
    """
    builder = CharacterBuilder()
    builder.set_class("Monk", 6)
    builder.set_subclass("Warrior of the Elements")
    builder.set_species("Warforged")
    builder.set_background("Genie Touched")
    builder.set_abilities({
        "Strength": 10,
        "Dexterity": 16,
        "Constitution": 14,
        "Intelligence": 10,
        "Wisdom": 16,
        "Charisma": 10,
    })
    
    # User choice: Magic Initiate (Wizard) with Wisdom
    builder.apply_choices({
        "species_trait_Specialized Design (Skill)": "Athletics",
        "species_trait_Specialized Design (Tool)": "Tinker's Tools",
        "feat_Magic Initiate (Wizard)_spellcasting_ability": "Wisdom",
        "feat_Magic Initiate (Wizard)_cantrips": ["Shocking Grasp", "True Strike"],
        "feat_Magic Initiate (Wizard)_1st_level_spell": "Chromatic Orb",
    })
    
    # Deliberately pollute always_prepared with 'Wisdom' as might happen from old stale session state
    builder.character_data["spells"]["always_prepared"]["Wisdom"] = {
        "level": 0,
        "source": "Magic Initiate (Wizard)",
        "always_prepared": True,
    }
    
    char = builder.to_character()
    spells_by_lvl = char["spells_by_level"]
    cantrips = {s["name"]: s for s in (spells_by_lvl.get(0) or spells_by_lvl.get("0") or [])}
    lvl1 = {s["name"]: s for s in (spells_by_lvl.get(1) or spells_by_lvl.get("1") or [])}
    
    # Assert 'Wisdom' is NOT in cantrips or lvl1
    assert "Wisdom" not in cantrips
    assert "Wisdom" not in lvl1
    
    # Elementalism (Wisdom)
    assert "Elementalism" in cantrips
    assert cantrips["Elementalism"]["spellcasting_ability"] == "Wisdom"
    assert cantrips["Elementalism"]["spell_save_dc"] == 14
    assert cantrips["Elementalism"]["spell_attack_bonus"] == 6
    
    # Shocking Grasp (Wisdom)
    assert "Shocking Grasp" in cantrips
    assert cantrips["Shocking Grasp"]["spellcasting_ability"] == "Wisdom"
    assert cantrips["Shocking Grasp"]["spell_save_dc"] == 14
    assert cantrips["Shocking Grasp"]["spell_attack_bonus"] == 6
    
    # True Strike (Wisdom)
    assert "True Strike" in cantrips
    assert cantrips["True Strike"]["spellcasting_ability"] == "Wisdom"
    assert cantrips["True Strike"]["spell_save_dc"] == 14
    assert cantrips["True Strike"]["spell_attack_bonus"] == 6
    
    # Chromatic Orb (Wisdom)
    assert "Chromatic Orb" in lvl1
    assert lvl1["Chromatic Orb"]["spellcasting_ability"] == "Wisdom"
    assert lvl1["Chromatic Orb"]["spell_save_dc"] == 14
    assert lvl1["Chromatic Orb"]["spell_attack_bonus"] == 6
    assert lvl1["Chromatic Orb"]["once_per_day"] is True or lvl1["Chromatic Orb"].get("once_per_long_rest") is True

