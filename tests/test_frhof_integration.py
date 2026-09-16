import json
import pytest
from pathlib import Path
from modules.supplement_manager import get_supplement_manager
from modules.data_loader import DataLoader
from modules.character_builder import CharacterBuilder
from app import app

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_frhof_supplement_package_validity():
    supp_path = REPO_ROOT / 'supplements' / 'forgotten-realms-heroes-of-faerun.json'
    assert supp_path.exists(), 'FRHoF supplement package missing'
    
    with open(supp_path, 'r', encoding='utf-8') as f:
        pkg = json.load(f)
        
    mgr = get_supplement_manager()
    valid, errors = mgr.validate_package(pkg)
    assert valid, f'Package schema validation failed: {errors}'
    
    # Assert counts
    assert len(pkg.get('subclasses', [])) == 8
    expected_subclasses = {
        'College of the Moon',
        'Knowledge Domain',
        'Banneret',
        'Oath of the Noble Genies',
        'Winter Walker',
        'Scion of the Three',
        'Spellfire Sorcery',
        'Bladesinger'
    }
    actual_subclasses = {sc['name'] for sc in pkg['subclasses']}
    assert actual_subclasses == expected_subclasses
    
    assert len(pkg.get('backgrounds', [])) == 18
    bg_names = {bg['name'] for bg in pkg['backgrounds']}
    assert 'Harper' in bg_names
    assert 'Dragon Cultist' in bg_names
    assert 'Spellfire Initiate' in bg_names
    assert 'Chondathan Freebooter' in bg_names
    assert 'Zhentarim Mercenary' in bg_names
    
    feats = pkg.get('feats', {})
    assert len(feats.get('origin_feats', {})) == 8
    assert len(feats.get('general_feats', {})) == 26
    assert 'Harper Agent' in feats['origin_feats']
    assert 'Spellfire Spark' in feats['origin_feats']
    assert 'Cold Caster' in feats['general_feats']
    assert 'Boon of Bloodshed' in feats['general_feats']
    assert 'Boon of the Soul Drinker' in feats['general_feats']
    
    assert len(pkg.get('spells', [])) == 19
    spell_names = {s['name'] for s in pkg['spells']}
    assert "Alustriel's Mooncloak" in spell_names
    assert "Blade of Disaster" in spell_names
    assert "Spellfire Flare" in spell_names
    assert "Wardaway" in spell_names
    
    # Assert spell class lists contain entries for major casters
    spell_lists = pkg.get('spell_class_lists', {})
    assert 'wizard' in spell_lists
    assert 'sorcerer' in spell_lists
    assert 'cleric' in spell_lists
    assert 'bard' in spell_lists
    assert 'druid' in spell_lists


def test_frhof_catalog_queries():
    dl = DataLoader()
    sources = ['forgotten-realms-heroes-of-faerun']
    
    # Subclasses for Wizard
    wizard_subclasses = dl.get_subclasses_for_class('Wizard', sources)
    assert 'Bladesinger' in wizard_subclasses
    bladesinger = wizard_subclasses['Bladesinger']
    assert 'Bladesong' in bladesinger['features_by_level']['3']
    
    # Subclasses for Bard
    bard_subclasses = dl.get_subclasses_for_class('Bard', sources)
    assert 'College of the Moon' in bard_subclasses
    
    # Subclasses for Paladin
    paladin_subclasses = dl.get_subclasses_for_class('Paladin', sources)
    assert 'Oath of the Noble Genies' in paladin_subclasses
    genie_spells_feature = paladin_subclasses['Oath of the Noble Genies']['features_by_level']['3']['Genie Spells']
    assert isinstance(genie_spells_feature, dict)
    assert 'Fly' in genie_spells_feature['spells']['9']
    
    # Subclasses for Cleric
    cleric_subclasses = dl.get_subclasses_for_class('Cleric', sources)
    assert 'Knowledge Domain' in cleric_subclasses
    kd_spells = cleric_subclasses['Knowledge Domain']['features_by_level']['3']['Knowledge Domain Spells']
    assert isinstance(kd_spells, dict)
    assert 'Identify' in kd_spells['spells']['3']
    
    # Backgrounds
    backgrounds = dl.get_backgrounds(sources)
    assert 'Harper' in backgrounds
    harper = backgrounds['Harper']
    assert harper['ability_score_increase']['total'] == 3
    assert set(harper['ability_score_increase']['options']) == {'Dexterity', 'Intelligence', 'Charisma'}
    
    # Feats
    all_feats = dl.get_feats(active_sources=sources)
    assert 'Harper Agent' in all_feats
    assert all_feats['Harper Agent']['category'].lower() == 'origin'
    assert 'Boon of Bloodshed' in all_feats
    
    # Spells
    spell = dl.get_spell_definition("Alustriel's Mooncloak", sources)
    assert spell is not None
    assert spell['level'] == 5
    assert spell['school'] == 'Abjuration'


