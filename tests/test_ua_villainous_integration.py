"""Integration tests for Unearthed Arcana: Villainous Options supplement package."""

import pytest
from app import app
from modules.supplement_manager import get_supplement_manager


def test_ua_villainous_manifest():
    mgr = get_supplement_manager()
    mgr.reload_all()
    ua_manifest = mgr.manifests.get("ua-2026-villainous-options")
    assert ua_manifest is not None
    assert ua_manifest["title"] == "Unearthed Arcana: Villainous Options"
    assert ua_manifest["publisher"] == "Wizards of the Coast (Playtest)"
    assert ua_manifest["version"] == "1.0.0"

    supplements = mgr.list_supplements()
    ua_entry = next((s for s in supplements if s["id"] == "ua-2026-villainous-options"), None)
    assert ua_entry is not None
    assert ua_entry["counts"]["subclasses"] == 7
    assert ua_entry["counts"]["feats"] == 19


def test_ua_villainous_subclasses_catalog():
    mgr = get_supplement_manager()

    # 1. Path of Lament (Barbarian)
    barb_subs = mgr.get_subclasses_for_class("Barbarian")
    assert "Path of Lament" in barb_subs
    lament = barb_subs["Path of Lament"]
    assert "features_by_level" in lament
    assert "Banshee's Wail" in lament["features_by_level"]["3"]
    assert "Commune with the Dead" in lament["features_by_level"]["6"]
    assert "Otherworldly Anguish" in lament["features_by_level"]["10"]
    assert "Sorrow Form" in lament["features_by_level"]["14"]

    # 2. Pestilence Domain (Cleric)
    cleric_subs = mgr.get_subclasses_for_class("Cleric")
    assert "Pestilence Domain" in cleric_subs
    pesti = cleric_subs["Pestilence Domain"]
    assert "Blight Weaver" in pesti["features_by_level"]["3"]
    assert "Plague Blessing" in pesti["features_by_level"]["3"]
    assert "Virulent Burst" in pesti["features_by_level"]["6"]
    assert "Vermin Form" in pesti["features_by_level"]["17"]

    # 3. Circle of the Titan (Druid - Revised)
    druid_subs = mgr.get_subclasses_for_class("Druid")
    assert "Circle of the Titan" in druid_subs
    titan = druid_subs["Circle of the Titan"]
    assert "Circle of the Titan Spells" in titan["features_by_level"]["3"]
    assert "Titan Form" in titan["features_by_level"]["3"]
    assert "Dire Impact" in titan["features_by_level"]["6"]
    assert "Primal Havoc" in titan["features_by_level"]["10"]
    assert "Monstrous Appetite" in titan["features_by_level"]["14"]

    # 4. Hell Knight (Fighter - Revised)
    fighter_subs = mgr.get_subclasses_for_class("Fighter")
    assert "Hell Knight" in fighter_subs
    hell_k = fighter_subs["Hell Knight"]
    assert "Diabolical Gift" in hell_k["features_by_level"]["3"]
    assert "Hell-Forged Weapon" in hell_k["features_by_level"]["3"]
    assert "Infernal Wound" in hell_k["features_by_level"]["3"]
    assert "Advanced Wounds" in hell_k["features_by_level"]["7"]
    assert "Infernal Equipment" in hell_k["features_by_level"]["7"]
    assert "Hellfire Surge" in hell_k["features_by_level"]["10"]
    assert "Devil's Misfortune" in hell_k["features_by_level"]["15"]
    assert "Infernal Bargain" in hell_k["features_by_level"]["18"]

    # 5. Warrior of Venom (Monk)
    monk_subs = mgr.get_subclasses_for_class("Monk")
    assert "Warrior of Venom" in monk_subs
    venom = monk_subs["Warrior of Venom"]
    assert "Envenom Weapon" in venom["features_by_level"]["3"]
    assert "Potent Arsenal" in venom["features_by_level"]["3"]
    assert "Toxic Touch" in venom["features_by_level"]["6"]
    assert "Toxin Refiner" in venom["features_by_level"]["11"]
    assert "Toxic Blood" in venom["features_by_level"]["11"]
    assert "Hallucinogenic Breath" in venom["features_by_level"]["17"]

    # 6. Demonic Sorcery (Sorcerer - Revised)
    sorc_subs = mgr.get_subclasses_for_class("Sorcerer")
    assert "Demonic Sorcery" in sorc_subs
    demonic = sorc_subs["Demonic Sorcery"]
    assert "Abyssal Rupture" in demonic["features_by_level"]["3"]
    assert "Demonic Spells" in demonic["features_by_level"]["3"]
    assert "Abyssal Realm" in demonic["features_by_level"]["6"]
    assert "Abyssal Conduit" in demonic["features_by_level"]["14"]
    assert "Abyssal Explosion" in demonic["features_by_level"]["18"]

    # 7. Primordial Patron (Warlock)
    warlock_subs = mgr.get_subclasses_for_class("Warlock")
    assert "Primordial Patron" in warlock_subs
    primordial = warlock_subs["Primordial Patron"]
    assert "Elemental Node" in primordial["features_by_level"]["3"]
    assert "Elemental Spells" in primordial["features_by_level"]["3"]
    assert "Elemental Haven" in primordial["features_by_level"]["6"]
    assert "Primeval Protection" in primordial["features_by_level"]["10"]
    assert "Elemental Harbinger" in primordial["features_by_level"]["14"]


