"""
Integration tests for the Lorwyn: First Light supplement.
Tests manifest discovery, species traits, lineages, backgrounds, feats,
and CharacterBuilder / API catalog integration.
"""

import pytest
from modules.supplement_manager import get_supplement_manager
from modules.character_builder import CharacterBuilder


def test_lfl_manifest_and_indexing():
    mgr = get_supplement_manager()
    mgr.reload_all()
    manifest = mgr.manifests.get("lorwyn-first-light")
    assert manifest is not None
    assert manifest["title"] == "Lorwyn: First Light"
    assert manifest["publisher"] == "Wizards of the Coast"

    supplements = mgr.list_supplements()
    lfl_entry = next((s for s in supplements if s["id"] == "lorwyn-first-light"), None)
    assert lfl_entry is not None
    assert lfl_entry["counts"]["species"] == 6
    assert lfl_entry["counts"]["backgrounds"] == 2
    assert lfl_entry["counts"]["feats"] == 2


def test_lfl_species_details():
    mgr = get_supplement_manager()

    # 1. Boggart
    boggart = mgr.get_species_detail("Boggart")
    assert boggart is not None
    assert boggart["creature_type"] == "Humanoid"
    assert boggart["size"] == "Small"
    assert boggart["speed"] == 30
    assert boggart["darkvision"] == 60
    assert "Fury of the Small" in boggart["traits"]
    assert "Nimble Escape" in boggart["traits"]
    assert "Goblinoid" in boggart["traits"]

    # 2. Flamekin
    flamekin = mgr.get_species_detail("Flamekin")
    assert flamekin is not None
    assert flamekin["creature_type"] == "Humanoid"
    assert flamekin["speed"] == 30
    assert flamekin["darkvision"] == 60
    assert "Fire Resistance" in flamekin["traits"]
    assert "Reach to the Blaze" in flamekin["traits"]

    # 3. Rimekin
    rimekin = mgr.get_species_detail("Rimekin")
    assert rimekin is not None
    assert rimekin["creature_type"] == "Humanoid"
    assert rimekin["speed"] == 30
    assert rimekin["darkvision"] == 60
    assert "Cold Resistance" in rimekin["traits"]
    assert "Cold Fire Magic" in rimekin["traits"]

    # 4. Lorwyn Changeling
    changeling = mgr.get_species_detail("Lorwyn Changeling")
    assert changeling is not None
    assert changeling["creature_type"] == "Fey"
    assert changeling["darkvision"] == 120
    assert "Shape Self" in changeling["traits"]
    assert "Unpredictable Movement" in changeling["traits"]
    assert "Instinctive Deception" in changeling["traits"]

    # 5. Faerie
    faerie = mgr.get_species_detail("Faerie")
    assert faerie is not None
    assert faerie["creature_type"] == "Fey"
    assert "Flight" in faerie["traits"]
    assert "Fairy Magic" in faerie["traits"]

    # 6. Kithkin
    kithkin = mgr.get_species_detail("Kithkin")
    assert kithkin is not None
    assert "Brave" in kithkin["traits"]
    assert "Luck" in kithkin["traits"]
    assert "Naturally Stealthy" in kithkin["traits"]


def test_lfl_species_variants():
    mgr = get_supplement_manager()

    # Lorwyn Elf
    lorwyn_elf = mgr.get_lineage("Lorwyn Elf")
    assert lorwyn_elf is not None
    assert lorwyn_elf["parent_species"] == "Elf"
    assert lorwyn_elf["cantrip_replacement"] == "Druid"
    assert "Lorwyn Elf Lineage" in lorwyn_elf["traits"]

    # Shadowmoor Elf
    shadowmoor_elf = mgr.get_lineage("Shadowmoor Elf")
    assert shadowmoor_elf is not None
    assert shadowmoor_elf["parent_species"] == "Elf"
    assert "Shadowmoor Elf Lineage" in shadowmoor_elf["traits"]
    effects = shadowmoor_elf["traits"]["Shadowmoor Elf Lineage"].get("effects", [])
    assert any(e.get("type") == "grant_darkvision" and e.get("range") == 120 for e in effects)

    # Shadowmoor Faerie & Shadowmoor Kithkin
    sh_faerie = mgr.get_lineage("Shadowmoor Faerie")
    assert sh_faerie is not None
    assert sh_faerie["parent_species"] == "Faerie"

    sh_kithkin = mgr.get_lineage("Shadowmoor Kithkin")
    assert sh_kithkin is not None
    assert sh_kithkin["parent_species"] == "Kithkin"

    # Ensure parent species Elf has lineages merged from supplement
    elf_detail = mgr.get_species_detail("Elf")
    assert elf_detail is not None
    assert "Lorwyn Elf" in elf_detail["lineages"]
    assert "Shadowmoor Elf" in elf_detail["lineages"]


