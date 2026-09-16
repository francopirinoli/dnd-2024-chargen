"""
Integration tests for the Unearthed Arcana: Underdark Options supplement.
Tests manifest discovery, subclasses, species, feats, spells,
and CharacterBuilder / API catalog integration.
"""

import pytest
from app import app
from modules.supplement_manager import get_supplement_manager
from modules.character_builder import CharacterBuilder


def test_ua_underdark_manifest_and_indexing():
    mgr = get_supplement_manager()
    mgr.reload_all()
    manifest = mgr.manifests.get("ua-2026-underdark-options")
    assert manifest is not None
    assert manifest["title"] == "Unearthed Arcana: Underdark Options"
    assert manifest["publisher"] == "Wizards of the Coast (Playtest)"
    assert manifest["compatibility"] == "2024"

    supplements = mgr.list_supplements()
    ua_entry = next((s for s in supplements if s["id"] == "ua-2026-underdark-options"), None)
    assert ua_entry is not None
    assert ua_entry["counts"]["subclasses"] == 6
    assert ua_entry["counts"]["species"] == 5
    assert ua_entry["counts"]["feats"] == 5
    assert ua_entry["counts"]["spells"] == 1


def test_ua_underdark_subclasses():
    mgr = get_supplement_manager()

    # 1. Path of Unlight (Barbarian)
    unlight = mgr.get_subclass("Barbarian", "Path of Unlight")
    assert unlight is not None
    assert "Radiant Rage" in unlight["features_by_level"]["3"]
    assert "Unlight Revelation" in unlight["features_by_level"]["6"]
    assert "Infectious Unlight" in unlight["features_by_level"]["10"]
    assert "Harbinger of Unlight" in unlight["features_by_level"]["10"]
    assert "Brilliant Rage" in unlight["features_by_level"]["14"]

    # 2. Freedom Domain (Cleric)
    freedom = mgr.get_subclass("Cleric", "Freedom Domain")
    assert freedom is not None
    assert "Freedom Domain Spells" in freedom["features_by_level"]["3"]
    assert "Invoke Liberty" in freedom["features_by_level"]["3"]
    assert "Unencumbered Grace" in freedom["features_by_level"]["3"]
    assert "Unstoppable" in freedom["features_by_level"]["6"]
    assert "Avatar of Freedom" in freedom["features_by_level"]["17"]

    # 3. Circle of Spores (Druid)
    spores = mgr.get_subclass("Druid", "Circle of Spores")
    assert spores is not None
    assert "Circle Spells" in spores["features_by_level"]["3"]
    assert "Halo of Spores" in spores["features_by_level"]["3"]
    assert "Symbiotic Entity" in spores["features_by_level"]["3"]
    assert "Fungal Infestation" in spores["features_by_level"]["6"]
    assert "Explosive Burst" in spores["features_by_level"]["10"]
    assert "Fungal Body" in spores["features_by_level"]["14"]

    # 4. House Agent (Rogue)
    house_agent = mgr.get_subclass("Rogue", "House Agent")
    assert house_agent is not None
    assert "House Insignia" in house_agent["features_by_level"]["3"]
    assert "Charming Presence" in house_agent["features_by_level"]["3"]
    assert "Backstab" in house_agent["features_by_level"]["9"]
    assert "Infiltration Partner" in house_agent["features_by_level"]["13"]
    assert "Silver Tongue" in house_agent["features_by_level"]["13"]
    assert "Subtle Manipulator" in house_agent["features_by_level"]["17"]

    # 5. Faerzress Sorcery (Sorcerer)
    faerzress = mgr.get_subclass("Sorcerer", "Faerzress Sorcery")
    assert faerzress is not None
    assert "Faerzress Spells" in faerzress["features_by_level"]["3"]
    assert "Faerzress Zone" in faerzress["features_by_level"]["3"]
    assert "Immunity to Faerzress" in faerzress["features_by_level"]["3"]
    assert "Faerzress Affinity" in faerzress["features_by_level"]["6"]
    assert "Faerzress Spell" in faerzress["features_by_level"]["14"]
    assert "Faerzress Step" in faerzress["features_by_level"]["14"]
    assert "Faerzress Form" in faerzress["features_by_level"]["18"]

    # 6. Imaskarcanist (Wizard)
    imaskar = mgr.get_subclass("Wizard", "Imaskarcanist")
    assert imaskar is not None
    assert "Unlight Adept" in imaskar["features_by_level"]["3"]
    assert "Unlight Invigoration" in imaskar["features_by_level"]["3"]
    assert "Unlight Restoration" in imaskar["features_by_level"]["6"]
    assert "Secrets of Deep Imaskar" in imaskar["features_by_level"]["10"]
    assert "Doom of Unlight" in imaskar["features_by_level"]["14"]


