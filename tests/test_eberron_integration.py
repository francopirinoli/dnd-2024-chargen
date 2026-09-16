import json
import pytest
from pathlib import Path
from modules.supplement_manager import get_supplement_manager
from modules.data_loader import DataLoader
from modules.character_builder import CharacterBuilder

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_eberron_supplement_package_validity():
    supp_path = REPO_ROOT / 'supplements' / 'eberron-forge-of-the-artificer.json'
    assert supp_path.exists(), 'Eberron supplement package missing'
    
    with open(supp_path, 'r', encoding='utf-8') as f:
        pkg = json.load(f)
        
    mgr = get_supplement_manager()
    valid, errors = mgr.validate_package(pkg)
    assert valid, f'Package schema validation failed: {errors}'
    
    # Assert counts
    assert len(pkg.get('classes', [])) == 1
    assert pkg['classes'][0]['name'] == 'Artificer'
    assert len(pkg.get('subclasses', [])) == 5
    subclass_names = {sc['name'] for sc in pkg['subclasses']}
    assert subclass_names == {'Alchemist', 'Armorer', 'Artillerist', 'Battle Smith', 'Cartographer'}
    
    assert len(pkg.get('species', [])) == 5
    species_names = {sp['name'] for sp in pkg['species']}
    assert species_names == {'Changeling', 'Kalashtar', 'Khoravar', 'Shifter', 'Warforged'}
    
    assert len(pkg.get('species_variants', [])) == 4
    lineage_names = {sv['name'] for sv in pkg['species_variants']}
    assert lineage_names == {'Beasthide', 'Longtooth', 'Swiftstride', 'Wildhunt'}
    
    assert len(pkg.get('backgrounds', [])) == 17
    
    feats = pkg.get('feats', {})
    assert len(feats.get('origin_feats', {})) == 13
    assert len(feats.get('general_feats', {})) == 15
    assert 'Boon of Siberys' in feats['general_feats']
    
    assert len(pkg.get('spells', [])) == 1
    assert pkg['spells'][0]['name'] == 'Homunculus Servant'
    
    assert 'artificer' in pkg.get('spell_class_lists', {})


def test_eberron_catalog_queries():
    dl = DataLoader()
    sources = ['eberron-forge-of-the-artificer']
    
    classes = dl.get_classes(sources)
    assert 'Artificer' in classes
    art_data = classes['Artificer']
    assert art_data['hit_die'] == 8
    assert art_data['primary_ability'] == 'Intelligence'
    assert art_data['subclass_selection_level'] == 3
    
    subclasses = dl.get_subclasses_for_class('Artificer', sources)
    assert len(subclasses) == 5
    assert 'Cartographer' in subclasses
    assert 'Alchemist' in subclasses
    
    species = dl.get_species(sources)
    assert 'Warforged' in species
    assert 'Shifter' in species
    assert 'Changeling' in species
    
    variants = dl.supplement_manager.get_species_variants(sources)
    assert 'Beasthide' in variants
    
    backgrounds = dl.get_backgrounds(sources)
    assert 'House Cannith Heir' in backgrounds
    assert 'Inquisitive' in backgrounds
    assert 'Aberrant Heir' in backgrounds
    
    spell = dl.get_spell_definition('Homunculus Servant', sources)
    assert spell is not None
    assert spell['level'] == 2
    assert spell['school'] == 'Conjuration'