def test_ua_villainous_feats_catalog():
    mgr = get_supplement_manager()

    # Origin Feats
    origin_feats = mgr.get_feats("origin")
    expected_origin = ["Atoner's Grace", "Raised by Cultists", "Trapper", "Underhanded"]
    for feat in expected_origin:
        assert feat in origin_feats, f"Missing origin feat: {feat}"
        assert origin_feats[feat]["category"] == "Origin"

    # General / Paths of Villainy Feats
    general_feats = mgr.get_feats("general")
    expected_death_knight = [
        "Death Knight Initiate",
        "Dread Authority",
        "Harbinger of Doom",
        "Deathly Presence",
        "Unholy Steed",
        "Death Knight Ascension"
    ]
    for feat in expected_death_knight:
        assert feat in general_feats, f"Missing Death Knight feat: {feat}"
        assert general_feats[feat]["category"] == "General"

    expected_lich = [
        "Lich Initiate",
        "Arcane Restoration",
        "Transfer Life",
        "Undead Grasp",
        "Lich Ascension"
    ]
    for feat in expected_lich:
        assert feat in general_feats, f"Missing Lich feat: {feat}"
        assert general_feats[feat]["category"] == "General"

    # Epic Boons
    expected_epic = [
        "Boon of the Bandit King",
        "Boon of the Cleansed Heart",
        "Boon of the Hunter's Eye",
        "Boon of Unwavering Devotion"
    ]
    for feat in expected_epic:
        assert feat in general_feats, f"Missing Epic Boon feat: {feat}"
        assert general_feats[feat]["category"] == "Epic Boon"


def test_ua_villainous_eldritch_invocations():
    mgr = get_supplement_manager()
    invocations = mgr.get_eldritch_invocations()

    assert "Elemental Overflow" in invocations
    assert invocations["Elemental Overflow"]["prerequisite_level"] == 5
    assert "Repeatable" in invocations["Elemental Overflow"]["notes"]

    assert "Elemental Transmutation" in invocations
    assert invocations["Elemental Transmutation"]["prerequisite_level"] == 2

    # Verify reference API
    client = app.test_client()
    r = client.get("/api/v1/catalog/reference/eldritch_invocations")
    assert r.status_code == 200
    ref_inv = r.get_json()
    assert "Elemental Overflow" in ref_inv
    assert "Elemental Transmutation" in ref_inv


