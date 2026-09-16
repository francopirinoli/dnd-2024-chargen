"""
Tests for Modular Supplements API and SupplementManager
"""

import json
import pytest
from modules.supplement_manager import SupplementManager, get_supplement_manager


@pytest.fixture
def sample_supplement_payload():
    return {
        "manifest": {
            "id": "test-kobold-heroes",
            "title": "Tome of Heroes (Test)",
            "publisher": "Kobold Press",
            "version": "1.0.0",
            "compatibility": "2024",
            "description": "Test supplement with Beer Domain cleric.",
            "dependencies": ["core-phb-2024"]
        },
        "subclasses": [
            {
                "name": "Beer Domain",
                "class": "Cleric",
                "description": "Clerics of hospitality and celebration.",
                "source": "Tome of Heroes",
                "features_by_level": {
                    "3": {
                        "Intoxicating Blessing": "You can bless a beverage to bolster your allies."
                    }
                }
            }
        ],
        "species": [
            {
                "name": "Derro",
                "description": "A subterranean ancestry with innate uncanny magic.",
                "creature_type": "Humanoid",
                "size": "Small",
                "speed": 30,
                "languages": ["Common", "Undercommon"],
                "traits": {
                    "Sunlight Sensitivity": "Disadvantage on attack rolls in sunlight."
                }
            }
        ]
    }


def test_list_supplements(client):
    r = client.get("/api/v1/supplements")
    assert r.status_code == 200
    data = r.get_json()
    assert "supplements" in data
    core = next((s for s in data["supplements"] if s["id"] == "core-phb-2024"), None)
    assert core is not None
    assert core["is_core"] is True
    assert core["counts"]["classes"] == 12
    assert core["counts"]["subclasses"] == 48


def test_validate_and_install_supplement(client, sample_supplement_payload):
    # 1. Validate
    val_r = client.post("/api/v1/supplements/validate", json=sample_supplement_payload)
    assert val_r.status_code == 200
    val_data = val_r.get_json()
    assert val_data["errors"] == []
    assert val_data["valid"] is True
    assert val_data["counts"]["subclasses"] == 1
    assert val_data["counts"]["species"] == 1

    # 2. Install
    inst_r = client.post("/api/v1/supplements/install", json=sample_supplement_payload)
    assert inst_r.status_code == 200
    inst_data = inst_r.get_json()
    assert inst_data["success"] is True

    # 3. Verify in catalog
    cat_r = client.get("/api/v1/catalog/classes/Cleric/subclasses")
    assert cat_r.status_code == 200
    sc_list = cat_r.get_json()["subclasses"]
    beer = next((s for s in sc_list if s["name"] == "Beer Domain"), None)
    assert beer is not None
    assert beer["source_id"] == "test-kobold-heroes"

    # 4. Verify species in catalog
    sp_r = client.get("/api/v1/catalog/species")
    assert sp_r.status_code == 200
    species_list = sp_r.get_json()["species"]
    derro = next((s for s in species_list if s["name"] == "Derro"), None)
    assert derro is not None
    assert derro["source_id"] == "test-kobold-heroes"

    # 5. Build character using supplement subclass
    build_r = client.post("/api/v1/character/build", json={
        "choices_made": {
            "character_name": "Barley",
            "classes": [{"class_name": "Cleric", "level": 3, "subclass": "Beer Domain"}],
            "species": "Human",
            "background": "Acolyte",
            "ability_scores": {
                "Strength": 10, "Dexterity": 10, "Constitution": 14,
                "Intelligence": 10, "Wisdom": 16, "Charisma": 10
            }
        }
    })
    assert build_r.status_code == 200
    char = build_r.get_json()["character"]
    assert char["class"] == "Cleric"
    assert char["subclass"] == "Beer Domain"

    # 6. Uninstall
    del_r = client.delete("/api/v1/supplements/test-kobold-heroes")
    assert del_r.status_code == 200
    assert del_r.get_json()["success"] is True

    # 7. Verify removed
    cat_after = client.get("/api/v1/catalog/classes/Cleric/subclasses")
    beer_after = next((s for s in cat_after.get_json()["subclasses"] if s.get("source_id") == "test-kobold-heroes"), None)
    assert beer_after is None