def test_ua_underdark_species():
    mgr = get_supplement_manager()

    # 1. Deep Imaskari
    imaskari = mgr.get_species_detail("Deep Imaskari")
    assert imaskari is not None
    assert imaskari["creature_type"] == "Humanoid"
    assert imaskari["speed"] == 30
    assert "Photoresistant" in imaskari["traits"]
    assert "Resourceful" in imaskari["traits"]
    assert "Unluminescent" in imaskari["traits"]
    assert "Aura of Unlight" in imaskari["traits"]

    # 2. Drider
    drider = mgr.get_species_detail("Drider")
    assert drider is not None
    assert drider["creature_type"] == "Monstrosity"
    assert drider["speed"] == 30
    assert drider["darkvision"] == 120
    assert "Arachnid Build" in drider["traits"]
    assert "Spells of the Spider Queen" in drider["traits"]
    assert "Spider Climb" in drider["traits"]
    assert "Web Walker" in drider["traits"]

    # 3. Illithidkin
    illithidkin = mgr.get_species_detail("Illithidkin")
    assert illithidkin is not None
    assert illithidkin["creature_type"] == "Humanoid"
    assert illithidkin["darkvision"] == 120
    assert "Psionic Aptitude" in illithidkin["traits"]
    assert "Sharpened Mind" in illithidkin["traits"]
    assert "Telepathy" in illithidkin["traits"]

    # 4. Kuo-Toa
    kuotoa = mgr.get_species_detail("Kuo-Toa")
    assert kuotoa is not None
    assert kuotoa["creature_type"] == "Humanoid"
    assert "Amphibious" in kuotoa["traits"]
    assert "Slippery" in kuotoa["traits"]
    assert "Deific Manifestation" in kuotoa["traits"]

    # 5. Myconid
    myconid = mgr.get_species_detail("Myconid")
    assert myconid is not None
    assert myconid["creature_type"] == "Plant"
    assert myconid["darkvision"] == 120
    assert "Telepathy" in myconid["traits"]
    assert "Rapport Spores" in myconid["traits"]
    assert "Skill Meld" in myconid["traits"]


def test_ua_underdark_feats():
    mgr = get_supplement_manager()
    feats = mgr.get_feats("general")

    expected_feats = [
        "Tadpole Host",
        "Illithid Thrallmaker",
        "Tadpole's Safeguard",
        "Ulitharid's Might",
        "Full Ceremorphosis"
    ]
    for name in expected_feats:
        assert name in feats, f"Missing feat: {name}"
        f = feats[name]
        assert f["category"] in ("General", "general")
        assert f.get("source") == "Unearthed Arcana: Underdark Options" or f.get("source_id") == "ua-2026-underdark-options"

    # Verify Ceremorphosis prerequisite progression
    assert "Level 4+" in feats["Tadpole Host"]["prerequisite"]
    assert "Tadpole Host Feat" in feats["Illithid Thrallmaker"]["prerequisite"]
    assert "Tadpole Host Feat" in feats["Tadpole's Safeguard"]["prerequisite"]
    assert "Tadpole Host Feat" in feats["Ulitharid's Might"]["prerequisite"]
    assert "Level 12+" in feats["Full Ceremorphosis"]["prerequisite"]
    assert feats["Full Ceremorphosis"]["repeatable"] is True


def test_ua_underdark_spells():
    mgr = get_supplement_manager()
    spell = mgr.get_spell_definition("Mind Blast")
    assert spell is not None
    assert spell["level"] == 6
    assert spell["school"] == "Evocation"
    assert "60-foot" in spell["range"]
    assert spell["classes"] == ["Sorcerer", "Warlock", "Wizard"]


