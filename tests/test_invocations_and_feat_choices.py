import pytest
from modules.character_builder import CharacterBuilder
from modules.derived_stats import build_level_up_preview, build_invocation_management_view

class TestInvocationsAndFeatChoices:
    def test_lessons_of_the_first_ones_with_alert(self):
        builder = CharacterBuilder()
        choices = {
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones", "Agonizing Blast"],
                "cantrip_choices": {},
                "choices": {
                    "Lessons of the First Ones": {
                        "origin_feat": "Alert"
                    }
                }
            }
        }
        builder.apply_choices(choices)

        # Check Alert is in features["feats"]
        feats = builder.character_data["features"]["feats"]
        assert any(f["name"] == "Alert" for f in feats), "Alert must be granted by Lessons of the First Ones"

        # Check stats & descriptors
        stats = builder.calculate_eldritch_invocation_stats()
        assert stats["has_invocations"] is True
        assert stats["max_invocations"] == 3  # Level 2 Warlock gets 3 invocations
        assert "Lessons of the First Ones" in stats["current_invocations"]
        assert "Agonizing Blast" in stats["current_invocations"]

        descriptors = stats.get("invocation_choice_descriptors", [])
        lessons_desc = next((d for d in descriptors if d["invocation"] == "Lessons of the First Ones"), None)
        assert lessons_desc is not None
        assert "Alert" in lessons_desc["options"]
        assert lessons_desc["selected"] == "Alert"

        # Check enriched class feature display
        char = builder.to_character()
        class_features = char["features"]["class"]
        inv_feat = next((f for f in class_features if "Eldritch Invocations" in f["name"]), None)
        assert inv_feat is not None
        assert "Lessons of the First Ones (Alert)" in inv_feat["name"]
        assert "Agonizing Blast" in inv_feat["name"]

    def test_lessons_of_the_first_ones_with_echoing_soul(self):
        builder = CharacterBuilder()
        choices = {
            "active_sources": ["core-phb-2024", "ravenloft-the-horrors-within"],
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones"],
                "cantrip_choices": {},
                "choices": {
                    "Lessons of the First Ones": {
                        "origin_feat": "Echoing Soul"
                    }
                }
            },
            "feat_Echoing Soul_skills": ["Stealth", "Perception"],
            "feat_Echoing Soul_expertise": ["Perception"],
            "feat_Echoing Soul_language": ["Draconic"],
        }
        builder.apply_choices(choices)

        feats = builder.character_data["features"]["feats"]
        assert any(f["name"] == "Echoing Soul" for f in feats), "Echoing Soul must be granted"

        profs = builder.character_data["proficiencies"]
        assert "Stealth" in profs["skills"]
        assert "Perception" in profs["skills"]
        assert "Perception" in builder.character_data.get("skill_expertise", [])
        assert "Draconic" in profs["languages"]

        # Check that invocation_choice_descriptors exposes feat_sub_choices
        stats = builder.calculate_eldritch_invocation_stats()
        descriptors = stats.get("invocation_choice_descriptors", [])
        lessons_desc = next((d for d in descriptors if d["invocation"] == "Lessons of the First Ones"), None)
        assert lessons_desc is not None
        sub_choices = lessons_desc.get("feat_sub_choices", [])
        assert len(sub_choices) == 3  # skills, expertise, language
        sub_names = [sc["name"] for sc in sub_choices]
        assert "skills" in sub_names
        assert "expertise" in sub_names
        assert "language" in sub_names

    def test_invocation_clearing_and_swapping(self):
        builder = CharacterBuilder()
        choices = {
            "active_sources": ["core-phb-2024", "ravenloft-the-horrors-within"],
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones"],
                "cantrip_choices": {},
                "choices": {
                    "Lessons of the First Ones": {
                        "origin_feat": "Echoing Soul"
                    }
                }
            },
            "feat_Echoing Soul_skills": ["Stealth", "Perception"],
            "feat_Echoing Soul_expertise": ["Perception"],
            "feat_Echoing Soul_language": ["Draconic"],
        }
        builder.apply_choices(choices)
        assert any(f["name"] == "Echoing Soul" for f in builder.character_data["features"]["feats"])

        # Now change invocation selection to Alert instead
        new_choices = {
            "active_sources": ["core-phb-2024", "ravenloft-the-horrors-within"],
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones"],
                "cantrip_choices": {},
                "choices": {
                    "Lessons of the First Ones": {
                        "origin_feat": "Alert"
                    }
                }
            }
        }
        builder.apply_choices(new_choices)

        feats = [f["name"] for f in builder.character_data["features"]["feats"]]
        assert "Alert" in feats
        assert "Echoing Soul" not in feats
        # Echoing Soul skills and languages should be cleaned up
        assert "Stealth" not in builder.character_data["proficiencies"]["skills"]
        assert "Draconic" not in builder.character_data["proficiencies"]["languages"]

    def test_dependency_tracking(self):
        builder = CharacterBuilder()
        builder.apply_choices({"class": "Warlock", "level": 5})

        inv_data = {
            "selected": ["Pact of the Blade", "Thirsting Blade"],
            "cantrip_choices": {},
            "choices": {}
        }
        builder.apply_choice("eldritch_invocation_selections", inv_data)

        # Thirsting Blade requires Pact of the Blade
        deps = builder.get_dependent_invocations("Pact of the Blade", inv_data["selected"])
        assert "Thirsting Blade" in deps

        # Lifedrinker or others not selected shouldn't be in deps
        assert len(deps) == 1

        # Nothing depends on Thirsting Blade
        assert len(builder.get_dependent_invocations("Thirsting Blade", inv_data["selected"])) == 0

        # Stats exposes dependency_map
        stats = builder.calculate_eldritch_invocation_stats()
        dep_map = stats.get("dependency_map", {})
        assert "Thirsting Blade" in dep_map.get("Pact of the Blade", [])

    def test_level_up_preview_invocation_changes(self):
        builder = CharacterBuilder()
        choices = {
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Pact of the Blade", "Agonizing Blast"],
                "cantrip_choices": {},
                "choices": {}
            }
        }
        builder.apply_choices(choices)

        # Preview level up to Warlock 3
        preview = build_level_up_preview(builder.character_data["choices_made"], class_to_level="Warlock")
        inv_changes = preview.get("invocation_changes")
        assert inv_changes is not None
        assert inv_changes["has_invocations"] is True
        assert inv_changes["allows_swap"] is True
        assert "Pact of the Blade" in inv_changes["current_invocations"]
        assert "Agonizing Blast" in inv_changes["current_invocations"]
        assert "available_invocations" in inv_changes

    def test_lessons_of_the_first_ones_supplement_sources_filtering(self):
        # 1. Core only
        builder_core = CharacterBuilder()
        builder_core.apply_choices({
            "active_sources": ["core-phb-2024"],
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        stats_core = builder_core.calculate_eldritch_invocation_stats()
        desc_core = next(d for d in stats_core["invocation_choice_descriptors"] if d["invocation"] == "Lessons of the First Ones")
        assert "Alert" in desc_core["options"]
        assert "Echoing Soul" not in desc_core["options"]
        assert "Arcane Infiltrator" not in desc_core["options"]
        assert len(desc_core["options"]) == 12

        # 2. With supplements enabled
        builder_supp = CharacterBuilder()
        builder_supp.apply_choices({
            "active_sources": ["core-phb-2024", "ravenloft-the-horrors-within", "arcana-unleashed"],
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Lessons of the First Ones"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        stats_supp = builder_supp.calculate_eldritch_invocation_stats()
        desc_supp = next(d for d in stats_supp["invocation_choice_descriptors"] if d["invocation"] == "Lessons of the First Ones")
        assert "Alert" in desc_supp["options"]
        assert "Echoing Soul" in desc_supp["options"]
        assert "Arcane Infiltrator" in desc_supp["options"]
        assert len(desc_supp["options"]) > 12

    def test_gift_of_the_depths_swim_speed_and_water_breathing(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Warlock",
            "level": 5,
            "eldritch_invocation_selections": {
                "selected": ["Gift of the Depths"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        char = builder.to_character()
        assert char.get("swim_speed") == 30
        assert char["combat"].get("swim_speed") == 30
        assert "Water Breathing" in char["spells"]["always_prepared"]
        assert char["spells"]["always_prepared"]["Water Breathing"]["once_per_long_rest"] is True

        # When swapping invocation, swim speed and Water Breathing should be cleared
        builder.apply_choice("eldritch_invocation_selections", {
            "selected": ["Armor of Shadows"],
            "cantrip_choices": {},
            "choices": {}
        })
        char_after = builder.to_character()
        assert char_after.get("swim_speed") is None
        assert char_after["combat"].get("swim_speed") is None
        assert "Water Breathing" not in char_after["spells"]["always_prepared"]

    def test_devils_sight_magical_darkness_sight(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Devil's Sight"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        assert builder.character_data.get("magical_darkness_sight") == {
            "range": 120,
            "source": "Devil's Sight",
            "source_type": "invocation",
        }

        # Swap invocation
        builder.apply_choice("eldritch_invocation_selections", {
            "selected": ["Armor of Shadows"],
            "cantrip_choices": {},
            "choices": {}
        })
        assert builder.character_data.get("magical_darkness_sight") == {}

    def test_witch_sight_truesight(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Warlock",
            "level": 15,
            "eldritch_invocation_selections": {
                "selected": ["Witch Sight"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        char = builder.to_character()
        assert char.get("truesight") == 30

    def test_at_will_spells_invocations(self):
        builder = CharacterBuilder()
        builder.apply_choices({
            "class": "Warlock",
            "level": 2,
            "eldritch_invocation_selections": {
                "selected": ["Armor of Shadows", "Fiendish Vigor"],
                "cantrip_choices": {},
                "choices": {}
            }
        })
        char = builder.to_character()
        always_prep = char["spells"]["always_prepared"]
        assert "Mage Armor" in always_prep
        assert always_prep["Mage Armor"]["at_will"] is True
        assert "False Life" in always_prep
        assert always_prep["False Life"]["at_will"] is True