def test_lfl_backgrounds():
    mgr = get_supplement_manager()

    # Lorwyn Expert
    bg_lorwyn = mgr.get_background("Lorwyn Expert")
    assert bg_lorwyn is not None
    assert bg_lorwyn["ability_score_increase"]["options"] == ["Strength", "Constitution", "Wisdom"]
    skills = next(e["skills"] for e in bg_lorwyn["effects"] if e["type"] == "grant_skill_proficiency")
    assert set(skills) == {"Athletics", "Nature"}
    feat = next(e["feat"] for e in bg_lorwyn["effects"] if e["type"] == "grant_origin_feat")
    assert feat == "Child of the Sun"

    # Shadowmoor Expert
    bg_shadow = mgr.get_background("Shadowmoor Expert")
    assert bg_shadow is not None
    assert bg_shadow["ability_score_increase"]["options"] == ["Dexterity", "Intelligence", "Charisma"]
    skills = next(e["skills"] for e in bg_shadow["effects"] if e["type"] == "grant_skill_proficiency")
    assert set(skills) == {"Acrobatics", "Deception"}
    feat = next(e["feat"] for e in bg_shadow["effects"] if e["type"] == "grant_origin_feat")
    assert feat == "Shadowmoor Hexer"


def test_lfl_feats():
    mgr = get_supplement_manager()
    feats = mgr.get_feats()

    sun = feats.get("Child of the Sun")
    assert sun is not None
    assert sun["category"] == "Origin"
    assert "Eyes of Eirdu" in sun["benefits"][0]
    assert "Faerie Fire" in sun["benefits"][1]

    hexer = feats.get("Shadowmoor Hexer")
    assert hexer is not None
    assert hexer["category"] == "Origin"
    assert "Hex" in hexer["benefits"][0]
    assert "Curse Magic" in hexer["benefits"][1]


def test_lfl_character_builder_integration():
    builder = CharacterBuilder()
    assert builder.set_species("Flamekin") is True
    assert builder.set_background("Lorwyn Expert") is True
    assert builder.set_class("Fighter") is True

    char = builder.character_data
    assert char["species"] == "Flamekin"
    assert char["background"] == "Lorwyn Expert"
    assert char["class"] == "Fighter"
    assert char["speed"] == 30
    assert "Fire" in char.get("resistances", [])
    species_feature_names = [f["name"] for f in char.get("features", {}).get("species", [])]
    assert "Fire Resistance" in species_feature_names

    # Check origin feat granted by background
    feat_names = [f["name"] for f in char.get("features", {}).get("feats", [])]
    assert "Child of the Sun" in feat_names


def test_lfl_api_catalog(client):
    # Check species catalog
    r = client.get("/api/v1/catalog/species")
    assert r.status_code == 200
    species_list = r.get_json()["species"]
    lfl_species = [s for s in species_list if s.get("source_id") == "lorwyn-first-light"]
    names = {s["name"] for s in lfl_species}
    assert "Boggart" in names
    assert "Flamekin" in names
    assert "Rimekin" in names
    assert "Lorwyn Changeling" in names
    assert "Faerie" in names
    assert "Kithkin" in names

    # Check backgrounds catalog
    r_bg = client.get("/api/v1/catalog/backgrounds")
    assert r_bg.status_code == 200
    bg_list = r_bg.get_json()["backgrounds"]
    lfl_bgs = [b for b in bg_list if b.get("source_id") == "lorwyn-first-light"]
    bg_names = {b["name"] for b in lfl_bgs}
    assert "Lorwyn Expert" in bg_names
    assert "Shadowmoor Expert" in bg_names

    # Check build endpoint with Lorwyn choices
    build_payload = {
        "choices_made": {
            "character_name": "Gaddock",
            "species": "Kithkin",
            "lineage": "Lorwyn Kithkin",
            "background": "Lorwyn Expert",
            "classes": [{"class_name": "Fighter", "level": 1}],
            "ability_scores": {
                "Strength": 14,
                "Dexterity": 12,
                "Constitution": 14,
                "Intelligence": 10,
                "Wisdom": 14,
                "Charisma": 10
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    }
    r_build = client.post("/api/v1/character/build", json=build_payload)
    assert r_build.status_code == 200
    built = r_build.get_json()["character"]
    assert built["species"] == "Kithkin"
    assert built["background"] == "Lorwyn Expert"
    feat_names = [f["name"] for f in built.get("features", {}).get("feats", [])]
    assert "Child of the Sun" in feat_names

    # Check preview-step returns Lorwyn Elf and Shadowmoor Elf for Elf
    r_prev = client.post(
        "/api/v1/character/preview-step",
        json={"step": "species", "choices_made": {"species": "Elf"}}
    )
    assert r_prev.status_code == 200
    lineage_names = {l["name"] for l in r_prev.get_json().get("lineages", [])}
    assert "Lorwyn Elf" in lineage_names
    assert "Shadowmoor Elf" in lineage_names

    # Check build with Elf + Lorwyn Elf
    elf_payload = {
        "choices_made": {
            "character_name": "Nissa",
            "species": "Elf",
            "lineage": "Lorwyn Elf",
            "background": "Acolyte",
            "classes": [{"class_name": "Druid", "level": 1}],
            "ability_scores": {
                "Strength": 10, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 10
            }
        }
    }
    r_elf_build = client.post("/api/v1/character/build", json=elf_payload)
    assert r_elf_build.status_code == 200
    elf_char = r_elf_build.get_json()["character"]
    assert elf_char["species"] == "Elf"
    assert elf_char["lineage"] == "Lorwyn Elf"
    lineage_feat_names = [f["name"] for f in elf_char.get("features", {}).get("lineage", [])]
    assert "Lorwyn Elf Lineage" in lineage_feat_names

