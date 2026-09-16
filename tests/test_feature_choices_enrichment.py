"""Tests for feature choice display and enrichment in character sheets.

Verifies that choices made for features (e.g. Battle Master maneuvers,
Arcane Archer shots, Hunter's Prey, Divine Order) are enriched with
sub-choice descriptions, calculated DCs, dice, uses, and exported
to both feature objects and top-level character data.
"""

import pytest
from modules.character_builder import CharacterBuilder


class TestFeatureChoicesEnrichment:
    """Tests for feature choices and sub-choice enrichment."""

    def test_battle_master_maneuvers_enrichment(self):
        """Test Battle Master maneuvers, superiority dice, and save DC."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Fighter",
            "level": 3,
            "subclass": "Battle Master",
            "fighting_style": "Defense",
            "maneuvers": ["Riposte", "Trip Attack", "Precision Attack"],
            "artisan_tool": "Smith's tools",
            "abilities": {
                "Strength": 16,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 12,
                "Charisma": 8,
            },
        })

        char = builder.to_character()

        # Check top-level exports
        assert "maneuvers" in char
        assert len(char["maneuvers"]) == 3
        maneuver_names = [m["name"] for m in char["maneuvers"]]
        assert maneuver_names == ["Riposte", "Trip Attack", "Precision Attack"]
        assert all(m["description"] for m in char["maneuvers"])

        assert "superiority_dice" in char
        sup_dice = char["superiority_dice"]
        assert sup_dice["count"] == 4
        assert sup_dice["die"] == "d8"
        # Str mod is +3, PB is +2 -> Save DC = 8 + 3 + 2 = 13
        assert sup_dice["save_dc"] == 13

        # Check subclass feature object
        subclass_features = char.get("features", {}).get("subclass", [])
        cs_feat = next(
            (f for f in subclass_features if "Combat Superiority" in f["name"]),
            None,
        )
        assert cs_feat is not None
        assert cs_feat["name"] == "Combat Superiority: Riposte, Trip Attack, Precision Attack"
        assert "chosen_options" in cs_feat
        assert len(cs_feat["chosen_options"]) == 3

        desc = cs_feat["description"]
        assert "**Superiority Dice**: 4 (d8) | **Maneuver Save DC**: 13" in desc
        assert "**Selected Maneuvers**:" in desc
        assert "• **Riposte**:" in desc
        assert "• **Trip Attack**:" in desc
        assert "• **Precision Attack**:" in desc

        # Ensure no duplication of maneuver titles in description
        assert desc.count("**Riposte**") == 1
        assert desc.count("**Trip Attack**") == 1
        assert desc.count("**Precision Attack**") == 1

        # Check Student of War
        sow_feat = next(
            (f for f in subclass_features if "Student of War" in f["name"]),
            None,
        )
        assert sow_feat is not None
        assert "Smith's tools" in sow_feat["name"]
        assert "chosen_options" in sow_feat

    def test_arcane_archer_shots_enrichment(self):
        """Test Arcane Archer arcane shots, shot die, save DC, and uses."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Fighter",
            "level": 3,
            "subclass": "Arcane Archer",
            "fighting_style": "Archery",
            "arcane_shots": ["Bursting Shot", "Grasping Shot"],
            "subclass_Arcane Archer Lore_cantrip": "Prestidigitation",
            "subclass_Arcane Archer Lore_skill1": "Arcana",
            "subclass_Arcane Archer Lore_skill2": "Nature",
            "abilities": {
                "Strength": 10,
                "Dexterity": 16,
                "Constitution": 14,
                "Intelligence": 16,
                "Wisdom": 12,
                "Charisma": 8,
            },
        })

        char = builder.to_character()

        # Check top-level exports
        assert "arcane_shots" in char
        assert len(char["arcane_shots"]) == 2
        shot_names = [s["name"] for s in char["arcane_shots"]]
        assert shot_names == ["Bursting Shot", "Grasping Shot"]
        assert all(s["description"] for s in char["arcane_shots"])

        # Int mod is +3, PB is +2 -> Save DC = 8 + 3 + 2 = 13
        assert char["arcane_shot_die"] == "d6"
        assert char["arcane_shot_dc"] == 13
        assert char["arcane_shot_uses"] == 3

        # Check subclass feature object
        subclass_features = char.get("features", {}).get("subclass", [])
        shot_feat = next(
            (f for f in subclass_features if "Arcane Shot" in f["name"]),
            None,
        )
        assert shot_feat is not None
        assert shot_feat["name"] == "Arcane Shot: Bursting Shot, Grasping Shot"
        assert "chosen_options" in shot_feat
        assert len(shot_feat["chosen_options"]) == 2

        desc = shot_feat["description"]
        assert "**Arcane Shot Die**: d6 | **Save DC**: 13 | **Uses**: 3 per Short or Long Rest" in desc
        assert "**Selected Arcane Shots**:" in desc
        assert "• **Bursting Shot**:" in desc
        assert "• **Grasping Shot**:" in desc

        # Ensure no duplication
        assert desc.count("**Bursting Shot**") == 1
        assert desc.count("**Grasping Shot**") == 1

        # Check Arcane Archer Lore
        lore_feat = next(
            (f for f in subclass_features if "Arcane Archer Lore" in f["name"]),
            None,
        )
        assert lore_feat is not None
        assert "chosen_options" in lore_feat
        lore_chosen = [o["name"] for o in lore_feat["chosen_options"]]
        assert "Prestidigitation" in lore_chosen
        assert "Arcana" in lore_chosen
        assert "Nature" in lore_chosen

    def test_generic_feature_choice_enrichment(self):
        """Test generic class and subclass choices like Divine Order."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Cleric",
            "level": 1,
            "divine_order": "Thaumaturge",
            "abilities": {
                "Strength": 14,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 10,
            },
        })

        char = builder.to_character()
        class_features = char.get("features", {}).get("class", [])
        divine_order_feat = next(
            (f for f in class_features if "Divine Order" in f["name"]),
            None,
        )
        assert divine_order_feat is not None
        assert "Thaumaturge" in divine_order_feat["name"]
        assert "chosen_options" in divine_order_feat
        assert divine_order_feat["chosen_options"][0]["name"] == "Thaumaturge"
        assert len(divine_order_feat["chosen_options"][0]["description"]) > 0
