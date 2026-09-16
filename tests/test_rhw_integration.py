"""
Integration tests for the Ravenloft: The Horrors Within supplement.
Tests manifest discovery, subclasses, species, backgrounds, feats,
and CharacterBuilder / API catalog integration.
"""

import pytest
from app import app
from modules.supplement_manager import get_supplement_manager
from modules.character_builder import CharacterBuilder


def test_rhw_manifest_and_indexing():
    mgr = get_supplement_manager()
    mgr.reload_all()
    manifest = mgr.manifests.get("ravenloft-the-horrors-within")
    assert manifest is not None
    assert manifest["title"] == "Ravenloft: The Horrors Within"
    assert manifest["publisher"] == "Wizards of the Coast"
    assert manifest["compatibility"] == "2024"

    supplements = mgr.list_supplements()
    rhw_entry = next((s for s in supplements if s["id"] == "ravenloft-the-horrors-within"), None)
    assert rhw_entry is not None
    assert rhw_entry["counts"]["subclasses"] == 7
    assert rhw_entry["counts"]["species"] == 4
    assert rhw_entry["counts"]["backgrounds"] == 4
    assert rhw_entry["counts"]["feats"] == 11


def test_rhw_subclasses():
    mgr = get_supplement_manager()

    # 1. Reanimator (Artificer)
    reanimator = mgr.get_subclass("Artificer", "Reanimator")
    assert reanimator is not None
    assert "Reanimator Spells" in reanimator["features_by_level"]["3"]
    assert "Reanimated Companion" in reanimator["features_by_level"]["3"]
    assert "Strange Modifications" in reanimator["features_by_level"]["5"]
    assert "Improved Reanimation" in reanimator["features_by_level"]["9"]
    assert "Refined Reanimation" in reanimator["features_by_level"]["15"]

    # 2. College of Spirits (Bard)
    spirits = mgr.get_subclass("Bard", "College of Spirits")
    assert spirits is not None
    assert "Channeler" in spirits["features_by_level"]["3"]
    assert "Spirits from Beyond" in spirits["features_by_level"]["3"]
    assert "Empowered Channeling" in spirits["features_by_level"]["6"]
    assert "Mystical Connection" in spirits["features_by_level"]["14"]

    # 3. Grave Domain (Cleric)
    grave = mgr.get_subclass("Cleric", "Grave Domain")
    assert grave is not None
    assert "Circle of Mortality" in grave["features_by_level"]["3"]
    assert "Channel Divinity: Path to the Grave" in grave["features_by_level"]["3"]
    assert "Sentinel at Death's Door" in grave["features_by_level"]["6"]
    assert "Divine Reaper" in grave["features_by_level"]["17"]

    # 4. Hollow Warden (Ranger)
    hollow = mgr.get_subclass("Ranger", "Hollow Warden")
    assert hollow is not None
    assert "Wrath of the Wild" in hollow["features_by_level"]["3"]
    assert "Hungering Might" in hollow["features_by_level"]["7"]
    assert "Rot and Violence" in hollow["features_by_level"]["11"]
    assert "Ancient Might" in hollow["features_by_level"]["15"]

    # 5. Phantom (Rogue)
    phantom = mgr.get_subclass("Rogue", "Phantom")
    assert phantom is not None
    assert "Whispers of the Dead" in phantom["features_by_level"]["3"]
    assert "Wails from the Grave" in phantom["features_by_level"]["3"]
    assert "Tokens of the Departed" in phantom["features_by_level"]["9"]
    assert "Ghost Walk" in phantom["features_by_level"]["13"]
    assert "Death's Friend" in phantom["features_by_level"]["17"]

    # 6. Shadow Sorcery (Sorcerer)
    shadow = mgr.get_subclass("Sorcerer", "Shadow Sorcery")
    assert shadow is not None
    assert "Power of Shadow" in shadow["features_by_level"]["3"]
    assert "Beasts of Ill Omen" in shadow["features_by_level"]["6"]
    assert "Shadow Walk" in shadow["features_by_level"]["14"]
    assert "Umbral Form" in shadow["features_by_level"]["18"]

    # 7. The Undead (Warlock)
    undead = mgr.get_subclass("Warlock", "The Undead")
    assert undead is not None
    assert "Form of Dread" in undead["features_by_level"]["3"]
    assert "Grave Touched" in undead["features_by_level"]["6"]
    assert "Necrotic Husk" in undead["features_by_level"]["10"]
    assert "Superior Dread" in undead["features_by_level"]["14"]


def test_rhw_species():
    mgr = get_supplement_manager()

    # 1. Dhampir
    dhampir = mgr.get_species_detail("Dhampir")
    assert dhampir is not None
    assert dhampir["creature_type"] == "Humanoid"
    assert dhampir["speed"] == 35
    assert dhampir["darkvision"] == 60
    assert "Spider Climb" in dhampir["traits"]
    assert "Trace of Undeath" in dhampir["traits"]
    assert "Vampiric Bite" in dhampir["traits"]

    # 2. Hexblood
    hexblood = mgr.get_species_detail("Hexblood")
    assert hexblood is not None
    assert hexblood["creature_type"] == "Fey"
    assert hexblood["speed"] == 30
    assert hexblood["darkvision"] == 60
    assert "Eerie Token" in hexblood["traits"]
    assert "Hex Magic" in hexblood["traits"]

    # 3. Lupin
    lupin = mgr.get_species_detail("Lupin")
    assert lupin is not None
    assert lupin["creature_type"] == "Humanoid"
    assert lupin["speed"] == 30
    assert "Feral Pounce" in lupin["traits"]
    assert "Howl" in lupin["traits"]
    assert "Werewolf Instincts" in lupin["traits"]
    assert lupin["traits"]["Werewolf Instincts"]["type"] == "choice"

    # 4. Reborn
    reborn = mgr.get_species_detail("Reborn")
    assert reborn is not None
    assert reborn["creature_type"] == "Humanoid"
    assert "Escaped Death" in reborn["traits"]
    assert "Everlasting" in reborn["traits"]
    assert "Knowledge from a Past Life" in reborn["traits"]
    assert "Strange Endurance" in reborn["traits"]


