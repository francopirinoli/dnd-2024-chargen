"""Tests for D&D 2024 origin and general feats — data completeness, builder integration, effects, and choices."""

import json
import pytest
from pathlib import Path

from modules.character_builder import CharacterBuilder


DATA_DIR = Path(__file__).parent.parent / "data"

# ==================== Expected feat lists ====================

ALL_ORIGIN_FEATS = [
    "Alert", "Crafter", "Healer", "Lucky",
    "Magic Initiate (Cleric)", "Magic Initiate (Druid)", "Magic Initiate (Wizard)",
    "Musician", "Savage Attacker", "Skilled", "Tavern Brawler", "Tough",
]

ALL_GENERAL_FEATS = [
    "Ability Score Improvement", "Actor", "Athlete", "Charger", "Chef",
    "Crossbow Expert", "Crusher", "Defensive Duelist", "Dual Wielder", "Durable",
    "Elemental Adept", "Fey Touched", "Grappler", "Great Weapon Master",
    "Heavily Armored", "Heavy Armor Master", "Inspiring Leader", "Keen Mind",
    "Lightly Armored", "Lucky", "Mage Slayer", "Martial Weapon Training",
    "Medium Armor Master", "Moderately Armored", "Mounted Combatant", "Observant",
    "Piercer", "Poisoner", "Polearm Master", "Resilient", "Ritual Caster",
    "Sentinel", "Shadow Touched", "Sharpshooter", "Shield Master", "Skill Expert",
    "Skulker", "Slasher", "Speedy", "Spell Sniper", "Telekinetic", "Telepathic",
    "War Caster", "Weapon Master",
]

ABILITY_CHOICE_GENERAL_FEATS = [
    "Athlete", "Charger", "Chef", "Crusher", "Elemental Adept", "Fey Touched",
    "Grappler", "Heavily Armored", "Heavy Armor Master", "Inspiring Leader",
    "Lightly Armored", "Mage Slayer", "Martial Weapon Training", "Medium Armor Master",
    "Moderately Armored", "Mounted Combatant", "Piercer", "Poisoner", "Ritual Caster",
    "Shadow Touched", "Slasher", "Speedy", "Spell Sniper", "Telekinetic", "Telepathic",
    "Weapon Master",
]

REQUIRED_FEAT_FIELDS = ["description", "benefits", "category", "prerequisite", "source"]


# ==================== Fixtures ====================


@pytest.fixture(scope="module")
def origin_feats():
    with open(DATA_DIR / "origin_feats.json") as f:
        return json.load(f)["origin_feats"]


@pytest.fixture(scope="module")
def general_feats():
    with open(DATA_DIR / "general_feats.json") as f:
        return json.load(f)["general_feats"]


# ==================== 1. Data Completeness Tests ====================


class TestOriginFeatsData:
    """Verify origin_feats.json has all expected feats with required structure."""

    def test_origin_feats_all_present(self, origin_feats):
        """All 12 origin feats must exist."""
        for feat_name in ALL_ORIGIN_FEATS:
            assert feat_name in origin_feats, f"Missing origin feat: {feat_name}"
        assert len(origin_feats) == len(ALL_ORIGIN_FEATS)

    @pytest.mark.parametrize("feat_name", ALL_ORIGIN_FEATS)
    def test_origin_feats_required_fields(self, origin_feats, feat_name):
        """Each origin feat must have description, benefits, category, prerequisite, source."""
        feat = origin_feats[feat_name]
        for field in REQUIRED_FEAT_FIELDS:
            assert field in feat, f"{feat_name} missing field: {field}"

    @pytest.mark.parametrize("feat_name", ALL_ORIGIN_FEATS)
    def test_origin_feats_category(self, origin_feats, feat_name):
        """All origin feats must have category 'Origin'."""
        assert origin_feats[feat_name]["category"] == "Origin"

    @pytest.mark.parametrize("feat_name", ALL_ORIGIN_FEATS)
    def test_origin_feats_source(self, origin_feats, feat_name):
        """All origin feats must have source 'Player's Handbook 2024'."""
        assert origin_feats[feat_name]["source"] == "Player's Handbook 2024"

    @pytest.mark.parametrize("feat_name", ALL_ORIGIN_FEATS)
    def test_origin_feats_no_prerequisite(self, origin_feats, feat_name):
        """Origin feats have no level prerequisite."""
        assert origin_feats[feat_name]["prerequisite"] == "None"


class TestGeneralFeatsData:
    """Verify general_feats.json has all expected feats with required structure."""

    def test_general_feats_all_present(self, general_feats):
        """All 44 general feats must exist."""
        for feat_name in ALL_GENERAL_FEATS:
            assert feat_name in general_feats, f"Missing general feat: {feat_name}"
        assert len(general_feats) == len(ALL_GENERAL_FEATS)

    @pytest.mark.parametrize("feat_name", ALL_GENERAL_FEATS)
    def test_general_feats_required_fields(self, general_feats, feat_name):
        """Each general feat must have description, benefits, category, prerequisite, source."""
        feat = general_feats[feat_name]
        for field in REQUIRED_FEAT_FIELDS:
            assert field in feat, f"{feat_name} missing field: {field}"

    @pytest.mark.parametrize("feat_name", ALL_GENERAL_FEATS)
    def test_general_feats_category(self, general_feats, feat_name):
        """All general feats must have category 'General'."""
        assert general_feats[feat_name]["category"] == "General"

    @pytest.mark.parametrize("feat_name", ALL_GENERAL_FEATS)
    def test_general_feats_source(self, general_feats, feat_name):
        """All general feats must have source 'Player's Handbook 2024'."""
        assert general_feats[feat_name]["source"] == "Player's Handbook 2024"

    @pytest.mark.parametrize("feat_name", ABILITY_CHOICE_GENERAL_FEATS)
    def test_ability_choice_feats_have_ability_bonus_choice_effects(
        self, general_feats, feat_name
    ):
        """Ability-choice feats must map each option to a +1 ability_bonus effect."""
        feat = general_feats[feat_name]
        ability_choice = next(
            (c for c in feat["choices"] if c.get("name") == "ability"), None
        )
        assert ability_choice is not None, f"{feat_name} is missing ability choice"
        options = ability_choice["source"]["options"]
        ability_effects = feat["choice_effects"]["ability"]

        for ability in options:
            assert ability in ability_effects
            assert ability_effects[ability] == [
                {"type": "ability_bonus", "ability": ability, "value": 1}
            ]


class TestFeatSourceConsistency:
    """All feats (origin + general) must share PLayers Handbook 2024 source."""

    def test_all_feats_source(self, origin_feats, general_feats):
        """Every single feat should have source 'Player's Handbook 2024'."""
        all_feats = {**origin_feats, **general_feats}
        for name, feat in all_feats.items():
            assert feat["source"] == "Player's Handbook 2024", (
                f"{name} has unexpected source: {feat['source']}"
            )


# ==================== 2. Builder Integration Tests ====================


