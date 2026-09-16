import pytest
from modules.supplement_manager import get_supplement_manager
from modules.character_builder import CharacterBuilder
from modules.data_loader import DataLoader


def test_abh_supplement_manifest_and_counts():
    mgr = get_supplement_manager()
    mgr.reload_all()
    manifest = mgr.manifests.get("astarions-book-of-hungers")
    assert manifest is not None
    assert manifest["title"] == "Astarion's Book of Hungers"

    supplements = mgr.list_supplements()
    abh_entry = next((s for s in supplements if s["id"] == "astarions-book-of-hungers"), None)
    assert abh_entry is not None
    assert abh_entry["counts"]["species"] == 1
    assert abh_entry["counts"]["backgrounds"] == 3
    assert abh_entry["counts"]["feats"] == 16


def test_abh_dhampir_species():
    mgr = get_supplement_manager()
    dhampir = mgr.get_species_detail("Dhampir")
    assert dhampir is not None
    assert dhampir["name"] == "Dhampir"
    assert dhampir["creature_type"] == "Humanoid"
    assert dhampir["speed"] == 35
    assert dhampir["darkvision"] == 60
    assert "Darkvision" in dhampir["traits"]
    assert "Spider Climb" in dhampir["traits"]
    assert "Trace of Undeath" in dhampir["traits"]
    assert "Vampiric Bite" in dhampir["traits"]


def test_abh_backgrounds():
    mgr = get_supplement_manager()
    for bg_name, feat_expected in [
        ("Carouser", "Tireless Reveler"),
        ("Vampire Devotee", "Vampire's Plaything"),
        ("Vampire Survivor", "Vampire Hunter"),
    ]:
        bg = mgr.get_background(bg_name)
        assert bg is not None
        origin_feats = [e["feat"] for e in bg["effects"] if e.get("type") == "grant_origin_feat"]
        assert origin_feats == [feat_expected]


def test_abh_character_builder_integration():
    builder = CharacterBuilder()
    assert builder.set_species("Dhampir") is True
    assert builder.set_class("Rogue") is True
    assert builder.set_background("Carouser") is True

    char = builder.character_data
    assert char["species"] == "Dhampir"
    assert char["class"] == "Rogue"
    assert char["background"] == "Carouser"
    assert char["speed"] == 35

    feat_names = [f["name"] for f in char["features"]["feats"]]
    assert "Tireless Reveler" in feat_names

    skills = char["proficiencies"]["skills"]
    assert "Deception" in skills
    assert "Persuasion" in skills