def test_rhw_backgrounds():
    mgr = get_supplement_manager()
    bgs = mgr.get_backgrounds()

    # Haunted One
    assert "Haunted One" in bgs
    ho = bgs["Haunted One"]
    assert set(ho["ability_score_increase"]["options"]) == {"Constitution", "Wisdom", "Charisma"}
    assert any(e.get("type") == "grant_origin_feat" and e.get("feat") == "Survivor" for e in ho["effects"])

    # Investigator
    assert "Investigator" in bgs
    inv = bgs["Investigator"]
    assert set(inv["ability_score_increase"]["options"]) == {"Intelligence", "Wisdom", "Charisma"}
    assert any(e.get("type") == "grant_origin_feat" and e.get("feat") == "Sharp Eye" for e in inv["effects"])

    # Mist Wanderer
    assert "Mist Wanderer" in bgs
    mw = bgs["Mist Wanderer"]
    assert set(mw["ability_score_increase"]["options"]) == {"Dexterity", "Constitution", "Wisdom"}
    assert any(e.get("type") == "grant_origin_feat" and e.get("feat") == "Mist Walker" for e in mw["effects"])

    # Spirit Medium
    assert "Spirit Medium" in bgs
    sm = bgs["Spirit Medium"]
    assert set(sm["ability_score_increase"]["options"]) == {"Constitution", "Intelligence", "Wisdom"}
    assert any(e.get("type") == "grant_origin_feat" and e.get("feat") == "Echoing Soul" for e in sm["effects"])


def test_rhw_feats():
    mgr = get_supplement_manager()
    feats = mgr.get_feats("origin")

    expected_feats = [
        "Sharp Eye", "Survivor", "Aberrant Anatomy", "Echoing Soul",
        "Gathered Whispers", "Living Shadow", "Mist Walker", "Second Skin",
        "Symbiotic Being", "Touch of Death", "Watchers"
    ]
    for feat_name in expected_feats:
        assert feat_name in feats, f"Missing feat: {feat_name}"
        feat_data = feats[feat_name]
        assert feat_data["category"] in ("Origin", "origin")
        assert feat_data.get("source") == "Ravenloft: The Horrors Within" or feat_data.get("source_id") == "ravenloft-the-horrors-within"


def test_rhw_character_building_and_api():
    client = app.test_client()

    # 1. Check API endpoint for supplements
    r_supp = client.get("/api/v1/supplements")
    assert r_supp.status_code == 200
    supp_list = r_supp.get_json()["supplements"]
    rhw_manifest = next((s for s in supp_list if s["id"] == "ravenloft-the-horrors-within"), None)
    assert rhw_manifest is not None

    # 2. Check catalog species
    r_spec = client.get("/api/v1/catalog/species")
    assert r_spec.status_code == 200
    species_list = r_spec.get_json()["species"]
    species_names = {s["name"] for s in species_list}
    assert {"Dhampir", "Hexblood", "Lupin", "Reborn"}.issubset(species_names)

    # 3. Check catalog backgrounds
    r_bg = client.get("/api/v1/catalog/backgrounds")
    assert r_bg.status_code == 200
    bg_list = r_bg.get_json()["backgrounds"]
    bg_names = {b["name"] for b in bg_list}
    assert {"Haunted One", "Investigator", "Mist Wanderer", "Spirit Medium"}.issubset(bg_names)

    # 4. Check build endpoint with Hollow Warden Ranger + Lupin + Mist Wanderer
    build_payload_ranger = {
        "choices_made": {
            "character_name": "Valdis",
            "species": "Lupin",
            "background": "Mist Wanderer",
            "classes": [
                {"class_name": "Ranger", "level": 3, "subclass": "Hollow Warden"}
            ],
            "ability_scores": {
                "Strength": 10, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 14, "Charisma": 10
            },
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1}
        }
    }
    r_build_ranger = client.post("/api/v1/character/build", json=build_payload_ranger)
    assert r_build_ranger.status_code == 200
    char_ranger = r_build_ranger.get_json()["character"]
    assert char_ranger["species"] == "Lupin"
    assert char_ranger["background"] == "Mist Wanderer"
    assert char_ranger["subclass"] == "Hollow Warden"

    # 5. Check build endpoint with Dhampir + Grave Domain Cleric + Haunted One
    build_payload_cleric = {
        "choices_made": {
            "character_name": "Kallista",
            "species": "Dhampir",
            "background": "Haunted One",
            "classes": [
                {"class_name": "Cleric", "level": 3, "subclass": "Grave Domain"}
            ],
            "ability_scores": {
                "Strength": 10, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 12
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    }
    r_build_cleric = client.post("/api/v1/character/build", json=build_payload_cleric)
    assert r_build_cleric.status_code == 200
    char_cleric = r_build_cleric.get_json()["character"]
    assert char_cleric["species"] == "Dhampir"
    assert char_cleric["background"] == "Haunted One"
    assert char_cleric["subclass"] == "Grave Domain"