def test_frhof_character_builder_bladesinger():
    choices = {
        'class': 'Wizard',
        'level': 3,
        'species': 'Elf',
        'subclass': 'Bladesinger',
        'background': 'Harper',
        'ability_scores': {
            'Strength': 8,
            'Dexterity': 16,
            'Constitution': 14,
            'Intelligence': 16,
            'Wisdom': 12,
            'Charisma': 10
        },
        'active_sources': ['forgotten-realms-heroes-of-faerun']
    }
    
    builder = CharacterBuilder()
    builder.apply_choices(choices)
    char = builder.to_character()
    
    assert char is not None
    assert char.get('class') == 'Wizard'
    assert char.get('level') == 3
    assert char.get('subclass') == 'Bladesinger'
    assert char.get('background') == 'Harper'
    
    subclass_features = [f['name'] if isinstance(f, dict) else f for f in char['features'].get('subclass', [])]
    assert 'Bladesong' in subclass_features
    assert 'Training in War and Song' in subclass_features


def test_frhof_character_builder_knowledge_cleric():
    choices = {
        'class': 'Cleric',
        'level': 3,
        'species': 'Human',
        'subclass': 'Knowledge Domain',
        'background': 'Mythalkeeper',
        'ability_scores': {
            'Strength': 10,
            'Dexterity': 12,
            'Constitution': 14,
            'Intelligence': 14,
            'Wisdom': 16,
            'Charisma': 10
        },
        'active_sources': ['forgotten-realms-heroes-of-faerun']
    }
    
    builder = CharacterBuilder()
    builder.apply_choices(choices)
    char = builder.to_character()
    
    assert char is not None
    assert char.get('subclass') == 'Knowledge Domain'
    subclass_features = [f['name'] if isinstance(f, dict) else f for f in char['features'].get('subclass', [])]
    assert 'Blessings of Knowledge' in subclass_features


def test_frhof_api_endpoints():
    client = app.test_client()
    
    # Supplements endpoint includes FRHoF
    resp = client.get('/api/v1/supplements')
    assert resp.status_code == 200
    data = resp.get_json()
    supps = data.get('supplements', [])
    frhof = next((s for s in supps if s['id'] == 'forgotten-realms-heroes-of-faerun'), None)
    assert frhof is not None
    assert frhof['title'] == 'Forgotten Realms: Heroes of Faerûn'
    assert frhof['counts']['subclasses'] == 8
    assert frhof['counts']['backgrounds'] == 18
    assert frhof['counts']['spells'] == 19
    assert frhof['counts']['feats'] == 34
    
    # Query Wizard subclasses with active source
    resp = client.get('/api/v1/catalog/classes/wizard/subclasses?sources=core-phb-2024,forgotten-realms-heroes-of-faerun')
    assert resp.status_code == 200
    w_data = resp.get_json()
    sc_names = [sc['name'] for sc in w_data.get('subclasses', [])]
    assert 'Bladesinger' in sc_names
    
    # Query backgrounds endpoint
    resp = client.get('/api/v1/catalog/backgrounds?sources=core-phb-2024,forgotten-realms-heroes-of-faerun')
    assert resp.status_code == 200
    data = resp.get_json()
    bgs = data.get('backgrounds', [])
    bg_names = [b['name'] for b in bgs]
    assert 'Harper' in bg_names
    assert 'Dragon Cultist' in bg_names
    assert 'Spellfire Initiate' in bg_names