def test_ua_villainous_character_building():
    client = app.test_client()

    # 1. Barbarian: Path of Lament
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Lament Rager",
            "species": "Human",
            "background": "Soldier",
            "classes": [{"class_name": "Barbarian", "level": 3, "subclass": "Path of Lament"}],
            "ability_scores": {"Strength": 16, "Dexterity": 14, "Constitution": 14, "Intelligence": 10, "Wisdom": 12, "Charisma": 8},
            "background_bonuses": {"Strength": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Path of Lament"

    # 2. Cleric: Pestilence Domain
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Plague Doctor",
            "species": "Human",
            "background": "Acolyte",
            "classes": [{"class_name": "Cleric", "level": 3, "subclass": "Pestilence Domain"}],
            "ability_scores": {"Strength": 10, "Dexterity": 12, "Constitution": 14, "Intelligence": 12, "Wisdom": 16, "Charisma": 10},
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Pestilence Domain"

    # 3. Druid: Circle of the Titan
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Titan Shifter",
            "species": "Human",
            "background": "Hermit",
            "classes": [{"class_name": "Druid", "level": 3, "subclass": "Circle of the Titan"}],
            "ability_scores": {"Strength": 10, "Dexterity": 14, "Constitution": 14, "Intelligence": 10, "Wisdom": 16, "Charisma": 10},
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Circle of the Titan"

    # 4. Fighter: Hell Knight
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Hellish Knight",
            "species": "Human",
            "background": "Soldier",
            "classes": [{"class_name": "Fighter", "level": 3, "subclass": "Hell Knight"}],
            "ability_scores": {"Strength": 16, "Dexterity": 12, "Constitution": 14, "Intelligence": 10, "Wisdom": 10, "Charisma": 14},
            "background_bonuses": {"Strength": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Hell Knight"

    # 5. Monk: Warrior of Venom
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Venomous Striker",
            "species": "Human",
            "background": "Criminal",
            "classes": [{"class_name": "Monk", "level": 3, "subclass": "Warrior of Venom"}],
            "ability_scores": {"Strength": 10, "Dexterity": 16, "Constitution": 14, "Intelligence": 10, "Wisdom": 16, "Charisma": 8},
            "background_bonuses": {"Dexterity": 2, "Wisdom": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Warrior of Venom"

    # 6. Sorcerer: Demonic Sorcery
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Abyssal Scion",
            "species": "Human",
            "background": "Sage",
            "classes": [{"class_name": "Sorcerer", "level": 3, "subclass": "Demonic Sorcery"}],
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 12, "Wisdom": 10, "Charisma": 16},
            "background_bonuses": {"Charisma": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Demonic Sorcery"

    # 7. Warlock: Primordial Patron
    r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Elemental Herald",
            "species": "Human",
            "background": "Sage",
            "classes": [{"class_name": "Warlock", "level": 3, "subclass": "Primordial Patron"}],
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 12, "Wisdom": 10, "Charisma": 16},
            "background_bonuses": {"Charisma": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    char = r.get_json()["character"]
    assert char["subclass"] == "Primordial Patron"


def test_ua_villainous_warlock_invocation_derived():
    client = app.test_client()
    r = client.post("/api/v1/character/derived", json={
        "view": "invocation_management",
        "choices_made": {
            "name": "Elemental Warlock",
            "class": "Warlock",
            "level": 5,
            "classes": [{"class_name": "Warlock", "level": 5, "subclass": "Primordial Patron"}],
            "species": "Human",
            "background": "Sage",
            "ability_scores": {"Strength": 8, "Dexterity": 14, "Constitution": 14, "Intelligence": 12, "Wisdom": 10, "Charisma": 16},
            "background_bonuses": {"Charisma": 2, "Constitution": 1}
        }
    })
    assert r.status_code == 200
    data = r.get_json()["data"]
    avail_names = {inv["name"] for inv in data.get("available_invocations", [])}
    assert "Elemental Overflow" in avail_names
    assert "Elemental Transmutation" in avail_names