def test_artificer_character_builder_level1():
    choices = {
        'class': 'Artificer',
        'level': 1,
        'species': 'Warforged',
        'background': 'House Cannith Heir',
        'ability_scores': {
            'Strength': 10,
            'Dexterity': 14,
            'Constitution': 14,
            'Intelligence': 16,
            'Wisdom': 12,
            'Charisma': 8
        },
        'active_sources': ['eberron-forge-of-the-artificer']
    }
    
    builder = CharacterBuilder()
    builder.apply_choices(choices)
    char = builder.to_character()
    
    assert char['class'] == 'Artificer'
    assert char['level'] == 1
    # Artificer gets 2 1st-level spell slots at level 1
    spell_slots = char.get('spell_slots', {})
    assert spell_slots.get('1st') == 2, f'Expected 2 1st-level spell slots, got {spell_slots}'
    
    # Hit Points: 8 (hit die) + Con mod (+2) = 10
    assert char['combat']['hit_points']['maximum'] == 10
    
    # Saving throws
    saving_throws = char.get('proficiencies', {}).get('saving_throws', [])
    assert 'Constitution' in saving_throws
    assert 'Intelligence' in saving_throws
    assert char['abilities']['constitution']['saving_throw_proficient'] is True
    assert char['abilities']['intelligence']['saving_throw_proficient'] is True
    
    # Armor training
    armor_proficiencies = char.get('proficiencies', {}).get('armor', [])
    assert any('medium' in a.lower() for a in armor_proficiencies)
    assert any('shield' in a.lower() for a in armor_proficiencies)


def test_artificer_cartographer_level3():
    choices = {
        'class': 'Artificer',
        'level': 3,
        'subclass': 'Cartographer',
        'species': 'Khoravar',
        'background': 'Archaeologist',
        'ability_scores': {
            'Strength': 8,
            'Dexterity': 14,
            'Constitution': 14,
            'Intelligence': 16,
            'Wisdom': 12,
            'Charisma': 10
        },
        'active_sources': ['eberron-forge-of-the-artificer']
    }
    
    builder = CharacterBuilder()
    builder.apply_choices(choices)
    char = builder.to_character()
    
    assert char['subclass'] == 'Cartographer'
    assert char['level'] == 3
    # At level 3, Artificer has 3 1st-level spell slots
    spell_slots = char.get('spell_slots', {})
    assert spell_slots.get('1st') == 3, f'Expected 3 1st-level spell slots, got {spell_slots}'
    
    # Subclass features at level 3
    subclass_features = char.get('subclass_data', {}).get('features_by_level', {}).get('3', {})
    assert "Adventurer's Atlas" in subclass_features
    assert 'Mapping Magic' in subclass_features


def test_warforged_traits():
    builder = CharacterBuilder()
    builder.apply_choices({
        'class': 'Fighter',
        'level': 1,
        'species': 'Warforged',
        'background': 'House Cannith Heir',
        'active_sources': ['eberron-forge-of-the-artificer']
    })
    char = builder.to_character()
    assert char['species'] == 'Warforged'
    sp_features = [f['name'] if isinstance(f, dict) else f for f in char['features']['species']]
    assert 'Construct Resilience' in sp_features
    assert 'Integrated Protection' in sp_features


def test_shifter_with_lineage():
    builder = CharacterBuilder()
    builder.apply_choices({
        'class': 'Barbarian',
        'level': 1,
        'species': 'Shifter',
        'lineage': 'Beasthide',
        'background': 'House Tharashk Heir',
        'active_sources': ['eberron-forge-of-the-artificer']
    })
    char = builder.to_character()
    assert char['species'] == 'Shifter'
    assert char.get('lineage') == 'Beasthide'
    sp_features = [f['name'] if isinstance(f, dict) else f for f in char['features']['species']]
    assert 'Shifting' in sp_features
    lineage_features = [f['name'] if isinstance(f, dict) else f for f in char['features']['lineage']]
    assert 'Beasthide Shifting' in lineage_features


def test_house_cannith_heir_background():
    builder = CharacterBuilder()
    builder.apply_choices({
        'class': 'Wizard',
        'level': 1,
        'species': 'Human',
        'background': 'House Cannith Heir',
        'active_sources': ['eberron-forge-of-the-artificer']
    })
    char = builder.to_character()
    assert char['background'] == 'House Cannith Heir'
    bg_feats = [f.get('name') if isinstance(f, dict) else f for f in char['features'].get('feats', [])]
    assert 'Mark of Making' in bg_feats
