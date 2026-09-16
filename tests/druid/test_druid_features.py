"""Tests for Druid class features and all subclasses (D&D 2024)."""

import pytest
from modules.character_builder import CharacterBuilder


# ==================== Helpers ====================


def _build_druid(level=1, subclass=None):
    """Helper to build a Druid character at a given level."""
    builder = CharacterBuilder()
    builder.set_species("Human")
    builder.set_class("Druid", level)
    if subclass and level >= 3:
        builder.set_subclass(subclass)
    return builder


def _build_full_druid(level=3, subclass=None, extra_choices=None):
    """Helper to build a full Druid character with apply_choices."""
    choices = {
        "character_name": "Test Druid",
        "level": level,
        "species": "Human",
        "class": "Druid",
        "background": "Acolyte",
        "ability_scores": {
            "Strength": 8, "Dexterity": 12, "Constitution": 14,
            "Intelligence": 13, "Wisdom": 16, "Charisma": 10,
        },
        "background_bonuses": {"Wisdom": 2, "Constitution": 1},
    }
    if subclass and level >= 3:
        choices["subclass"] = subclass
    if extra_choices:
        choices.update(extra_choices)

    builder = CharacterBuilder()
    builder.apply_choices(choices)
    return builder


def _feature_names(character_data, category="class"):
    """Extract feature names from character_data features."""
    return [f["name"] for f in character_data["features"].get(category, [])]


# ==================== Base Druid Class ====================


class TestDruidBaseClass:
    """Test base Druid class features (no subclass needed for L1-2)."""

    def test_druidic_at_level_1(self):
        """Druidic feature should be present at level 1."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Druidic" in names

    def test_druidic_grants_speak_with_animals(self):
        """Druidic should grant Speak with Animals as always prepared."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Speak with Animals" in always_prepared

    def test_spellcasting_at_level_1(self):
        """Spellcasting feature should be present at level 1."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Spellcasting" in names

    def test_primal_order_feature_at_level_1(self):
        """Primal Order feature should be present at level 1."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Primal Order" in names

    def test_primal_order_warden_grants_martial_weapons(self):
        """Choosing Warden primal order should grant Martial weapons proficiency."""
        builder = _build_full_druid(level=1, extra_choices={"primal_order": "Warden"})
        char_data = builder.character_data
        assert "Martial weapons" in char_data["proficiencies"]["weapons"]

    def test_primal_order_warden_grants_medium_armor(self):
        """Choosing Warden primal order should grant Medium armor proficiency."""
        builder = _build_full_druid(level=1, extra_choices={"primal_order": "Warden"})
        char_data = builder.character_data
        assert "Medium armor" in char_data["proficiencies"]["armor"]

    def test_wild_shape_at_level_2(self):
        """Wild Shape feature should be present at level 2."""
        builder = _build_druid(level=2)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Wild Shape" in names

    def test_wild_companion_at_level_2(self):
        """Wild Companion feature should be present at level 2."""
        builder = _build_druid(level=2)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Wild Companion" in names

    def test_wild_resurgence_at_level_5(self):
        """Wild Resurgence feature should be present at level 5."""
        builder = _build_druid(level=5)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Wild Resurgence" in names

    def test_wild_resurgence_not_at_level_4(self):
        """Wild Resurgence should NOT be present before level 5."""
        builder = _build_druid(level=4)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Wild Resurgence" not in names

    def test_elemental_fury_at_level_7(self):
        """Elemental Fury feature should be present at level 7."""
        builder = _build_druid(level=7)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Elemental Fury" in names

    def test_beast_spells_at_level_18(self):
        """Beast Spells feature should be present at level 18."""
        builder = _build_druid(level=18)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Beast Spells" in names

    def test_archdruid_at_level_20(self):
        """Archdruid feature should be present at level 20."""
        builder = _build_druid(level=20)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert "Archdruid" in names

    def test_base_armor_proficiencies(self):
        """Druid should have Light armor and Shields proficiencies."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        assert "Light armor" in char_data["proficiencies"]["armor"]
        assert "Shields" in char_data["proficiencies"]["armor"]

    def test_base_weapon_proficiencies(self):
        """Druid should have Simple weapons proficiency."""
        builder = _build_druid(level=1)
        char_data = builder.character_data
        assert "Simple weapons" in char_data["proficiencies"]["weapons"]

    @pytest.mark.parametrize(
        "level,expected_feature",
        [
            (1, "Druidic"),
            (1, "Spellcasting"),
            (1, "Primal Order"),
            (2, "Wild Shape"),
            (2, "Wild Companion"),
            (5, "Wild Resurgence"),
            (7, "Elemental Fury"),
            (18, "Beast Spells"),
            (20, "Archdruid"),
        ],
    )
    def test_feature_progression(self, level, expected_feature):
        """Verify features appear at their correct levels."""
        builder = _build_druid(level=level)
        char_data = builder.character_data
        names = _feature_names(char_data, "class")
        assert expected_feature in names, (
            f"Expected '{expected_feature}' at level {level}, got: {names}"
        )


# ==================== Circle of the Moon ====================


class TestCircleOfTheMoon:
    """Test Circle of the Moon subclass features."""

    def test_circle_forms_at_level_3(self):
        """Circle Forms feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Circle Forms" in names

    def test_circle_of_the_moon_spells_at_level_3(self):
        """Circle of the Moon Spells feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Circle of the Moon Spells" in names

    def test_moon_spells_cure_wounds_at_level_3(self):
        """Cure Wounds should be always prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Cure Wounds" in always_prepared

    def test_moon_spells_moonbeam_at_level_3(self):
        """Moonbeam should be always prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Moonbeam" in always_prepared

    def test_moon_spells_starry_wisp_cantrip(self):
        """Starry Wisp cantrip should be granted at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Starry Wisp" in always_prepared

    def test_moon_spells_conjure_animals_at_level_5(self):
        """Conjure Animals should be always prepared at level 5."""
        builder = _build_druid(level=5, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Conjure Animals" in always_prepared

    def test_moon_spells_conjure_animals_not_at_level_3(self):
        """Conjure Animals should NOT be prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Conjure Animals" not in always_prepared

    def test_moon_spells_fount_of_moonlight_at_level_7(self):
        """Fount of Moonlight should be always prepared at level 7."""
        builder = _build_druid(level=7, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fount of Moonlight" in always_prepared

    def test_moon_spells_mass_cure_wounds_at_level_9(self):
        """Mass Cure Wounds should be always prepared at level 9."""
        builder = _build_druid(level=9, subclass="Circle of the Moon")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Mass Cure Wounds" in always_prepared

    def test_improved_circle_forms_at_level_6(self):
        """Improved Circle Forms feature should be present at level 6."""
        builder = _build_druid(level=6, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Improved Circle Forms" in names

    def test_moonlight_step_at_level_10(self):
        """Moonlight Step feature should be present at level 10."""
        builder = _build_druid(level=10, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Moonlight Step" in names

    def test_lunar_form_at_level_14(self):
        """Lunar Form feature should be present at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Lunar Form" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Circle Forms", "Circle of the Moon Spells"]),
            (6, ["Improved Circle Forms"]),
            (10, ["Moonlight Step"]),
            (14, ["Lunar Form"]),
        ],
    )
    def test_moon_feature_progression(self, level, expected_features):
        """Verify Moon subclass features appear at correct levels."""
        builder = _build_druid(level=level, subclass="Circle of the Moon")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        for name in expected_features:
            assert name in names, f"Expected '{name}' at level {level}"


