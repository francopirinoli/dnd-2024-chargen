#!/usr/bin/env python3
"""
Unit tests for the Cleric class implementation.
Tests all features, effects, and mechanics specific to the Cleric class.
"""

import pytest
from modules.character_builder import CharacterBuilder


@pytest.fixture
def cleric_builder():
    """Fixture providing a fresh CharacterBuilder for each test"""
    return CharacterBuilder()


class TestClericClass:
    """Test Cleric class implementation"""

    def test_cleric_basic_setup(self, cleric_builder):
        """Test basic cleric character creation"""
        # Create level 1 cleric
        assert cleric_builder.set_species("Human") is True
        assert cleric_builder.set_class("Cleric", 1) is True

        char_data = cleric_builder.character_data

        # Check basic class properties
        assert char_data["class"] == "Cleric"
        assert char_data["level"] == 1

        # Check proficiencies
        saving_throws = char_data["proficiencies"]["saving_throws"]
        assert "Wisdom" in saving_throws
        assert "Charisma" in saving_throws

        armor_profs = char_data["proficiencies"]["armor"]
        assert "Light armor" in armor_profs
        assert "Medium armor" in armor_profs
        assert "Shields" in armor_profs

        weapon_profs = char_data["proficiencies"]["weapons"]
        assert "Simple weapons" in weapon_profs

    def test_cleric_spellcasting_feature(self, cleric_builder):
        """Test that Spellcasting feature is added correctly"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 1)

        char_data = cleric_builder.character_data
        class_features = char_data["features"]["class"]

        # Find spellcasting feature
        spellcasting_feature = None
        for feature in class_features:
            if feature["name"] == "Spellcasting":
                spellcasting_feature = feature
                break

        assert spellcasting_feature is not None
        assert "spellcasting ability" in spellcasting_feature["description"].lower()

    def test_divine_order_choice(self, cleric_builder):
        """Test Divine Order choice application"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 1)

        # Test Protector choice
        protector_success = cleric_builder.apply_choice("divine_order", "Protector")
        assert protector_success is True

        char_data = cleric_builder.character_data

        # Check that Protector effects are applied
        weapon_profs = char_data["proficiencies"]["weapons"]
        assert "Martial weapons" in weapon_profs

        armor_profs = char_data["proficiencies"]["armor"]
        assert "Heavy armor" in armor_profs

        # Test Thaumaturge choice (reset and try)
        cleric_builder = CharacterBuilder()
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 1)

        # Test that we can make the Divine Order choice for Thaumaturge
        thaumaturge_success = cleric_builder.apply_choice("Divine Order", "Thaumaturge")
        assert thaumaturge_success is True

        char_data = cleric_builder.character_data

        # Check that the choice was recorded
        choices_made = char_data.get("choices_made", {})
        assert choices_made.get("Divine Order") == "Thaumaturge"

        # Check for Intelligence bonus to Arcana/Religion (ability_bonus effect)
        ability_bonuses = char_data.get("ability_bonuses", [])
        intelligence_bonus = None
        for bonus in ability_bonuses:
            if bonus.get("ability") == "Intelligence" and "Arcana" in bonus.get(
                "skills", []
            ):
                intelligence_bonus = bonus
                break

        assert intelligence_bonus is not None, (
            "Thaumaturge should grant Intelligence bonus to Arcana and Religion"
        )
        assert "Arcana" in intelligence_bonus["skills"]
        assert "Religion" in intelligence_bonus["skills"]
        assert intelligence_bonus["value"] == "wisdom_modifier"
        assert intelligence_bonus["minimum"] == 1

    def test_channel_divinity_scaling(self, cleric_builder):
        """Test Channel Divinity feature scaling at different levels"""
        cleric_builder.set_species("Human")

        # Test at level 2 (when Channel Divinity is gained)
        cleric_builder.set_class("Cleric", 2)
        char_data = cleric_builder.character_data

        class_features = char_data["features"]["class"]
        channel_divinity = None
        for feature in class_features:
            if "Channel Divinity" in feature["name"]:
                channel_divinity = feature
                break

        assert channel_divinity is not None
        description = channel_divinity["description"]

        # At level 2, should show "1d8" and "2" uses
        assert "1d8" in description
        assert "2" in description

        # Test at level 7 (Divine Spark should scale)
        cleric_builder.set_class("Cleric", 7)
        char_data = cleric_builder.character_data

        class_features = char_data["features"]["class"]
        channel_divinity = None
        for feature in class_features:
            if "Channel Divinity" in feature["name"]:
                channel_divinity = feature
                break

        assert channel_divinity is not None
        description = channel_divinity["description"]

        # At level 7, should show "2d8" for Divine Spark
        assert "2d8" in description

        # Test at level 18 (max scaling)
        cleric_builder.set_class("Cleric", 18)
        char_data = cleric_builder.character_data

        class_features = char_data["features"]["class"]
        channel_divinity = None
        for feature in class_features:
            if "Channel Divinity" in feature["name"]:
                channel_divinity = feature
                break

        assert channel_divinity is not None
        description = channel_divinity["description"]

        # At level 18, should show "4d8" for Divine Spark and "4" uses
        assert "4d8" in description
        # Uses should be 4 at level 18
        assert "4" in description

    def test_blessed_strikes_choice_system(self, cleric_builder):
        """Test Blessed Strikes choice at level 7"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 7)

        # Apply Divine Strike choice
        divine_strike_success = cleric_builder.apply_choice(
            "blessed_strikes", "Divine Strike"
        )
        assert divine_strike_success is True

        char_data = cleric_builder.character_data
        choices = char_data["choices_made"]
        assert choices.get("blessed_strikes") == "Divine Strike"

        # Test Potent Spellcasting choice (reset and try)
        cleric_builder = CharacterBuilder()
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 7)

        potent_success = cleric_builder.apply_choice(
            "blessed_strikes", "Potent Spellcasting"
        )
        assert potent_success is True

        char_data = cleric_builder.character_data
        choices = char_data["choices_made"]
        assert choices.get("blessed_strikes") == "Potent Spellcasting"

    @pytest.mark.parametrize(
        "level,expected_dice",
        [(7, "1d8"), (10, "1d8"), (13, "1d8"), (14, "2d8"), (17, "2d8"), (20, "2d8")],
    )
    def test_divine_strike_scaling(self, cleric_builder, level, expected_dice):
        """Test Divine Strike damage scaling from 1d8 to 2d8 at level 14"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", level)

        # Apply Divine Strike choice
        divine_strike_success = cleric_builder.apply_choice(
            "blessed_strikes", "Divine Strike"
        )
        assert divine_strike_success is True

        char_data = cleric_builder.character_data
        class_features = char_data["features"]["class"]

        # Find the Divine Strike feature in character's class features
        divine_strike_feature = None
        for feature in class_features:
            if "Blessed Strikes: Divine Strike" in feature["name"]:
                divine_strike_feature = feature
                break

        assert divine_strike_feature is not None, (
            f"Divine Strike feature not found at level {level}"
        )

        # Check that the description contains the expected dice value
        description = divine_strike_feature["description"]
        assert expected_dice in description, (
            f"Expected {expected_dice} in Divine Strike description at level {level}, got: {description}"
        )

    @pytest.mark.parametrize(
        "level,has_temp_hp",
        [(7, False), (10, False), (13, False), (14, True), (17, True), (20, True)],
    )
    def test_potent_spellcasting_scaling(self, cleric_builder, level, has_temp_hp):
        """Test Potent Spellcasting enhancement at level 14"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", level)

        # Apply Potent Spellcasting choice
        potent_success = cleric_builder.apply_choice(
            "blessed_strikes", "Potent Spellcasting"
        )
        assert potent_success is True

        char_data = cleric_builder.character_data
        class_features = char_data["features"]["class"]

        # Find the Potent Spellcasting feature in character's class features
        potent_feature = None
        for feature in class_features:
            if "Blessed Strikes: Potent Spellcasting" in feature["name"]:
                potent_feature = feature
                break

        assert potent_feature is not None, (
            f"Potent Spellcasting feature not found at level {level}"
        )

        # Check that the description contains the base effect
        description = potent_feature["description"]
        assert "Add your Wisdom modifier to the damage" in description

        # Check for the level 14+ temporary hit points feature
        if has_temp_hp:
            assert "Temporary Hit Points" in description, (
                f"Expected temporary HP feature at level {level}, got: {description}"
            )
            assert "twice your Wisdom modifier" in description
        else:
            assert "Temporary Hit Points" not in description, (
                f"Should not have temporary HP feature at level {level}, got: {description}"
            )

    @pytest.mark.parametrize(
        "level,expected_prepared,expected_cantrips",
        [(1, 4, 3), (5, 9, 4), (9, 14, 4), (17, 19, 5), (20, 22, 5)],
    )
    def test_cleric_spell_progression(
        self, level, expected_prepared, expected_cantrips
    ):
        """Test cleric spell slot and prepared spell progression"""
        cleric_builder = CharacterBuilder()
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", level)

        class_data = cleric_builder.character_data.get("class_data", {})

        # Check prepared spells
        prepared_spells = class_data.get("prepared_spells_by_level", {})
        actual_prepared = prepared_spells.get(str(level), 0)
        assert actual_prepared == expected_prepared

        # Check cantrips
        cantrips = class_data.get("cantrips_by_level", {})
        actual_cantrips = cantrips.get(str(level), 0)
        assert actual_cantrips == expected_cantrips

    def test_subclass_integration(self, cleric_builder):
        """Test that subclasses integrate properly with cleric class"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 3)  # Level 3 for subclass selection

        # Test Life Domain
        assert cleric_builder.set_subclass("Life Domain") is True

        char_data = cleric_builder.character_data
        assert char_data["subclass"] == "Life Domain"

        # Check that subclass integration works
        subclass_features = char_data["features"]["subclass"]
        assert len(subclass_features) > 0