class TestFeatDataLoading:
    """Verify CharacterBuilder._load_feat_data returns data for all feats."""

    @pytest.mark.parametrize("feat_name", ALL_ORIGIN_FEATS)
    def test_load_origin_feat(self, feat_name):
        """Builder can load each origin feat by name."""
        builder = CharacterBuilder()
        data = builder._load_feat_data(feat_name)
        assert data is not None, f"_load_feat_data returned None for '{feat_name}'"
        assert data["category"] == "Origin"

    @pytest.mark.parametrize("feat_name", ALL_GENERAL_FEATS)
    def test_load_general_feat(self, feat_name):
        """Builder can load each general feat by name."""
        builder = CharacterBuilder()
        data = builder._load_feat_data(feat_name)
        assert data is not None, f"_load_feat_data returned None for '{feat_name}'"
        # "Lucky" exists in both origin and general; _load_feat_data returns origin first
        if feat_name in ALL_ORIGIN_FEATS:
            assert data["category"] in ("Origin", "General")
        else:
            assert data["category"] == "General"

    def test_load_nonexistent_feat(self):
        """Unknown feat name returns None."""
        builder = CharacterBuilder()
        assert builder._load_feat_data("Nonexistent Feat") is None


# Background → feat mappings for parametrize
BACKGROUND_FEAT_PAIRS = [
    ("Acolyte", "Magic Initiate (Cleric)"),
    ("Artisan", "Crafter"),
    ("Charlatan", "Skilled"),
    ("Criminal", "Alert"),
    ("Entertainer", "Musician"),
    ("Farmer", "Tough"),
    ("Folk Hero", "Tough"),
    ("Guard", "Alert"),
    ("Guide", "Magic Initiate (Druid)"),
    ("Guild Artisan", "Crafter"),
    ("Hermit", "Healer"),
    ("Merchant", "Lucky"),
    ("Noble", "Skilled"),
    ("Sage", "Magic Initiate (Wizard)"),
    ("Sailor", "Tavern Brawler"),
    ("Scribe", "Skilled"),
    ("Soldier", "Savage Attacker"),
    ("Wayfarer", "Lucky"),
]