def test_ua_underdark_character_building_and_api():
    client = app.test_client()

    # 1. API supplement list
    r_supp = client.get("/api/v1/supplements")
    assert r_supp.status_code == 200
    supp_list = r_supp.get_json()["supplements"]
    ua_manifest = next((s for s in supp_list if s["id"] == "ua-2026-underdark-options"), None)
    assert ua_manifest is not None

    # 2. Species catalog
    r_spec = client.get("/api/v1/catalog/species")
    assert r_spec.status_code == 200
    species_names = {s["name"] for s in r_spec.get_json()["species"]}
    assert {"Deep Imaskari", "Drider", "Illithidkin", "Kuo-Toa", "Myconid"}.issubset(species_names)

    # 3. Spells definition and feats catalog
    r_spell = client.get("/api/v1/catalog/spells/definitions/Mind%20Blast")
    assert r_spell.status_code == 200
    assert r_spell.get_json()["name"] == "Mind Blast"

    r_feats = client.get("/api/v1/catalog/feats?type=general")
    assert r_feats.status_code == 200
    feat_names = {f["name"] for f in r_feats.get_json()["feats"]}
    assert {"Tadpole Host", "Full Ceremorphosis"}.issubset(feat_names)

    # 4. Build Barbarian: Path of Unlight + Deep Imaskari
    build_payload_barb = {
        "choices_made": {
            "character_name": "Imaskar Rager",
            "species": "Deep Imaskari",
            "background": "Soldier",
            "classes": [
                {"class_name": "Barbarian", "level": 3, "subclass": "Path of Unlight"}
            ],
            "ability_scores": {
                "Strength": 16, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 12, "Charisma": 8
            },
            "background_bonuses": {"Strength": 2, "Constitution": 1}
        }
    }
    r_build_barb = client.post("/api/v1/character/build", json=build_payload_barb)
    assert r_build_barb.status_code == 200
    char_barb = r_build_barb.get_json()["character"]
    assert char_barb["species"] == "Deep Imaskari"
    assert char_barb["subclass"] == "Path of Unlight"

    # 5. Build Druid: Circle of Spores + Myconid
    build_payload_druid = {
        "choices_made": {
            "character_name": "Spore Caller",
            "species": "Myconid",
            "background": "Hermit",
            "classes": [
                {"class_name": "Druid", "level": 3, "subclass": "Circle of Spores"}
            ],
            "ability_scores": {
                "Strength": 10, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 10
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    }
    r_build_druid = client.post("/api/v1/character/build", json=build_payload_druid)
    assert r_build_druid.status_code == 200
    char_druid = r_build_druid.get_json()["character"]
    assert char_druid["species"] == "Myconid"
    assert char_druid["subclass"] == "Circle of Spores"

    # 6. Build Cleric: Freedom Domain + Kuo-Toa
    build_payload_cleric = {
        "choices_made": {
            "character_name": "Kuo-Toa Liberator",
            "species": "Kuo-Toa",
            "background": "Acolyte",
            "classes": [
                {"class_name": "Cleric", "level": 3, "subclass": "Freedom Domain"}
            ],
            "ability_scores": {
                "Strength": 12, "Dexterity": 12, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 10
            },
            "background_bonuses": {"Wisdom": 2, "Constitution": 1}
        }
    }
    r_build_cleric = client.post("/api/v1/character/build", json=build_payload_cleric)
    assert r_build_cleric.status_code == 200
    char_cleric = r_build_cleric.get_json()["character"]
    assert char_cleric["species"] == "Kuo-Toa"
    assert char_cleric["subclass"] == "Freedom Domain"

    # 7. Build Rogue: House Agent + Drider
    build_payload_rogue = {
        "choices_made": {
            "character_name": "House Assassin",
            "species": "Drider",
            "background": "Criminal",
            "classes": [
                {"class_name": "Rogue", "level": 3, "subclass": "House Agent"}
            ],
            "ability_scores": {
                "Strength": 10, "Dexterity": 16, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 14
            },
            "background_bonuses": {"Dexterity": 2, "Constitution": 1}
        }
    }
    r_build_rogue = client.post("/api/v1/character/build", json=build_payload_rogue)
    assert r_build_rogue.status_code == 200
    char_rogue = r_build_rogue.get_json()["character"]
    assert char_rogue["species"] == "Drider"
    assert char_rogue["subclass"] == "House Agent"

    # 8. Build Sorcerer: Faerzress Sorcery + Illithidkin
    build_payload_sorc = {
        "choices_made": {
            "character_name": "Faerzress Mutant",
            "species": "Illithidkin",
            "background": "Sage",
            "classes": [
                {"class_name": "Sorcerer", "level": 3, "subclass": "Faerzress Sorcery"}
            ],
            "ability_scores": {
                "Strength": 8, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 12, "Wisdom": 10, "Charisma": 16
            },
            "background_bonuses": {"Charisma": 2, "Constitution": 1}
        }
    }
    r_build_sorc = client.post("/api/v1/character/build", json=build_payload_sorc)
    assert r_build_sorc.status_code == 200
    char_sorc = r_build_sorc.get_json()["character"]
    assert char_sorc["species"] == "Illithidkin"
    assert char_sorc["subclass"] == "Faerzress Sorcery"

    # 9. Build Wizard: Imaskarcanist + Deep Imaskari
    build_payload_wiz = {
        "choices_made": {
            "character_name": "Deep Imaskar Mage",
            "species": "Deep Imaskari",
            "background": "Sage",
            "classes": [
                {"class_name": "Wizard", "level": 3, "subclass": "Imaskarcanist"}
            ],
            "ability_scores": {
                "Strength": 8, "Dexterity": 14, "Constitution": 14,
                "Intelligence": 16, "Wisdom": 12, "Charisma": 10
            },
            "background_bonuses": {"Intelligence": 2, "Constitution": 1}
        }
    }
    r_build_wiz = client.post("/api/v1/character/build", json=build_payload_wiz)
    assert r_build_wiz.status_code == 200
    char_wiz = r_build_wiz.get_json()["character"]
    assert char_wiz["species"] == "Deep Imaskari"
    assert char_wiz["subclass"] == "Imaskarcanist"