# ==================== Circle of the Sea ====================


class TestCircleOfTheSea:
    """Test Circle of the Sea subclass features."""

    def test_wrath_of_the_sea_at_level_3(self):
        """Wrath of the Sea feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Wrath of the Sea" in names

    def test_sea_spells_feature_at_level_3(self):
        """Circle of the Sea Spells feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Circle of the Sea Spells" in names

    def test_sea_spells_fog_cloud_at_level_3(self):
        """Fog Cloud should be always prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fog Cloud" in always_prepared

    def test_sea_spells_gust_of_wind_at_level_3(self):
        """Gust of Wind should be always prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Gust of Wind" in always_prepared

    def test_sea_spells_thunderwave_at_level_3(self):
        """Thunderwave should be always prepared at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Thunderwave" in always_prepared

    def test_sea_spells_ray_of_frost_cantrip(self):
        """Ray of Frost cantrip should be granted at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Ray of Frost" in always_prepared

    def test_sea_spells_lightning_bolt_at_level_5(self):
        """Lightning Bolt should be always prepared at level 5."""
        builder = _build_druid(level=5, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Lightning Bolt" in always_prepared

    def test_sea_spells_water_breathing_at_level_5(self):
        """Water Breathing should be always prepared at level 5."""
        builder = _build_druid(level=5, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Water Breathing" in always_prepared

    def test_sea_spells_level_5_not_at_level_3(self):
        """Level 5 spells should NOT be available at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Lightning Bolt" not in always_prepared
        assert "Water Breathing" not in always_prepared

    def test_sea_spells_control_water_at_level_7(self):
        """Control Water should be always prepared at level 7."""
        builder = _build_druid(level=7, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Control Water" in always_prepared

    def test_sea_spells_ice_storm_at_level_7(self):
        """Ice Storm should be always prepared at level 7."""
        builder = _build_druid(level=7, subclass="Circle of the Sea")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Ice Storm" in always_prepared

    def test_aquatic_affinity_at_level_6(self):
        """Aquatic Affinity feature should be present at level 6."""
        builder = _build_druid(level=6, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Aquatic Affinity" in names

    def test_stormborn_at_level_10(self):
        """Stormborn feature should be present at level 10."""
        builder = _build_druid(level=10, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Stormborn" in names

    def test_oceanic_gift_at_level_14(self):
        """Oceanic Gift feature should be present at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Oceanic Gift" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Circle of the Sea Spells", "Wrath of the Sea"]),
            (6, ["Aquatic Affinity"]),
            (10, ["Stormborn"]),
            (14, ["Oceanic Gift"]),
        ],
    )
    def test_sea_feature_progression(self, level, expected_features):
        """Verify Sea subclass features appear at correct levels."""
        builder = _build_druid(level=level, subclass="Circle of the Sea")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        for name in expected_features:
            assert name in names, f"Expected '{name}' at level {level}"