class TestOriginFeatFromBackground:
    """Origin feats are granted via backgrounds; verify they appear in character feats."""

    @pytest.mark.parametrize("background,expected_feat", BACKGROUND_FEAT_PAIRS)
    def test_origin_feat_from_background(self, built_character, background, expected_feat):
        """Setting a background adds the correct origin feat to character feats."""
        character = built_character({
            "character_name": "Feat Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": background,
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        feat_names = [f["name"] for f in character["features"]["feats"]]
        assert expected_feat in feat_names, (
            f"Background '{background}' should grant feat '{expected_feat}', "
            f"but feats are: {feat_names}"
        )

    @pytest.mark.parametrize("background,expected_feat", BACKGROUND_FEAT_PAIRS)
    def test_feat_has_source(self, built_character, background, expected_feat):
        """Feat entry should record the background as its source."""
        character = built_character({
            "character_name": "Source Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": background,
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        feat_entry = next(
            (f for f in character["features"]["feats"] if f["name"] == expected_feat),
            None,
        )
        assert feat_entry is not None
        assert feat_entry["source"] == background

    @pytest.mark.parametrize("background,expected_feat", BACKGROUND_FEAT_PAIRS)
    def test_feat_has_description(self, built_character, background, expected_feat):
        """Feat entry should have a non-empty description."""
        character = built_character({
            "character_name": "Desc Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": background,
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        feat_entry = next(
            (f for f in character["features"]["feats"] if f["name"] == expected_feat),
            None,
        )
        assert feat_entry is not None
        assert len(feat_entry["description"]) > 0


class TestToughFeatHP:
    """Tough feat should add 2 * level to HP."""

    def _build_fighter(self, background, level):
        """Helper: build a level N Human Fighter with given background."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "HP Test",
            "level": level,
            "species": "Human",
            "class": "Fighter",
            "background": background,
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        return builder.to_character()

    def test_tough_feat_present(self):
        """Farmer background grants Tough feat."""
        char = self._build_fighter("Farmer", 1)
        feat_names = [f["name"] for f in char["features"]["feats"]]
        assert "Tough" in feat_names

    def test_tough_feat_hp_bonus_level_1(self):
        """At level 1, Tough should add 2 HP (2 * 1 = 2). Regression test for #10."""
        tough_char = self._build_fighter("Farmer", 1)
        no_tough_char = self._build_fighter("Criminal", 1)
        tough_hp = tough_char["combat"]["hit_points"]["maximum"]
        normal_hp = no_tough_char["combat"]["hit_points"]["maximum"]
        # Tough should add 2 HP at level 1
        assert tough_hp == normal_hp + 2, (
            f"Tough HP {tough_hp} should be {normal_hp} + 2 = {normal_hp + 2}"
        )

    def test_tough_feat_hp_bonus_level_5(self):
        """At level 5, Tough should add 10 HP (2 * 5 = 10). Regression test for #10."""
        tough_char = self._build_fighter("Farmer", 5)
        no_tough_char = self._build_fighter("Criminal", 5)
        tough_hp = tough_char["combat"]["hit_points"]["maximum"]
        normal_hp = no_tough_char["combat"]["hit_points"]["maximum"]
        assert tough_hp == normal_hp + 10, (
            f"Tough HP {tough_hp} should be {normal_hp} + 10 = {normal_hp + 10}"
        )


# ==================== 3. Effects Tests ====================


class TestGeneralFeatEffects:
    """Feats with effects arrays should contain the correct effect definitions."""

    def test_lightly_armored_effects(self, general_feats):
        """Lightly Armored grants Light armor and Shields proficiency."""
        effects = general_feats["Lightly Armored"]["effects"]
        armor_effects = [e for e in effects if e["type"] == "grant_armor_proficiency"]
        assert len(armor_effects) == 1
        assert "Light armor" in armor_effects[0]["proficiencies"]
        assert "Shields" in armor_effects[0]["proficiencies"]

    def test_heavily_armored_effects(self, general_feats):
        """Heavily Armored grants Heavy armor proficiency."""
        effects = general_feats["Heavily Armored"]["effects"]
        armor_effects = [e for e in effects if e["type"] == "grant_armor_proficiency"]
        assert len(armor_effects) == 1
        assert "Heavy armor" in armor_effects[0]["proficiencies"]

    def test_moderately_armored_effects(self, general_feats):
        """Moderately Armored grants Medium armor proficiency."""
        effects = general_feats["Moderately Armored"]["effects"]
        armor_effects = [e for e in effects if e["type"] == "grant_armor_proficiency"]
        assert len(armor_effects) == 1
        assert "Medium armor" in armor_effects[0]["proficiencies"]

    def test_martial_weapon_training_effects(self, general_feats):
        """Martial Weapon Training grants Martial weapons proficiency."""
        effects = general_feats["Martial Weapon Training"]["effects"]
        weapon_effects = [e for e in effects if e["type"] == "grant_weapon_proficiency"]
        assert len(weapon_effects) == 1
        assert "Martial weapons" in weapon_effects[0]["proficiencies"]

    def test_speedy_effects(self, general_feats):
        """Speedy increases speed by 10."""
        effects = general_feats["Speedy"]["effects"]
        speed_effects = [e for e in effects if e["type"] == "increase_speed"]
        assert len(speed_effects) == 1
        assert speed_effects[0]["value"] == 10

    def test_telekinetic_effects(self, general_feats):
        """Telekinetic grants Mage Hand cantrip."""
        effects = general_feats["Telekinetic"]["effects"]
        cantrip_effects = [e for e in effects if e["type"] == "grant_cantrip"]
        assert len(cantrip_effects) == 1
        assert cantrip_effects[0]["spell"] == "Mage Hand"

    def test_fey_touched_effects(self, general_feats):
        """Fey Touched grants Misty Step spell."""
        effects = general_feats["Fey Touched"]["effects"]
        spell_effects = [e for e in effects if e["type"] == "grant_spell"]
        assert len(spell_effects) == 1
        assert spell_effects[0]["spell"] == "Misty Step"

    def test_shadow_touched_effects(self, general_feats):
        """Shadow Touched grants Invisibility spell."""
        effects = general_feats["Shadow Touched"]["effects"]
        spell_effects = [e for e in effects if e["type"] == "grant_spell"]
        assert len(spell_effects) == 1
        assert spell_effects[0]["spell"] == "Invisibility"

    def test_telepathic_effects(self, general_feats):
        """Telepathic grants Detect Thoughts spell."""
        effects = general_feats["Telepathic"]["effects"]
        spell_effects = [e for e in effects if e["type"] == "grant_spell"]
        assert len(spell_effects) == 1
        assert spell_effects[0]["spell"] == "Detect Thoughts"

    def test_actor_effects(self, general_feats):
        """Actor grants Charisma +1."""
        effects = general_feats["Actor"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Charisma"
        assert ability_effects[0]["value"] == 1

    def test_crossbow_expert_effects(self, general_feats):
        """Crossbow Expert grants Dexterity +1."""
        effects = general_feats["Crossbow Expert"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Dexterity"
        assert ability_effects[0]["value"] == 1

    def test_defensive_duelist_effects(self, general_feats):
        """Defensive Duelist grants Dexterity +1."""
        effects = general_feats["Defensive Duelist"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Dexterity"
        assert ability_effects[0]["value"] == 1

    def test_durable_effects(self, general_feats):
        """Durable grants Constitution +1."""
        effects = general_feats["Durable"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Constitution"
        assert ability_effects[0]["value"] == 1

    def test_keen_mind_effects(self, general_feats):
        """Keen Mind grants Intelligence +1."""
        effects = general_feats["Keen Mind"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Intelligence"
        assert ability_effects[0]["value"] == 1

    def test_shield_master_effects(self, general_feats):
        """Shield Master grants Strength +1."""
        effects = general_feats["Shield Master"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Strength"
        assert ability_effects[0]["value"] == 1

    def test_skulker_effects(self, general_feats):
        """Skulker grants Dexterity +1."""
        effects = general_feats["Skulker"]["effects"]
        ability_effects = [e for e in effects if e["type"] == "ability_bonus"]
        assert len(ability_effects) == 1
        assert ability_effects[0]["ability"] == "Dexterity"
        assert ability_effects[0]["value"] == 1

    def test_chef_effects(self, general_feats):
        """Chef grants Cook's Utensils proficiency."""
        effects = general_feats["Chef"]["effects"]
        tool_effects = [e for e in effects if e["type"] == "grant_tool_proficiency"]
        assert len(tool_effects) == 1
        assert "Cook's Utensils" in tool_effects[0]["tools"]

    def test_poisoner_effects(self, general_feats):
        """Poisoner grants Poisoner's Kit proficiency."""
        effects = general_feats["Poisoner"]["effects"]
        tool_effects = [e for e in effects if e["type"] == "grant_tool_proficiency"]
        assert len(tool_effects) == 1
        assert "Poisoner's Kit" in tool_effects[0]["tools"]


class TestOriginFeatEffects:
    class TestMagicInitiateAlwaysPrepared:
        """Magic Initiate (Wizard): granted spells/cantrips are always prepared."""

        def _build_magic_initiate_wizard(self, cantrips, spell):
            """Helper: build a level 1 Human Fighter with Magic Initiate (Wizard) feat and chosen spells."""
            builder = CharacterBuilder()
            builder.apply_choices({
                "character_name": "MI Wizard Test",
                "level": 1,
                "species": "Human",
                "class": "Fighter",
                "background": "Sage",  # Sage grants Magic Initiate (Wizard)
                "ability_scores": {
                    "Strength": 10, "Dexterity": 10, "Constitution": 10,
                    "Intelligence": 16, "Wisdom": 10, "Charisma": 10
                },
                "background_bonuses": {"Intelligence": 2, "Constitution": 1},
                # Use namespaced feat-choice keys (the actual format sent by the wizard)
                "feat_Magic Initiate (Wizard)_cantrips": cantrips,
                "feat_Magic Initiate (Wizard)_1st_level_spell": spell,
            })
            return builder.to_character()

        def test_magic_initiate_wizard_spells_always_prepared(self):
            """Spells/cantrips from Magic Initiate (Wizard) are always prepared."""
            cantrips = ["Mage Hand", "Prestidigitation"]
            spell = "Shield"
            char = self._build_magic_initiate_wizard(cantrips, spell)
            # Check cantrips — must appear with always_prepared=True
            cantrip_entries = [s for s in char["spells"]["cantrips"] if s["source"] == "Magic Initiate (Wizard)"]
            assert len(cantrip_entries) == 2, "Expected 2 cantrips from Magic Initiate (Wizard)"
            for entry in cantrip_entries:
                assert entry.get("always_prepared"), f"Cantrip {entry['name']} should be always prepared"
            # Check spell — must appear with always_prepared=True
            spell_entries = [s for s in char["spells"]["level_1"] if s["source"] == "Magic Initiate (Wizard)"]
            assert len(spell_entries) == 1, "Expected 1 level-1 spell from Magic Initiate (Wizard)"
            for entry in spell_entries:
                assert entry.get("always_prepared"), f"Spell {entry['name']} should be always prepared"

        def test_magic_initiate_counted_in_stats_always_prepared(self):
            """Magic Initiate cantrips/spells are stored in always_prepared (not prepared), counted in +X bonus."""
            cantrips = ["Mage Hand", "Prestidigitation"]
            spell = "Shield"
            builder = CharacterBuilder()
            builder.apply_choices({
                "character_name": "MI Stats Test",
                "level": 1,
                "species": "Human",
                "class": "Fighter",
                "background": "Sage",  # Sage grants Magic Initiate (Wizard)
                "ability_scores": {
                    "Strength": 10, "Dexterity": 10, "Constitution": 10,
                    "Intelligence": 16, "Wisdom": 10, "Charisma": 10
                },
                "background_bonuses": {"Intelligence": 2, "Constitution": 1},
                "feat_Magic Initiate (Wizard)_cantrips": cantrips,
                "feat_Magic Initiate (Wizard)_1st_level_spell": spell,
            })
            always_prepared = builder.character_data["spells"]["always_prepared"]
            prepared_cantrips = builder.character_data["spells"]["prepared"]["cantrips"]
            prepared_spells = builder.character_data["spells"]["prepared"]["spells"]
            # Cantrips and spell must be in always_prepared, NOT in prepared
            for cantrip in cantrips:
                assert cantrip in always_prepared, f"{cantrip} should be in always_prepared"
                assert cantrip not in prepared_cantrips, f"{cantrip} must NOT be in prepared.cantrips"
            assert spell in always_prepared, f"{spell} should be in always_prepared"
            assert spell not in prepared_spells, f"{spell} must NOT be in prepared.spells"
            # Verify stored metadata
            assert always_prepared["Mage Hand"]["level"] == 0
            assert always_prepared["Mage Hand"]["counts_against_limit"] is False
            assert always_prepared[spell]["counts_against_limit"] is False

    class TestFeyTouchedAlwaysPrepared:
        """Fey Touched: both the fixed Misty Step and the chosen spell are always prepared."""

        def _build_fey_touched(self, extra_spell):
            builder = CharacterBuilder()
            builder.apply_choices({
                "character_name": "FT Test",
                "level": 4,
                "species": "Human",
                "class": "Fighter",
                "background": "Sage",
                "ability_scores": {
                    "Strength": 10, "Dexterity": 10, "Constitution": 10,
                    "Intelligence": 16, "Wisdom": 10, "Charisma": 10
                },
                "background_bonuses": {"Intelligence": 2, "Constitution": 1},
                "class_feat_4": "Fey Touched",
                "class_feat_4_1st_level_spell": extra_spell,
            })
            return builder.to_character()

        def _find_spell_in_character(self, char, spell_name):
            """Return the spell entry with the given name from spells_by_level, or None."""
            for spells in char["spells_by_level"].values():
                for s in spells:
                    if s["name"] == spell_name:
                        return s
            return None

        def test_misty_step_always_prepared(self):
            """Misty Step (granted via effect) must be always prepared."""
            char = self._build_fey_touched("Bless")
            misty = self._find_spell_in_character(char, "Misty Step")
            assert misty is not None, "Misty Step should be in the character's spells"
            assert misty.get("always_prepared"), "Misty Step should be always prepared"

        def test_chosen_spell_always_prepared(self):
            """The additional chosen spell (e.g. Bless) must also be always prepared."""
            char = self._build_fey_touched("Bless")
            bless = self._find_spell_in_character(char, "Bless")
            assert bless is not None, "Bless should be in the character's spells"
            assert bless.get("always_prepared"), "Fey Touched chosen spell should be always prepared"
    """Origin feats with effects should have correct definitions."""

    def test_tough_has_bonus_hp_effect(self, origin_feats):
        """Tough feat must have a bonus_hp effect with value 2 and per_level scaling."""
        effects = origin_feats["Tough"].get("effects", [])
        hp_effects = [e for e in effects if e["type"] == "bonus_hp"]
        assert len(hp_effects) == 1
        assert hp_effects[0]["value"] == 2
        assert hp_effects[0]["scaling"] == "per_level"

    def test_alert_has_bonus_initiative_effect(self, origin_feats):
        """Alert must add proficiency bonus to initiative via a structured effect."""
        effects = origin_feats["Alert"].get("effects", [])
        initiative_effects = [e for e in effects if e["type"] == "bonus_initiative"]
        assert len(initiative_effects) == 1
        assert initiative_effects[0]["value"] == "proficiency"

    def test_alert_adds_proficiency_bonus_to_initiative(self, built_character):
        """Alert should make initiative equal Dex modifier plus proficiency bonus."""
        character = built_character({
            "character_name": "Alert Test",
            "level": 5,
            "species": "Human",
            "class": "Fighter",
            "background": "Criminal",  # Criminal grants the Alert origin feat.
            "ability_scores": {
                "Strength": 15, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        feat_names = [feat["name"] for feat in character["features"]["feats"]]
        assert "Alert" in feat_names
        # Dex mod (+2) + proficiency bonus at level 5 (+3) = 5.
        assert character["combat"]["initiative"] == 5
        assert character["combat"]["initiative_bonus"] == 5


# Feats that have effects (for parametrize)
FEATS_WITH_EFFECTS = [
    ("Lightly Armored", "grant_armor_proficiency"),
    ("Heavily Armored", "grant_armor_proficiency"),
    ("Moderately Armored", "grant_armor_proficiency"),
    ("Martial Weapon Training", "grant_weapon_proficiency"),
    ("Speedy", "increase_speed"),
    ("Telekinetic", "grant_cantrip"),
    ("Fey Touched", "grant_spell"),
    ("Shadow Touched", "grant_spell"),
    ("Telepathic", "grant_spell"),
    ("Actor", "ability_bonus"),
    ("Crossbow Expert", "ability_bonus"),
    ("Defensive Duelist", "ability_bonus"),
    ("Durable", "ability_bonus"),
    ("Keen Mind", "ability_bonus"),
    ("Shield Master", "ability_bonus"),
    ("Skulker", "ability_bonus"),
    ("Chef", "grant_tool_proficiency"),
    ("Poisoner", "grant_tool_proficiency"),
]


class TestEffectsStructure:
    """All feats with effects must have well-formed effect entries."""

    @pytest.mark.parametrize("feat_name,expected_type", FEATS_WITH_EFFECTS)
    def test_feat_has_expected_effect_type(self, general_feats, feat_name, expected_type):
        """Each feat's effects array contains the expected effect type."""
        effects = general_feats[feat_name].get("effects", [])
        effect_types = [e["type"] for e in effects]
        assert expected_type in effect_types, (
            f"{feat_name} should have effect type '{expected_type}', "
            f"but has: {effect_types}"
        )

    @pytest.mark.parametrize("feat_name,_", FEATS_WITH_EFFECTS)
    def test_effects_have_type_field(self, general_feats, feat_name, _):
        """Every effect entry must have a 'type' key."""
        effects = general_feats[feat_name].get("effects", [])
        for i, effect in enumerate(effects):
            assert "type" in effect, f"{feat_name} effect[{i}] missing 'type' field"


# ==================== 4. Choices Validation ====================


class TestFeatsWithChoices:
    """Feats containing choices arrays must have valid choice structure."""

    def _all_feats_with_choices(self, origin_feats, general_feats):
        """Return list of (feat_name, choices_array) for all feats that have choices."""
        result = []
        for name, data in origin_feats.items():
            if "choices" in data:
                result.append((name, data["choices"]))
        for name, data in general_feats.items():
            if "choices" in data:
                result.append((name, data["choices"]))
        return result

    def test_choices_is_list(self, origin_feats, general_feats):
        """choices field must be a list."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            assert isinstance(choices, list), f"{name}: choices should be a list"

    def test_choices_have_type(self, origin_feats, general_feats):
        """Each choice entry must have a 'type' field."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                assert "type" in choice, f"{name} choice[{i}] missing 'type'"

    def test_choices_have_name(self, origin_feats, general_feats):
        """Each choice entry must have a 'name' field."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                assert "name" in choice, f"{name} choice[{i}] missing 'name'"

    def test_choices_have_source(self, origin_feats, general_feats):
        """Each choice entry must have a 'source' field."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                assert "source" in choice, f"{name} choice[{i}] missing 'source'"

    def test_choice_type_is_valid(self, origin_feats, general_feats):
        """Choice type must be one of the known types."""
        valid_types = {"select_single", "select_multiple"}
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                assert choice["type"] in valid_types, (
                    f"{name} choice[{i}] has invalid type '{choice['type']}'"
                )

    def test_select_multiple_has_count(self, origin_feats, general_feats):
        """select_multiple choices must have a positive 'count' field."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                if choice["type"] == "select_multiple":
                    assert "count" in choice, (
                        f"{name} choice[{i}] select_multiple missing 'count'"
                    )
                    assert choice["count"] > 0, (
                        f"{name} choice[{i}] count should be > 0"
                    )

    def test_choice_source_has_type(self, origin_feats, general_feats):
        """Choice source must have a 'type' field (fixed_list or external)."""
        for name, choices in self._all_feats_with_choices(origin_feats, general_feats):
            for i, choice in enumerate(choices):
                source = choice["source"]
                assert "type" in source, (
                    f"{name} choice[{i}] source missing 'type'"
                )
                assert source["type"] in {"fixed_list", "external"}, (
                    f"{name} choice[{i}] source has invalid type '{source['type']}'"
                )


# ==================== Specific Origin Feats with Choices ====================


class TestMagicInitiateChoices:
    """Magic Initiate feats should have cantrip and spell choices."""

    @pytest.mark.parametrize("variant", [
        "Magic Initiate (Cleric)",
        "Magic Initiate (Druid)",
        "Magic Initiate (Wizard)",
    ])
    def test_has_cantrip_choice(self, origin_feats, variant):
        """Each Magic Initiate variant must have a cantrip selection (2 cantrips)."""
        choices = origin_feats[variant]["choices"]
        cantrip_choices = [c for c in choices if c["name"] == "cantrips"]
        assert len(cantrip_choices) == 1
        assert cantrip_choices[0]["type"] == "select_multiple"
        assert cantrip_choices[0]["count"] == 2

    @pytest.mark.parametrize("variant", [
        "Magic Initiate (Cleric)",
        "Magic Initiate (Druid)",
        "Magic Initiate (Wizard)",
    ])
    def test_has_spell_choice(self, origin_feats, variant):
        """Each Magic Initiate variant must have a 1st-level spell selection."""
        choices = origin_feats[variant]["choices"]
        spell_choices = [c for c in choices if c["name"] == "1st_level_spell"]
        assert len(spell_choices) == 1
        assert spell_choices[0]["type"] == "select_single"

    @pytest.mark.parametrize("variant,expected_file", [
        ("Magic Initiate (Cleric)", "spells/class_lists/cleric.json"),
        ("Magic Initiate (Druid)", "spells/class_lists/druid.json"),
        ("Magic Initiate (Wizard)", "spells/class_lists/wizard.json"),
    ])
    def test_cantrip_source_file(self, origin_feats, variant, expected_file):
        """Cantrip choices should reference the correct external spell file."""
        choices = origin_feats[variant]["choices"]
        cantrip_choice = next(c for c in choices if c["name"] == "cantrips")
        assert cantrip_choice["source"]["type"] == "external"
        assert cantrip_choice["source"]["file"] == expected_file

    @pytest.mark.parametrize("variant,expected_file", [
        ("Magic Initiate (Cleric)", "spells/class_lists/cleric.json"),
        ("Magic Initiate (Druid)", "spells/class_lists/druid.json"),
        ("Magic Initiate (Wizard)", "spells/class_lists/wizard.json"),
    ])
    def test_spell_source_file(self, origin_feats, variant, expected_file):
        """1st-level spell choices should reference the correct external spell file."""
        choices = origin_feats[variant]["choices"]
        spell_choice = next(c for c in choices if c["name"] == "1st_level_spell")
        assert spell_choice["source"]["type"] == "external"
        assert spell_choice["source"]["file"] == expected_file

    @pytest.mark.parametrize("variant,expected_cantrips", [
        ("Magic Initiate (Cleric)", ["Guidance", "Sacred Flame", "Thaumaturgy"]),
        ("Magic Initiate (Druid)", ["Druidcraft", "Guidance", "Resistance"]),
        ("Magic Initiate (Wizard)", ["Fire Bolt", "Mage Hand", "Minor Illusion"]),
    ])
    def test_cantrip_options_non_empty(self, origin_feats, variant, expected_cantrips):
        """Cantrip options must resolve to a non-empty list containing expected spells."""
        from utils.choice_resolver import load_external_choice_list
        choices = origin_feats[variant]["choices"]
        cantrip_choice = next(c for c in choices if c["name"] == "cantrips")
        file_path = cantrip_choice["source"]["file"]
        options = load_external_choice_list(file_path, "cantrips")
        assert len(options) > 0, f"{variant} cantrip options should not be empty"
        for spell in expected_cantrips:
            assert spell in options, f"{spell} should be in {variant} cantrip options"

    @pytest.mark.parametrize("variant,expected_spells", [
        ("Magic Initiate (Cleric)", ["Bane", "Command", "Cure Wounds", "Detect Magic", "Healing Word"]),
        ("Magic Initiate (Druid)", ["Faerie Fire", "Detect Magic", "Speak with Animals"]),
        ("Magic Initiate (Wizard)", ["Magic Missile", "Detect Magic", "Sleep"]),
    ])
    def test_spell_options_non_empty(self, origin_feats, variant, expected_spells):
        """1st-level spell options must resolve to a non-empty list containing expected spells."""
        from utils.choice_resolver import load_external_choice_list
        choices = origin_feats[variant]["choices"]
        spell_choice = next(c for c in choices if c["name"] == "1st_level_spell")
        file_path = spell_choice["source"]["file"]
        list_name = spell_choice["source"]["list"]
        options = load_external_choice_list(file_path, list_name)
        assert len(options) > 0, f"{variant} 1st-level spell options should not be empty"
        for spell in expected_spells:
            assert spell in options, f"{spell} should be in {variant} 1st-level spell options"


class TestSkilledChoices:
    """Skilled feat should allow choosing 3 skills or tools."""

    def test_skilled_choice_count(self, origin_feats):
        """Skilled allows selecting 3 skills or tools."""
        choices = origin_feats["Skilled"]["choices"]
        assert len(choices) == 1
        assert choices[0]["type"] == "select_multiple"
        assert choices[0]["count"] == 3

    def test_skilled_has_skill_options(self, origin_feats):
        """Skilled's options include standard D&D skills."""
        choices = origin_feats["Skilled"]["choices"]
        options = choices[0]["source"]["options"]
        # Spot-check some standard skills
        assert "Perception" in options
        assert "Stealth" in options
        assert "Athletics" in options


# ==================== 5. Builder Integration Tests ====================


class TestGetFeatChoices:
    """CharacterBuilder.get_feat_choices() should extract choices from the background feat."""

    def _builder_with_skilled(self):
        """Create a builder whose background grants the Skilled feat (Noble background)."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 1,
            "class": "Fighter",
            "background": "Noble",
            "ability_scores": {
                "Strength": 16, "Dexterity": 14, "Constitution": 15,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 10,
            },
            "background_bonuses": {"Charisma": 2, "Wisdom": 1},
        })
        return builder

    def test_returns_feat_name(self):
        """get_feat_choices returns the correct feat name for a Skilled background."""
        builder = self._builder_with_skilled()
        result = builder.get_feat_choices()
        # Soldier background grants the Skilled feat
        assert result["feat_name"] == "Skilled"

    def test_returns_one_choice(self):
        """get_feat_choices returns exactly one choice entry for Skilled."""
        builder = self._builder_with_skilled()
        result = builder.get_feat_choices()
        assert len(result["choices"]) == 1

    def test_choice_has_correct_count(self):
        """The Skilled choice should require selecting 3 options."""
        builder = self._builder_with_skilled()
        choice = builder.get_feat_choices()["choices"][0]
        assert choice["count"] == 3

    def test_choice_options_non_empty(self):
        """The Skilled choice should resolve to a non-empty options list."""
        builder = self._builder_with_skilled()
        choice = builder.get_feat_choices()["choices"][0]
        assert len(choice["options"]) > 0

    def test_choice_feature_name_is_choice_name(self):
        """feature_name should equal the raw choice name from the data file."""
        builder = self._builder_with_skilled()
        choice = builder.get_feat_choices()["choices"][0]
        assert choice["feature_name"] == "skills_or_tools"

    def test_no_background_returns_empty(self):
        """get_feat_choices returns empty list when no background is set."""
        builder = CharacterBuilder()
        result = builder.get_feat_choices()
        assert result["feat_name"] is None
        assert result["choices"] == []


class TestApplyFeatChoices:
    """CharacterBuilder.apply_feat_choices() should add proficiencies correctly."""

    def _builder_with_skilled(self):
        """Create a builder whose background grants the Skilled feat (Noble background)."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 1,
            "class": "Fighter",
            "background": "Noble",
            "ability_scores": {
                "Strength": 16, "Dexterity": 14, "Constitution": 15,
                "Intelligence": 8, "Wisdom": 10, "Charisma": 10,
            },
            "background_bonuses": {"Charisma": 2, "Wisdom": 1},
        })
        return builder

    def test_skills_added_to_skill_proficiencies(self):
        """Chosen skills should appear in proficiencies['skills']."""
        builder = self._builder_with_skilled()
        builder.apply_feat_choices({"skills_or_tools": ["Arcana", "Perception", "Stealth"]})
        character = builder.to_character()
        skills = character["proficiencies"]["skills"]
        assert "Arcana" in skills
        assert "Perception" in skills
        assert "Stealth" in skills

    def test_tools_added_to_tool_proficiencies(self):
        """Chosen tool names (not skills) should appear in proficiencies['tools']."""
        builder = self._builder_with_skilled()
        builder.apply_feat_choices({"skills_or_tools": ["Arcana", "Perception", "Thieves' Tools"]})
        character = builder.to_character()
        assert "Arcana" in character["proficiencies"]["skills"]
        assert "Thieves' Tools" in character["proficiencies"]["tools"]

    def test_mixed_skills_and_tools(self):
        """A mix of 2 skills and 1 tool should be split into the right buckets."""
        builder = self._builder_with_skilled()
        builder.apply_feat_choices({"skills_or_tools": ["Athletics", "Survival", "Carpenter's Tools"]})
        character = builder.to_character()
        assert "Athletics" in character["proficiencies"]["skills"]
        assert "Survival" in character["proficiencies"]["skills"]
        assert "Carpenter's Tools" in character["proficiencies"]["tools"]

    def test_choices_stored_in_choices_made(self):
        """Selected values should be persisted in choices_made under a namespaced key."""
        builder = self._builder_with_skilled()
        builder.apply_feat_choices({"skills_or_tools": ["Arcana", "Deception", "History"]})
        choices_made = builder.to_json()["choices_made"]
        assert "feat_Skilled_skills_or_tools" in choices_made
        assert set(choices_made["feat_Skilled_skills_or_tools"]) == {"Arcana", "Deception", "History"}

    def test_no_duplicate_proficiencies(self):
        """Applying feat choices twice should not duplicate proficiencies."""
        builder = self._builder_with_skilled()
        builder.apply_feat_choices({"skills_or_tools": ["Arcana", "History", "Perception"]})
        builder.apply_feat_choices({"skills_or_tools": ["Arcana", "History", "Perception"]})
        character = builder.to_character()
        assert character["proficiencies"]["skills"].count("Arcana") == 1


# ==================== 6. Tavern Brawler Effects ====================


class TestTavernBrawlerEffectsData:
    """Tavern Brawler origin feat effect data validation."""

    def test_tavern_brawler_has_weapon_proficiency_effect(self, origin_feats):
        """Tavern Brawler must have a grant_weapon_proficiency effect."""
        effects = origin_feats["Tavern Brawler"].get("effects", [])
        weapon_effects = [e for e in effects if e["type"] == "grant_weapon_proficiency"]
        assert len(weapon_effects) == 1

    def test_tavern_brawler_grants_improvised_weapons(self, origin_feats):
        """Tavern Brawler's weapon proficiency effect must include 'Improvised weapons'."""
        effects = origin_feats["Tavern Brawler"]["effects"]
        weapon_effect = next(e for e in effects if e["type"] == "grant_weapon_proficiency")
        assert "Improvised weapons" in weapon_effect["proficiencies"]


class TestTavernBrawlerIntegration:
    """Integration test: Sailor background grants Tavern Brawler which grants Improvised weapons."""

    def _build_sailor_fighter(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Test",
            "level": 1,
            "species": "Human",
            "class": "Fighter",
            "background": "Sailor",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        return builder.to_character()

    def test_tavern_brawler_feat_present(self):
        """Sailor background should grant Tavern Brawler feat."""
        character = self._build_sailor_fighter()
        feat_names = [f["name"] for f in character["features"]["feats"]]
        assert "Tavern Brawler" in feat_names

    def test_improvised_weapons_in_proficiencies(self):
        """Tavern Brawler effect should add 'Improvised weapons' to weapon proficiencies."""
        character = self._build_sailor_fighter()
        assert "Improvised weapons" in character["proficiencies"]["weapons"]


# ==================== 7. Crafter Choices ====================


class TestCrafterChoices:
    """Crafter origin feat choice structure validation."""

    def test_crafter_has_one_choice(self, origin_feats):
        """Crafter must have exactly 1 choice entry."""
        choices = origin_feats["Crafter"]["choices"]
        assert len(choices) == 1

    def test_crafter_choice_type(self, origin_feats):
        """Crafter choice type must be select_multiple."""
        choice = origin_feats["Crafter"]["choices"][0]
        assert choice["type"] == "select_multiple"

    def test_crafter_choice_count(self, origin_feats):
        """Crafter allows selecting 3 artisan tools."""
        choice = origin_feats["Crafter"]["choices"][0]
        assert choice["count"] == 3

    def test_crafter_choice_name(self, origin_feats):
        """Crafter choice name must be 'artisan_tools'."""
        choice = origin_feats["Crafter"]["choices"][0]
        assert choice["name"] == "artisan_tools"

    def test_crafter_choice_source_type(self, origin_feats):
        """Crafter choice source must be a fixed_list."""
        choice = origin_feats["Crafter"]["choices"][0]
        assert choice["source"]["type"] == "fixed_list"

    def test_crafter_has_expected_tools(self, origin_feats):
        """Crafter options must include key artisan tools."""
        options = origin_feats["Crafter"]["choices"][0]["source"]["options"]
        assert "Smith's Tools" in options
        assert "Carpenter's Tools" in options
        assert "Alchemist's Supplies" in options

    def test_crafter_option_count(self, origin_feats):
        """Crafter must have exactly 17 artisan tool options."""
        options = origin_feats["Crafter"]["choices"][0]["source"]["options"]
        assert len(options) == 17


# ==================== 8. Musician Choices ====================


class TestMusicianChoices:
    """Musician origin feat choice structure validation."""

    def test_musician_has_one_choice(self, origin_feats):
        """Musician must have exactly 1 choice entry."""
        choices = origin_feats["Musician"]["choices"]
        assert len(choices) == 1

    def test_musician_choice_type(self, origin_feats):
        """Musician choice type must be select_multiple."""
        choice = origin_feats["Musician"]["choices"][0]
        assert choice["type"] == "select_multiple"

    def test_musician_choice_count(self, origin_feats):
        """Musician allows selecting 3 musical instruments."""
        choice = origin_feats["Musician"]["choices"][0]
        assert choice["count"] == 3

    def test_musician_choice_name(self, origin_feats):
        """Musician choice name must be 'musical_instruments'."""
        choice = origin_feats["Musician"]["choices"][0]
        assert choice["name"] == "musical_instruments"

    def test_musician_choice_source_type(self, origin_feats):
        """Musician choice source must be a fixed_list."""
        choice = origin_feats["Musician"]["choices"][0]
        assert choice["source"]["type"] == "fixed_list"

    def test_musician_has_expected_instruments(self, origin_feats):
        """Musician options must include key instruments."""
        options = origin_feats["Musician"]["choices"][0]["source"]["options"]
        assert "Lute" in options
        assert "Drum" in options
        assert "Flute" in options

    def test_musician_option_count(self, origin_feats):
        """Musician must have exactly 10 musical instrument options."""
        options = origin_feats["Musician"]["choices"][0]["source"]["options"]
        assert len(options) == 10


class TestSelectedOriginFeatToolEffects:
    """Chosen Crafter and Musician tools must reach the exported character."""

    @pytest.mark.parametrize(
        "background,choice_key,selected_tools,unchosen_tool",
        [
            (
                "Artisan",
                "feat_Crafter_artisan_tools",
                ["Smith's Tools", "Carpenter's Tools", "Alchemist's Supplies"],
                "Brewer's Supplies",
            ),
            (
                "Entertainer",
                "feat_Musician_musical_instruments",
                ["Lute", "Drum", "Flute"],
                "Bagpipes",
            ),
        ],
    )
    def test_selected_tools_are_granted_in_to_character(
        self, background, choice_key, selected_tools, unchosen_tool
    ):
        builder = CharacterBuilder()
        builder.apply_choices(
            {
                "character_name": "Origin Feat Tool Test",
                "level": 1,
                "species": "Human",
                "class": "Fighter",
                "background": background,
                "ability_scores": {
                    "Strength": 14,
                    "Dexterity": 14,
                    "Constitution": 14,
                    "Intelligence": 10,
                    "Wisdom": 10,
                    "Charisma": 10,
                },
                choice_key: selected_tools,
            }
        )

        tools = builder.to_character()["proficiencies"]["tools"]
        assert set(selected_tools).issubset(tools)
        assert unchosen_tool not in tools


class TestDualWielderArmorClass:
    """Dual Wielder's AC bonus is conditional on actually wielding two weapons."""

    @staticmethod
    def _build_dual_wielder(class_equipment, include_feat):
        choices = {
            "character_name": "Dual Wielder AC Test",
            "level": 4,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 14,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 10,
                "Charisma": 10,
            },
            "equipment_selections": {
                "class_equipment": class_equipment,
                "background_equipment": "option_a",
            },
        }
        if include_feat:
            choices["class_feat_4"] = "Dual Wielder"
        builder = CharacterBuilder()
        builder.apply_choices(choices)
        return builder.to_character()

    @staticmethod
    def _unarmored_option(character):
        return next(
            option
            for option in character["ac_options"]
            if option["equipped_armor"] is None
            and option["formula"].startswith("10 + Dex modifier")
        )

    def test_bonus_applies_to_unarmored_option_while_dual_wielding(self):
        without_feat = self._build_dual_wielder("option_b", include_feat=False)
        with_feat = self._build_dual_wielder("option_b", include_feat=True)

        unarmored_without_feat = self._unarmored_option(without_feat)
        unarmored_with_feat = self._unarmored_option(with_feat)
        assert unarmored_with_feat["ac"] == unarmored_without_feat["ac"] + 1
        assert "Dual Wielder" in unarmored_with_feat["formula"]

    def test_bonus_does_not_apply_with_only_one_melee_weapon(self):
        without_feat = self._build_dual_wielder("option_c", include_feat=False)
        with_feat = self._build_dual_wielder("option_c", include_feat=True)

        assert self._unarmored_option(with_feat)["ac"] == self._unarmored_option(
            without_feat
        )["ac"]


# ==================== 5. Choice-Dependent Effects (General Feats) ====================


class TestAbilityScoreImprovementEffects:
    """ASI feat: +2 to one ability or +1 to two abilities via choice_effects."""

    def _build_with_asi(self, asi_choices):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "ASI Test",
            "level": 4,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        builder.apply_feat_choices(asi_choices, feat_name="Ability Score Improvement")
        return builder.to_character()

    def test_asi_has_choice_effects(self, general_feats):
        """ASI must have choice_effects for both ability_plus_2 and abilities_plus_1."""
        ce = general_feats["Ability Score Improvement"]["choice_effects"]
        assert "ability_plus_2" in ce
        assert "abilities_plus_1" in ce

    def test_asi_plus_2_one_ability(self):
        """Choosing +2 to Strength should increase Strength by 2."""
        char_with = self._build_with_asi({"ability_plus_2": "Strength"})
        char_without = self._build_with_asi({})
        str_with = char_with["abilities"]["strength"]["score"]
        str_without = char_without["abilities"]["strength"]["score"]
        assert str_with == str_without + 2

    def test_asi_plus_1_two_abilities(self):
        """Choosing +1 to Dexterity and Wisdom should increase each by 1."""
        char_with = self._build_with_asi({"abilities_plus_1": ["Dexterity", "Wisdom"]})
        char_without = self._build_with_asi({})
        dex_diff = char_with["abilities"]["dexterity"]["score"] - char_without["abilities"]["dexterity"]["score"]
        wis_diff = char_with["abilities"]["wisdom"]["score"] - char_without["abilities"]["wisdom"]["score"]
        assert dex_diff == 1
        assert wis_diff == 1

    def test_asi_does_not_exceed_20(self):
        """ASI should cap ability scores at 20."""
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Cap Test",
            "level": 4,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        # Strength is 15 + 2 (background) = 17, +2 ASI = 19 (under cap)
        builder.apply_feat_choices({"ability_plus_2": "Strength"}, feat_name="Ability Score Improvement")
        char = builder.to_character()
        assert char["abilities"]["strength"]["score"] <= 20


class TestResilientFeatEffects:
    """Resilient feat: +1 to chosen ability + saving throw proficiency."""

    def _build_with_resilient(self, ability):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Resilient Test",
            "level": 4,
            "species": "Human",
            "class": "Rogue",
            "background": "Criminal",
            "ability_scores": {
                "Strength": 10, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 13, "Charisma": 8
            },
            "background_bonuses": {"Dexterity": 2, "Constitution": 1},
        })
        builder.apply_feat_choices({"ability": ability}, feat_name="Resilient")
        return builder.to_character()

    def test_resilient_has_choice_effects(self, general_feats):
        """Resilient must have choice_effects for all 6 abilities."""
        ce = general_feats["Resilient"]["choice_effects"]["ability"]
        for ability in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
            assert ability in ce

    def test_resilient_constitution_score_increase(self):
        """Resilient (Constitution) should increase CON by 1."""
        char = self._build_with_resilient("Constitution")
        # Base 14 + background 1 + Resilient 1 = 16
        assert char["abilities"]["constitution"]["score"] == 16

    def test_resilient_constitution_save_proficiency(self):
        """Resilient (Constitution) should grant CON save proficiency."""
        char = self._build_with_resilient("Constitution")
        assert char["abilities"]["constitution"]["saving_throw_proficient"] is True

    def test_resilient_wisdom_save_proficiency(self):
        """Resilient (Wisdom) should grant WIS save proficiency."""
        char = self._build_with_resilient("Wisdom")
        assert char["abilities"]["wisdom"]["saving_throw_proficient"] is True

    def test_resilient_save_bonus_includes_proficiency(self):
        """Resilient save bonus should include proficiency bonus."""
        char = self._build_with_resilient("Constitution")
        prof_bonus = char["proficiency_bonus"]
        con_mod = char["abilities"]["constitution"]["modifier"]
        expected_save = con_mod + prof_bonus
        assert char["abilities"]["constitution"]["saving_throw"] == expected_save

    def test_resilient_does_not_affect_other_saves(self):
        """Resilient (Constitution) should not affect unrelated saves."""
        char = self._build_with_resilient("Constitution")
        # Strength is not proficient from Rogue (DEX/INT) or Resilient (CON)
        assert char["abilities"]["strength"]["saving_throw_proficient"] is False


class TestChefFeatAbilityChoice:
    """Chef should apply +1 to the chosen ability via choice_effects."""

    def _build_chef(self, feat_choices):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Chef Test",
            "level": 4,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "ability_scores": {
                "Strength": 15, "Dexterity": 14, "Constitution": 13,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        builder.apply_feat_choices(feat_choices, feat_name="Chef")
        return builder.to_character()

    def test_chef_constitution_choice_increases_constitution(self):
        char_with = self._build_chef({"ability": "Constitution"})
        char_without = self._build_chef({})
        assert char_with["abilities"]["constitution"]["score"] == (
            char_without["abilities"]["constitution"]["score"] + 1
        )


class TestSkillExpertFeatEffects:
    """Skill Expert: +1 ability, skill proficiency, skill expertise via choice_effects."""

    def _build_with_skill_expert(self, ability, skill_prof, skill_exp):
        builder = CharacterBuilder()
        builder.apply_choices({
            "character_name": "Skill Expert Test",
            "level": 4,
            "species": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "skill_choices": ["Athletics", "Perception"],
            "ability_scores": {
                "Strength": 15, "Dexterity": 13, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1},
        })
        builder.apply_feat_choices(
            {"ability": ability, "skill_proficiency": skill_prof, "skill_expertise": skill_exp},
            feat_name="Skill Expert",
        )
        return builder.to_character()

    def test_skill_expert_has_choice_effects(self, general_feats):
        """Skill Expert must have choice_effects for ability, skill_proficiency, skill_expertise."""
        ce = general_feats["Skill Expert"]["choice_effects"]
        assert "ability" in ce
        assert "skill_proficiency" in ce
        assert "skill_expertise" in ce

    def test_skill_expert_ability_increase(self):
        """Skill Expert should increase chosen ability by 1."""
        char = self._build_with_skill_expert("Wisdom", "Stealth", "Athletics")
        # Base 12 + Skill Expert 1 = 13
        assert char["abilities"]["wisdom"]["score"] == 13

    def test_skill_expert_grants_skill_proficiency(self):
        """Skill Expert should grant proficiency in chosen skill."""
        char = self._build_with_skill_expert("Strength", "Stealth", "Athletics")
        assert "Stealth" in char["proficiencies"]["skills"]

    def test_skill_expert_grants_expertise(self):
        """Skill Expert should grant expertise in chosen skill."""
        char = self._build_with_skill_expert("Strength", "Stealth", "Athletics")
        assert "Athletics" in char.get("skill_expertise", [])

    def test_skill_expert_expertise_doubles_proficiency(self):
        """Expertise from Skill Expert should double proficiency bonus in skill calculations."""
        char = self._build_with_skill_expert("Strength", "Stealth", "Athletics")
        athletics = char["skills"]["athletics"]
        assert athletics["expertise"] is True
        prof_bonus = char["proficiency_bonus"]
        str_mod = char["abilities"]["strength"]["modifier"]
        assert athletics["bonus"] == str_mod + prof_bonus * 2


class TestObservantFeatEffects:
    """Observant feat: +1 INT/WIS, proficiency-or-expertise in chosen skill."""

    def _build_with_observant(self, ability, skill, extra_skill_prof=None):
        choices = {
            "character_name": "Observant Test",
            "level": 4,
            "species": "Human",
            "class": "Rogue",
            "background": "Criminal",
            "skill_choices": ["Stealth", "Investigation"],
            "ability_scores": {
                "Strength": 8, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 13, "Wisdom": 14, "Charisma": 10
            },
            "background_bonuses": {"Dexterity": 2, "Intelligence": 1},
        }
        if extra_skill_prof:
            choices["skill_choices"].append(extra_skill_prof)
        builder = CharacterBuilder()
        builder.apply_choices(choices)
        builder.apply_feat_choices(
            {"ability": ability, "keen_observer_skill": skill},
            feat_name="Observant",
        )
        return builder.to_character()

    def test_observant_has_choice_effects(self, general_feats):
        """Observant must have choice_effects for ability and keen_observer_skill."""
        ce = general_feats["Observant"]["choice_effects"]
        assert "ability" in ce
        assert "keen_observer_skill" in ce

    def test_observant_intelligence_increase(self):
        """Observant (Intelligence) should increase INT by 1."""
        char = self._build_with_observant("Intelligence", "Perception")
        # Base 13 + background 1 + Observant 1 = 15
        assert char["abilities"]["intelligence"]["score"] == 15

    def test_observant_wisdom_increase(self):
        """Observant (Wisdom) should increase WIS by 1."""
        char = self._build_with_observant("Wisdom", "Perception")
        # Base 14 + Observant 1 = 15
        assert char["abilities"]["wisdom"]["score"] == 15

    def test_observant_grants_proficiency_when_lacking(self):
        """Observant should grant proficiency if character lacks it in the chosen skill."""
        # Perception is NOT in Rogue class skills selected
        char = self._build_with_observant("Wisdom", "Perception")
        assert "Perception" in char["proficiencies"]["skills"]
        # Should NOT get expertise since they didn't already have proficiency
        assert "Perception" not in char.get("skill_expertise", [])

    def test_observant_grants_expertise_when_already_proficient(self):
        """Observant should grant expertise if character already has proficiency."""
        # Investigation IS selected as a Rogue skill
        char = self._build_with_observant("Intelligence", "Investigation")
        assert "Investigation" in char["proficiencies"]["skills"]
        assert "Investigation" in char.get("skill_expertise", [])

    def test_observant_keen_observer_options(self, general_feats):
        """Keen Observer skill choice must offer Insight, Investigation, Perception."""
        choices = general_feats["Observant"]["choices"]
        skill_choice = next(c for c in choices if c["name"] == "keen_observer_skill")
        options = skill_choice["source"]["options"]
        assert set(options) == {"Insight", "Investigation", "Perception"}