class TestClericFeatureEffects:
    """Test cleric feature effects system integration"""

    def test_effect_application(self, cleric_builder):
        """Test that effects are properly applied"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 1)

        # Apply Divine Order choice
        cleric_builder.apply_choice("divine_order", "Protector")

        # Check applied effects
        applied_effects = getattr(cleric_builder, "applied_effects", [])

        # Should have weapon proficiency effect
        weapon_effect = None
        for effect in applied_effects:
            if effect.get("type") == "grant_weapon_proficiency":
                weapon_effect = effect
                break

        assert weapon_effect is not None

        # Should have armor proficiency effect
        armor_effect = None
        for effect in applied_effects:
            if effect.get("type") == "grant_armor_proficiency":
                armor_effect = effect
                break

        assert armor_effect is not None

    def test_spell_effects_integration(self, cleric_builder):
        """Test spell granting effects from domain features"""
        cleric_builder.set_species("Human")
        cleric_builder.set_class("Cleric", 3)
        cleric_builder.set_subclass("Life Domain")

        char_data = cleric_builder.character_data

        # Check that grant_spell effects were applied
        applied_effects = getattr(cleric_builder, "applied_effects", [])

        spell_effects = [e for e in applied_effects if e.get("type") == "grant_spell"]
        assert len(spell_effects) > 0

        # Verify spells are in always_prepared dict (domain spells)
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Bless" in always_prepared
        assert "Cure Wounds" in always_prepared


class TestCleric2024Audit:
    """Comprehensive tests for the 2024 RAW Cleric class audit and upgrades."""

    def test_cleric_progression_tables(self, cleric_builder):
        """Verify progression tables in cleric.json."""
        cleric_builder.set_class("Cleric", 1)
        cd_uses = cleric_builder.character_data["class_data"].get("channel_divinity_uses_by_level", {})
        spark_dice = cleric_builder.character_data["class_data"].get("divine_spark_dice_by_level", {})

        assert cd_uses["2"] == 2
        assert cd_uses["6"] == 3
        assert cd_uses["18"] == 4

        assert spark_dice["2"] == "1d8"
        assert spark_dice["7"] == "2d8"
        assert spark_dice["13"] == "3d8"
        assert spark_dice["18"] == "4d8"

    def test_cleric_stats_calculation(self):
        """Test calculate_cleric_stats at multiple levels."""
        # Level 1
        b1 = CharacterBuilder()
        b1.set_class("Cleric", 1)
        b1.apply_choice("divine_order", "Protector")
        s1 = b1.calculate_cleric_stats()
        assert s1["cleric_level"] == 1
        assert s1["has_channel_divinity"] is False
        assert s1["divine_order"]["name"] == "Protector"

        # Level 2
        b2 = CharacterBuilder()
        b2.set_class("Cleric", 2)
        s2 = b2.calculate_cleric_stats()
        assert s2["has_channel_divinity"] is True
        assert s2["channel_divinity_max"] == 2
        assert s2["divine_spark_dice"] == "1d8"
        assert s2["sear_undead"] is False

        # Level 5
        b5 = CharacterBuilder()
        b5.set_class("Cleric", 5)
        s5 = b5.calculate_cleric_stats()
        assert s5["sear_undead"] is True

        # Level 6
        b6 = CharacterBuilder()
        b6.set_class("Cleric", 6)
        s6 = b6.calculate_cleric_stats()
        assert s6["channel_divinity_max"] == 3

        # Level 7
        b7 = CharacterBuilder()
        b7.set_class("Cleric", 7)
        b7.apply_choice("blessed_strikes", "Divine Strike")
        s7 = b7.calculate_cleric_stats()
        assert s7["divine_spark_dice"] == "2d8"
        assert s7["blessed_strikes"]["name"] == "Divine Strike"
        assert s7["blessed_strikes"]["dice"] == "1d8"

        # Level 10
        b10 = CharacterBuilder()
        b10.set_class("Cleric", 10)
        s10 = b10.calculate_cleric_stats()
        assert s10["divine_intervention"] is True
        assert s10["greater_divine_intervention"] is False

        # Level 14
        b14 = CharacterBuilder()
        b14.set_class("Cleric", 14)
        b14.apply_choice("blessed_strikes", "Divine Strike")
        s14 = b14.calculate_cleric_stats()
        assert s14["blessed_strikes"]["dice"] == "2d8"

        # Level 18
        b18 = CharacterBuilder()
        b18.set_class("Cleric", 18)
        s18 = b18.calculate_cleric_stats()
        assert s18["channel_divinity_max"] == 4
        assert s18["divine_spark_dice"] == "4d8"

        # Level 20
        b20 = CharacterBuilder()
        b20.set_class("Cleric", 20)
        s20 = b20.calculate_cleric_stats()
        assert s20["greater_divine_intervention"] is True

    def test_cleric_level_19_epic_boon_structure(self, cleric_builder):
        """Test that Level 19 Epic Boon is a structured ASI/feat choice slot."""
        cleric_builder.set_class("Cleric", 19)
        class_data = cleric_builder.character_data["class_data"]
        boon_feature = class_data["features_by_level"]["19"]["Epic Boon"]
        assert isinstance(boon_feature, dict)
        assert boon_feature["choices"]["name"] == "class_feat_19"
        assert boon_feature["feature_kind"] == "asi"

    def test_divine_strike_weapon_attack_notes(self):
        """Test that Divine Strike adds damage notes to weapon attacks."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Cleric", 7)
        builder.apply_choice("divine_order", "Protector")
        builder.apply_choice("blessed_strikes", "Divine Strike")
        builder.character_data["equipment"] = {"weapons": [{"name": "Mace"}]}

        char = builder.to_character()
        attacks = char.get("attacks", [])
        mace_attack = next((a for a in attacks if a["name"] == "Mace"), None)
        assert mace_attack is not None
        assert any("Divine Strike" in note for note in mace_attack.get("damage_notes", []))

    def test_subclass_knowledge_domain_choices_and_effects(self):
        """Test Knowledge Domain choices for Artisan's Tool and skills with expertise."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Knowledge Domain")

        # Apply Artisan tool and skills choices
        builder.apply_choice("subclass_Blessings of Knowledge_artisan_tool", "Alchemist's Supplies")
        builder.apply_choice("subclass_Blessings of Knowledge_knowledge_skills", ["Arcana", "History"])

        char = builder.to_character()
        assert "Alchemist's Supplies" in char["proficiencies"]["tools"]
        assert "Arcana" in char["proficiencies"]["skills"]
        assert "History" in char["proficiencies"]["skills"]
        assert "Arcana" in char.get("skill_expertise", [])
        assert "History" in char.get("skill_expertise", [])

        # Subclass spells granted
        always_prep = char["spells"]["always_prepared"]
        assert "Command" in always_prep
        assert "Identify" in always_prep

        # Check Unfettered Mind at level 6 grants Intelligence save proficiency
        builder_lv6 = CharacterBuilder()
        builder_lv6.set_species("Human")
        builder_lv6.set_class("Cleric", 6)
        builder_lv6.set_subclass("Knowledge Domain")
        builder_lv6.apply_choice("subclass_Blessings of Knowledge_artisan_tool", "Alchemist's Supplies")
        builder_lv6.apply_choice("subclass_Blessings of Knowledge_knowledge_skills", ["Arcana", "History"])
        char6 = builder_lv6.to_character()
        assert "Intelligence" in char6["proficiencies"]["saving_throws"]

    def test_subclass_grave_domain_circle_of_mortality(self):
        """Test Grave Domain Circle of Mortality grants Spare the Dying."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Grave Domain")
        char = builder.to_character()

        cantrips = [c["name"] for c in char["spells"]["cantrips"]]
        assert "Spare the Dying" in cantrips

    def test_subclass_pestilence_domain_resistances(self):
        """Test Pestilence Domain Blight Weaver grants Necrotic and Poison resistance."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Pestilence Domain")
        char = builder.to_character()

        resistances = char.get("resistances", [])
        assert "Necrotic" in resistances
        assert "Poison" in resistances

    def test_subclass_freedom_domain_ac_and_skills(self):
        """Test Freedom Domain Unencumbered Grace alternative AC and Acrobatics."""
        builder = CharacterBuilder()
        builder.set_species("Human")
        builder.set_class("Cleric", 3)
        builder.set_subclass("Freedom Domain")
        char = builder.to_character()

        assert "Acrobatics" in char["proficiencies"]["skills"]
        # Verify alternative AC option recorded
        ac_options = builder.character_data.get("alternative_ac_options", [])
        freedom_ac = next((opt for opt in ac_options if opt.get("source") == "Unencumbered Grace"), None)
        assert freedom_ac is not None
        assert "wisdom" in freedom_ac.get("modifiers", [])

    def test_cleric_level_up_preview(self):
        """Test level up preview cleric_changes."""
        from modules.derived_stats import build_level_up_preview

        choices = {
            "character_name": "Eldrin",
            "level": 5,
            "species": "Human",
            "class": "Cleric",
            "background": "Acolyte",
            "divine_order": "Protector",
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 10,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 16,
                "Charisma": 12,
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1},
        }

        # Level 5 -> 6: Channel Divinity uses increase from 2 to 3
        preview = build_level_up_preview(choices)
        cleric_changes = preview.get("cleric_changes", {})
        assert cleric_changes["is_cleric"] is True
        assert cleric_changes["has_channel_divinity"] is True
        assert cleric_changes["current_cd_uses"] == 2
        assert cleric_changes["next_cd_uses"] == 3
        assert cleric_changes["cd_uses_increased"] is True