# ==================== Circle of the Stars ====================


class TestCircleOfTheStars:
    """Test Circle of the Stars subclass features."""

    def test_star_map_at_level_3(self):
        """Star Map feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Star Map" in names

    def test_star_map_grants_guiding_bolt(self):
        """Star Map should grant Guiding Bolt as always prepared."""
        builder = _build_druid(level=3, subclass="Circle of the Stars")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Guiding Bolt" in always_prepared

    def test_star_map_grants_guidance_cantrip(self):
        """Star Map should grant Guidance cantrip."""
        builder = _build_druid(level=3, subclass="Circle of the Stars")
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Guidance" in always_prepared

    def test_starry_form_at_level_3(self):
        """Starry Form feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Starry Form" in names

    def test_cosmic_omen_at_level_6(self):
        """Cosmic Omen feature should be present at level 6."""
        builder = _build_druid(level=6, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Cosmic Omen" in names

    def test_cosmic_omen_not_at_level_3(self):
        """Cosmic Omen should NOT be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Cosmic Omen" not in names

    def test_twinkling_constellations_at_level_10(self):
        """Twinkling Constellations feature should be present at level 10."""
        builder = _build_druid(level=10, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Twinkling Constellations" in names

    def test_full_of_stars_at_level_14(self):
        """Full of Stars feature should be present at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Full of Stars" in names

    def test_full_of_stars_grants_bludgeoning_resistance(self):
        """Full of Stars should grant Bludgeoning damage resistance at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Stars")
        char_data = builder.character_data
        assert "Bludgeoning" in char_data["resistances"]

    def test_full_of_stars_grants_piercing_resistance(self):
        """Full of Stars should grant Piercing damage resistance at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Stars")
        char_data = builder.character_data
        assert "Piercing" in char_data["resistances"]

    def test_full_of_stars_grants_slashing_resistance(self):
        """Full of Stars should grant Slashing damage resistance at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Stars")
        char_data = builder.character_data
        assert "Slashing" in char_data["resistances"]

    def test_no_resistances_before_level_14(self):
        """Resistances from Full of Stars should NOT appear before level 14."""
        builder = _build_druid(level=10, subclass="Circle of the Stars")
        char_data = builder.character_data
        # Human has no innate resistances
        assert "Bludgeoning" not in char_data["resistances"]
        assert "Piercing" not in char_data["resistances"]
        assert "Slashing" not in char_data["resistances"]

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Star Map", "Starry Form"]),
            (6, ["Cosmic Omen"]),
            (10, ["Twinkling Constellations"]),
            (14, ["Full of Stars"]),
        ],
    )
    def test_stars_feature_progression(self, level, expected_features):
        """Verify Stars subclass features appear at correct levels."""
        builder = _build_druid(level=level, subclass="Circle of the Stars")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        for name in expected_features:
            assert name in names, f"Expected '{name}' at level {level}"


# ==================== Circle of the Land ====================


class TestCircleOfTheLand:
    """Test Circle of the Land subclass features."""

    def test_lands_aid_at_level_3(self):
        """Land's Aid feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Land's Aid" in names

    def test_circle_of_the_land_spells_at_level_3(self):
        """Circle of the Land Spells feature should be present at level 3."""
        builder = _build_druid(level=3, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Circle of the Land Spells" in names

    def test_natural_recovery_at_level_6(self):
        """Natural Recovery feature should be present at level 6."""
        builder = _build_druid(level=6, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Natural Recovery" in names

    def test_natures_ward_at_level_10(self):
        """Nature's Ward feature should be present at level 10."""
        builder = _build_druid(level=10, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Nature's Ward" in names

    def test_natures_ward_grants_poisoned_immunity(self):
        """Nature's Ward should grant immunity to the Poisoned condition."""
        builder = _build_druid(level=10, subclass="Circle of the Land")
        char_data = builder.character_data
        assert "Poisoned" in char_data["condition_immunities"]

    def test_natures_ward_no_immunity_before_level_10(self):
        """Poisoned immunity should NOT be present before level 10."""
        builder = _build_druid(level=6, subclass="Circle of the Land")
        char_data = builder.character_data
        assert "Poisoned" not in char_data["condition_immunities"]

    def test_natures_sanctuary_at_level_14(self):
        """Nature's Sanctuary feature should be present at level 14."""
        builder = _build_druid(level=14, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        assert "Nature's Sanctuary" in names

    @pytest.mark.parametrize(
        "level,expected_features",
        [
            (3, ["Circle of the Land Spells", "Land's Aid"]),
            (6, ["Natural Recovery"]),
            (10, ["Nature's Ward"]),
            (14, ["Nature's Sanctuary"]),
        ],
    )
    def test_land_feature_progression(self, level, expected_features):
        """Verify Land subclass features appear at correct levels."""
        builder = _build_druid(level=level, subclass="Circle of the Land")
        char_data = builder.character_data
        names = _feature_names(char_data, "subclass")
        for name in expected_features:
            assert name in names, f"Expected '{name}' at level {level}"


class TestCircleOfTheLandSpells:
    """Test Circle of the Land spell effects with land_type choice."""

    def test_arid_grants_fire_bolt_cantrip(self):
        """Choosing Arid land type should grant Fire Bolt cantrip."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Arid"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fire Bolt" in always_prepared

    def test_arid_grants_level_3_spells(self):
        """Choosing Arid should grant Blur and Burning Hands at level 3."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Arid"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Blur" in always_prepared
        assert "Burning Hands" in always_prepared

    def test_arid_grants_fireball_at_level_5(self):
        """Choosing Arid should grant Fireball at level 5."""
        builder = _build_full_druid(
            level=5, subclass="Circle of the Land",
            extra_choices={"land_type": "Arid"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fireball" in always_prepared

    def test_arid_fireball_not_at_level_3(self):
        """Arid's Fireball should NOT be available at level 3."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Arid"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fireball" not in always_prepared

    def test_polar_grants_ray_of_frost_cantrip(self):
        """Choosing Polar land type should grant Ray of Frost cantrip."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Polar"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Ray of Frost" in always_prepared

    def test_polar_grants_level_3_spells(self):
        """Choosing Polar should grant Fog Cloud and Hold Person at level 3."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Polar"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Fog Cloud" in always_prepared
        assert "Hold Person" in always_prepared

    def test_temperate_grants_shocking_grasp_cantrip(self):
        """Choosing Temperate land type should grant Shocking Grasp cantrip."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Temperate"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Shocking Grasp" in always_prepared

    def test_temperate_grants_level_3_spells(self):
        """Choosing Temperate should grant Misty Step and Sleep at level 3."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Temperate"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Misty Step" in always_prepared
        assert "Sleep" in always_prepared

    def test_tropical_grants_acid_splash_cantrip(self):
        """Choosing Tropical land type should grant Acid Splash cantrip."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Tropical"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Acid Splash" in always_prepared

    def test_tropical_grants_level_3_spells(self):
        """Choosing Tropical should grant Ray of Sickness and Web at level 3."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": "Tropical"},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert "Ray of Sickness" in always_prepared
        assert "Web" in always_prepared

    @pytest.mark.parametrize(
        "land_type,cantrip",
        [
            ("Arid", "Fire Bolt"),
            ("Polar", "Ray of Frost"),
            ("Temperate", "Shocking Grasp"),
            ("Tropical", "Acid Splash"),
        ],
    )
    def test_land_type_cantrips(self, land_type, cantrip):
        """Each land type should grant its associated cantrip."""
        builder = _build_full_druid(
            level=3, subclass="Circle of the Land",
            extra_choices={"land_type": land_type},
        )
        char_data = builder.character_data
        always_prepared = char_data["spells"]["always_prepared"]
        assert cantrip in always_prepared, (
            f"Land type '{land_type}' should grant '{cantrip}', "
            f"got: {list(always_prepared.keys()) if isinstance(always_prepared, dict) else always_prepared}"
        )
