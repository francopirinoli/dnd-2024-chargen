"""
build_frhof_supplement.py
Assembles supplements/forgotten-realms-heroes-of-faerun.json from the scraped FRHoF dataset.
Conforms strictly to models/supplement_schema.json.
"""

import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

SCRAPED_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "C:/Users/Ventas/.gemini/antigravity/brain/689aface-04ea-4698-95fa-ef2b1cc59d75/scratch/scraped_frhof.json"
)
if not os.path.exists(SCRAPED_DATA_PATH):
    # Fallback to local scratch if path differs
    SCRAPED_DATA_PATH = os.path.abspath("C:/Users/Ventas/.gemini/antigravity/brain/689aface-04ea-4698-95fa-ef2b1cc59d75/scratch/scraped_frhof.json")

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supplements", "forgotten-realms-heroes-of-faerun.json")

def clean_str(s: str) -> str:
    if not s:
        return ""
    return s.replace('&apos;', "'").replace('&#39;', "'").replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').strip()

def build_frhof():
    with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # Subclass spell mapping
    subclass_spells_map = {
        "Knowledge Domain": {
            "description": "When you reach a Cleric level specified in the Knowledge Domain Spells table, you thereafter always have the listed spells prepared.",
            "spells": {
                "3": ["Command", "Comprehend Languages", "Detect Magic", "Detect Thoughts", "Identify", "Mind Spike"],
                "5": ["Dispel Magic", "Nondetection", "Tongues"],
                "7": ["Arcane Eye", "Banishment", "Confusion"],
                "9": ["Legend Lore", "Scrying", "Synaptic Static"]
            }
        },
        "Oath of the Noble Genies": {
            "description": "When you reach a Paladin level specified in the Genie Spells table, you thereafter always have the listed spells prepared.",
            "spells": {
                "3": ["Chromatic Orb", "Elementalism", "Thunderous Smite"],
                "5": ["Mirror Image", "Phantasmal Force"],
                "9": ["Fly", "Gaseous Form"],
                "13": ["Conjure Minor Elementals", "Summon Elemental"],
                "17": ["Banishing Smite", "Contact Other Plane"]
            }
        },
        "Winter Walker": {
            "description": "When you reach a Ranger level specified in the Winter Walker Spells table, you thereafter always have the listed spells prepared.",
            "spells": {
                "3": ["Ice Knife"],
                "5": ["Hold Person"],
                "9": ["Remove Curse"],
                "13": ["Ice Storm"],
                "17": ["Cone of Cold"]
            }
        },
        "Spellfire Sorcery": {
            "description": "When you reach a Sorcerer level specified in the Spellfire Spells table, you thereafter always have the listed spells prepared.",
            "spells": {
                "3": ["Cure Wounds", "Guiding Bolt", "Lesser Restoration", "Scorching Ray"],
                "5": ["Aura of Vitality", "Dispel Magic"],
                "7": ["Fire Shield", "Wall of Fire"],
                "9": ["Greater Restoration", "Flame Strike"]
            }
        }
    }

    # 1. Subclasses
    subclasses = []
    class_mapping = {
        'bard': 'Bard',
        'cleric': 'Cleric',
        'fighter': 'Fighter',
        'paladin': 'Paladin',
        'ranger': 'Ranger',
        'rogue': 'Rogue',
        'sorcerer': 'Sorcerer',
        'wizard': 'Wizard'
    }

    for cat, cls_name in class_mapping.items():
        for slug, item in raw_data.get(cat, {}).items():
            title = clean_str(item['title'])
            text = clean_str(item['text'])
            
            # Extract description
            desc_parts = []
            for line in text.splitlines():
                if re.match(r'^Level\s+\d+:', line.strip()):
                    break
                l_str = line.strip()
                if l_str and not l_str.startswith('Source:'):
                    desc_parts.append(l_str)
            desc = " ".join(desc_parts).strip()
            
            # Extract features by level
            features_by_level = {}
            feature_matches = list(re.finditer(r'^Level\s+(\d+):\s+(.+)$', text, re.MULTILINE))
            for i, match in enumerate(feature_matches):
                lvl = match.group(1)
                feat_name = clean_str(match.group(2))
                start_pos = match.end()
                end_pos = feature_matches[i+1].start() if i + 1 < len(feature_matches) else len(text)
                feat_text = clean_str(text[start_pos:end_pos])
                
                if lvl not in features_by_level:
                    features_by_level[lvl] = {}
                    
                # Check if this feature is a subclass spell feature
                if title in subclass_spells_map and any(kw in feat_name.lower() for kw in ['spells', 'knowledge domain spells', 'genie spells', 'winter walker spells', 'spellfire spells']):
                    features_by_level[lvl][feat_name] = subclass_spells_map[title]
                else:
                    features_by_level[lvl][feat_name] = feat_text

            subclasses.append({
                "name": title,
                "class": cls_name,
                "description": desc,
                "source": "Forgotten Realms: Heroes of Faerûn",
                "features_by_level": features_by_level
            })

    # 2. Backgrounds
    backgrounds = []
    for slug, item in raw_data.get('background', {}).items():
        title = clean_str(item['title'])
        text = clean_str(item['text'])
        
        # ASI
        asi_match = re.search(r'Ability Scores?:\s*([^\n]+)', text)
        asi_list = []
        if asi_match:
            raw_asi = asi_match.group(1)
            asi_list = [clean_str(a) for a in re.split(r',|\band\b', raw_asi) if clean_str(a)]
        
        # Feat
        feat_match = re.search(r'Feat:\s*([^\n]+)', text)
        feat_name = clean_str(feat_match.group(1)) if feat_match else "Alert"
        
        # Skills
        skills_match = re.search(r'Skill Proficiencies:\s*([^\n]+)', text)
        skill_list = []
        if skills_match:
            raw_skills = skills_match.group(1)
            skill_list = [clean_str(s) for s in re.split(r',|\band\b', raw_skills) if clean_str(s)]
        
        # Tools
        tools_match = re.search(r'Tool Proficiency:\s*([^\n]+)', text)
        tool_list = []
        if tools_match:
            raw_tools = clean_str(tools_match.group(1))
            if raw_tools.lower() != 'none':
                tool_list = [raw_tools]
                
        # Equipment
        equip_match = re.search(r'Equipment:\s*Choose A or B:\s*\(A\)\s*(.+?);\s*or\s*\(B\)\s*(.+)', text, re.DOTALL)
        if equip_match:
            opt_a_text = equip_match.group(1).strip()
            opt_b_text = equip_match.group(2).strip()
            gold_b_match = re.search(r'(\d+)\s*GP', opt_b_text)
            gold_b = int(gold_b_match.group(1)) if gold_b_match else 50
            
            gold_a_match = re.search(r'(\d+)\s*GP', opt_a_text)
            gold_a = int(gold_a_match.group(1)) if gold_a_match else 0
            items_a = [clean_str(i) for i in opt_a_text.split(',') if clean_str(i) and not re.match(r'^\d+\s*GP$', clean_str(i))]
            
            starting_equipment = {
                "option_a": {
                    "items": items_a,
                    "gold": gold_a
                },
                "option_b": {
                    "gold": gold_b
                }
            }
        else:
            starting_equipment = {
                "option_a": {"items": ["Traveler's Clothes"], "gold": 15},
                "option_b": {"gold": 50}
            }
            
        lines = [clean_str(l) for l in text.splitlines() if clean_str(l)]
        lore_lines = []
        for l in lines:
            if any(l.startswith(k) for k in ['Source:', 'Ability Score', 'Feat:', 'Skill Proficiencies:', 'Tool Proficiency:', 'Equipment:']):
                continue
            lore_lines.append(l)
        desc = " ".join(lore_lines).strip()
        
        effects = [
            {
                "type": "grant_skill_proficiency",
                "skills": skill_list
            },
            {
                "type": "grant_origin_feat",
                "feat": feat_name
            }
        ]
        if tool_list:
            effects.append({
                "type": "grant_tool_proficiency",
                "tools": tool_list
            })
            
        suggested = {}
        if len(asi_list) >= 2:
            suggested = {asi_list[0]: 2, asi_list[1]: 1}
            
        backgrounds.append({
            "name": title,
            "description": desc,
            "edition": "2024",
            "status": "active",
            "source": "Forgotten Realms: Heroes of Faerûn",
            "ability_score_increase": {
                "total": 3,
                "options": asi_list,
                "suggested": suggested
            },
            "effects": effects,
            "starting_equipment": starting_equipment
        })

    # 3. Feats
    origin_feats = {}
    general_feats = {}

    for slug, item in raw_data.get('feat', {}).items():
        title = clean_str(item['title'])
        text = clean_str(item['text'])
        
        is_epic = "Epic Boon Feat" in text
        is_origin = "Origin Feat" in text
        
        prereq_match = re.search(r'Prerequisite:\s*([^\n\)]+)', text)
        prereq = clean_str(prereq_match.group(1)) if prereq_match else None
        if is_epic and not prereq:
            prereq = "Level 19+"
            
        category = "Epic Boon" if is_epic else ("Origin" if is_origin else "General")
        
        benefits = []
        lines = [clean_str(l) for l in text.splitlines() if clean_str(l)]
        for l in lines:
            if l.startswith('Source:') or 'Feat (Prerequisite' in l or l in ['Origin Feat', 'General Feat', 'Epic Boon Feat']:
                continue
            benefits.append(l)
            
        feat_obj = {
            "description": f"{category} Feat" + (f" (Prerequisite: {prereq})" if prereq else ""),
            "benefits": benefits,
            "category": category,
            "source": "Forgotten Realms: Heroes of Faerûn"
        }
        if prereq:
            feat_obj["prerequisite"] = prereq
            
        if is_origin:
            origin_feats[title] = feat_obj
        else:
            general_feats[title] = feat_obj

    # 4. Spells & Spell Class Lists
    spells = []
    spell_class_lists = {
        "artificer": {"cantrips": [], "spells_by_level": {}},
        "bard": {"cantrips": [], "spells_by_level": {}},
        "cleric": {"cantrips": [], "spells_by_level": {}},
        "druid": {"cantrips": [], "spells_by_level": {}},
        "paladin": {"cantrips": [], "spells_by_level": {}},
        "ranger": {"cantrips": [], "spells_by_level": {}},
        "sorcerer": {"cantrips": [], "spells_by_level": {}},
        "warlock": {"cantrips": [], "spells_by_level": {}},
        "wizard": {"cantrips": [], "spells_by_level": {}},
    }

    for slug, item in raw_data.get('spell', {}).items():
        title = clean_str(item['title'])
        text = clean_str(item['text'])
        lines = [clean_str(l) for l in text.splitlines() if clean_str(l)]
        
        level = 0
        school = "Evocation"
        classes = []
        
        for l in lines:
            m = re.search(r'(Cantrip|Level\s+(\d+))\s+([A-Za-z]+)\s*\(([^)]+)\)', l)
            if m:
                if m.group(1) == 'Cantrip':
                    level = 0
                else:
                    level = int(m.group(2))
                school = m.group(3).capitalize()
                raw_classes = m.group(4)
                classes = [clean_str(c) for c in re.split(r',', raw_classes) if clean_str(c)]
                break
                
        cast_match = re.search(r'Casting Time:\s*([^\n]+)', text)
        casting_time = clean_str(cast_match.group(1)) if cast_match else "1 action"
        ritual = "ritual" in casting_time.lower()
        
        range_match = re.search(r'Range:\s*([^\n]+)', text)
        spell_range = clean_str(range_match.group(1)) if range_match else "Self"
        
        comp_match = re.search(r'Components:\s*([^\n]+)', text)
        components = []
        if comp_match:
            c_str = clean_str(comp_match.group(1))
            comp_parts = re.findall(r'[VSM](?:\s*\([^)]+\))?', c_str)
            components = [clean_str(cp) for cp in comp_parts]
            
        dur_match = re.search(r'Duration:\s*([^\n]+)', text)
        duration = clean_str(dur_match.group(1)) if dur_match else "Instantaneous"
        
        spells.append({
            "name": title,
            "level": level,
            "school": school,
            "casting_time": casting_time,
            "range": spell_range,
            "components": components,
            "duration": duration,
            "description": text.strip(),
            "classes": classes,
            "ritual": ritual,
            "source": "Forgotten Realms: Heroes of Faerûn"
        })
        
        for c in classes:
            c_low = c.lower()
            if c_low in spell_class_lists:
                if level == 0:
                    if title not in spell_class_lists[c_low]["cantrips"]:
                        spell_class_lists[c_low]["cantrips"].append(title)
                else:
                    lvl_str = str(level)
                    if lvl_str not in spell_class_lists[c_low]["spells_by_level"]:
                        spell_class_lists[c_low]["spells_by_level"][lvl_str] = []
                    if title not in spell_class_lists[c_low]["spells_by_level"][lvl_str]:
                        spell_class_lists[c_low]["spells_by_level"][lvl_str].append(title)

    # Clean empty lists in spell_class_lists
    for c_low in list(spell_class_lists.keys()):
        # Sort cantrips
        spell_class_lists[c_low]["cantrips"].sort()
        # Sort levels
        for lvl_str in spell_class_lists[c_low]["spells_by_level"]:
            spell_class_lists[c_low]["spells_by_level"][lvl_str].sort()

    manifest = {
        "id": "forgotten-realms-heroes-of-faerun",
        "title": "Forgotten Realms: Heroes of Faerûn",
        "publisher": "Wizards of the Coast",
        "version": "1.0.0",
        "compatibility": "2024",
        "description": "Character options from Forgotten Realms: Heroes of Faerûn, including 8 subclasses (College of the Moon, Knowledge Domain, Banneret, Oath of the Noble Genies, Winter Walker, Scion of the Three, Spellfire Sorcery, Bladesinger), 18 backgrounds, 34 feats, and 19 spells.",
        "dependencies": [
            "core-phb-2024"
        ]
    }

    supplement_package = {
        "manifest": manifest,
        "subclasses": subclasses,
        "backgrounds": backgrounds,
        "feats": {
            "origin_feats": origin_feats,
            "general_feats": general_feats
        },
        "spells": spells,
        "spell_class_lists": spell_class_lists
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(supplement_package, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated FRHoF supplement package at: {OUTPUT_PATH}")
    print(f"  - Subclasses:    {len(subclasses)}")
    print(f"  - Backgrounds:   {len(backgrounds)}")
    print(f"  - Origin Feats:  {len(origin_feats)}")
    print(f"  - General Feats: {len(general_feats)}")
    print(f"  - Spells:        {len(spells)}")

if __name__ == '__main__':
    build_frhof()
