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
