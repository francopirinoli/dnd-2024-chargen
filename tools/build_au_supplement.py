"""
build_au_supplement.py
Assembles supplements/arcana-unleashed.json from the Arcana Unleashed dataset.
Conforms strictly to models/supplement_schema.json.
"""

import json
import os
import re
import sys
from pathlib import Path

# Configure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(r"C:\Users\Franco\.gemini\antigravity\brain\89cc94d4-3aba-4f65-8f53-6651c8f26c1c\scratch\au_data")
OUTPUT_PATH = REPO_ROOT / "supplements" / "arcana-unleashed.json"

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = text
    t = re.sub(r'\{@dice\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@b\s+([^}]+)\}', r'**\1**', t)
    t = re.sub(r'\{@i\s+([^}]+)\}', r'*\1*', t)
    t = re.sub(r'\{@spell\s+([^|}]+)[^}]*\}', r'*\1*', t)
    t = re.sub(r'\{@item\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@skill\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@condition\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@action\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@filter\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@creature\s+([^|}]+)[^}]*\}', r'\1', t)
    t = re.sub(r'\{@sense\s+([^|}]+)[^}]*\}', r'\1', t)
    def _clean_pipe_tag(match):
        parts = match.group(1).split('|')
        return parts[-1] if len(parts) >= 3 else parts[0]
    t = re.sub(r'\{@(?:variantrule|table|status|class|book|sense|quickref|itemProperty)\s+([^}]+)\}', _clean_pipe_tag, t)
    t = re.sub(r'\{@\w+\s+([^|}]+)[^}]*\}', r'\1', t)
    t = t.replace('\u2212', '-')
    return t.strip()

def entries_to_text(entries) -> str:
    lines = []
    if isinstance(entries, str):
        return clean_text(entries)
    if isinstance(entries, list):
        for e in entries:
            t = entries_to_text(e)
            if t:
                lines.append(t)
    elif isinstance(entries, dict):
        etype = entries.get("type")
        name = entries.get("name")
        if etype == "entries":
            sub = entries_to_text(entries.get("entries", []))
            if name:
                lines.append(f"**{name}**: {sub}")
            else:
                lines.append(sub)
        elif etype == "list":
            for item in entries.get("items", []):
                if isinstance(item, dict) and item.get("name"):
                    lines.append(f"- **{clean_text(item['name'])}**: {clean_text(entries_to_text(item.get('entry') or item.get('entries', '')))}")
                else:
                    lines.append(f"- {entries_to_text(item)}")
        elif etype == "table":
            caption = entries.get("caption", "")
            if caption:
                lines.append(f"**{caption}**:")
            col_labels = entries.get("colLabels", [])
            if col_labels:
                lines.append("| " + " | ".join(clean_text(str(c)) for c in col_labels) + " |")
                lines.append("| " + " | ".join("---" for _ in col_labels) + " |")
            for row in entries.get("rows", []):
                lines.append("| " + " | ".join(clean_text(str(c)) for c in row) + " |")
        elif "entries" in entries:
            lines.append(entries_to_text(entries["entries"]))
    return "\n\n".join(lines).strip()

def format_time(time_list):
    if not time_list:
        return "1 action"
    t = time_list[0]
    num = t.get("number", 1)
    unit = t.get("unit", "action")
    if unit == "bonus":
        return f"{num} bonus action"
    elif unit == "reaction":
        return f"{num} reaction"
    elif unit == "action":
        return f"{num} action" if num == 1 else f"{num} actions"
    elif unit == "minute":
        return f"{num} minute" if num == 1 else f"{num} minutes"
    elif unit == "hour":
        return f"{num} hour" if num == 1 else f"{num} hours"
    return f"{num} {unit}"

def format_range(range_obj):
    if not range_obj:
        return "Self"
    rtype = range_obj.get("type", "")
    dist = range_obj.get("distance", {})
    amt = dist.get("amount")
    unit = dist.get("type", "feet")
    if rtype == "point":
        if amt is None:
            return "Touch" if unit == "touch" else "Self"
        return f"{amt} feet" if unit == "feet" else f"{amt} {unit}"
    elif rtype == "emanation":
        return f"Self ({amt}-foot Emanation)"
    elif rtype == "line":
        return f"Self ({amt}-foot Line)"
    elif rtype == "cone":
        return f"Self ({amt}-foot Cone)"
    elif rtype == "radius":
        return f"{amt}-foot radius"
    elif rtype == "special":
        return "Special"
    return "Self"

def format_components(comp_obj):
    comps = []
    if comp_obj.get("v"):
        comps.append("V")
    if comp_obj.get("s"):
        comps.append("S")
    m = comp_obj.get("m")
    if m:
        if isinstance(m, str):
            comps.append(f"M ({m})")
        elif isinstance(m, dict):
            text = m.get("text", "")
            comps.append(f"M ({text})" if text else "M")
        else:
            comps.append("M")
    return comps if comps else ["V"]

def format_duration(dur_list):
    if not dur_list:
        return "Instantaneous"
    d = dur_list[0]
    dtype = d.get("type", "")
    conc = d.get("concentration", False)
    prefix = "Concentration, up to " if conc else ""
    if dtype == "instant":
        return "Instantaneous"
    elif dtype == "timed":
        dur = d.get("duration", {})
        amt = dur.get("amount", 1)
        u = dur.get("type", "round")
        if u == "round":
            s = f"{amt} round" if amt == 1 else f"{amt} rounds"
        elif u == "minute":
            s = f"{amt} minute" if amt == 1 else f"{amt} minutes"
        elif u == "hour":
            s = f"{amt} hour" if amt == 1 else f"{amt} hours"
        elif u == "day":
            s = f"{amt} day" if amt == 1 else f"{amt} days"
        else:
            s = f"{amt} {u}"
        return prefix + s
    elif dtype == "special":
        return "Special"
    return "Instantaneous"

SCHOOL_MAP = {
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "V": "Evocation",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
}

def build():
    # 1. Manifest
    manifest = {
        "id": "arcana-unleashed",
        "title": "Arcana Unleashed",
        "publisher": "Wizards of the Coast",
        "version": "1.0.0",
        "compatibility": "2024",
        "description": "Character options from Arcana Unleashed: 8 subclasses (Arcana Domain Cleric, Arcane Archer Fighter, Warrior of the Mystic Arts Monk, Vestige Patron Warlock, Conjurer Wizard, Enchanter Wizard, Necromancer Wizard, Transmuter Wizard), 10 backgrounds, 29 feats, and 33 spells.",
        "dependencies": [
            "core-phb-2024"
        ]
    }

    # 2. Subclasses
    subclasses = [
        # Cleric: Arcana Domain
        {
            "name": "Arcana Domain",
            "class": "Cleric",
            "source": "Arcana Unleashed",
            "description": "Magic suffuses the multiverse and fuels both destruction and creation. Clerics with the Arcana Domain view magical knowledge not as power to be used in pursuit of personal ends, but as a gift they have the responsibility to share. Gods associated with the Arcana Domain know the secrets and potential of magic intimately.",
            "features_by_level": {
                "3": {
                    "Arcana Domain Spells": {
                        "description": "When you reach a Cleric level specified in the Arcana Domain Spells table, you thereafter always have the listed spells prepared.",
                        "spells": {
                            "3": ["Detect Magic", "Magic Missile", "Magic Weapon", "Nystul's Magic Aura"],
                            "5": ["Counterspell", "Dispel Magic"],
                            "7": ["Arcane Eye", "Leomund's Secret Chest"],
                            "9": ["Bigby's Hand", "Teleportation Circle"]
                        },
                        "effects": [
                            {"type": "grant_spell", "spell": "Detect Magic", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Magic Missile", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Magic Weapon", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Nystul's Magic Aura", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Counterspell", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Dispel Magic", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Arcane Eye", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Leomund's Secret Chest", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Bigby's Hand", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Teleportation Circle", "min_level": 9, "counts_against_limit": False}
                        ]
                    },
                    "Student of Arcana": {
                        "description": "You gain proficiency in the Arcana skill or one skill of your choice from the skills available to Clerics at level 1. You also learn two Wizard cantrips of your choice. Whenever you gain a Cleric level, you can replace one of these cantrips with another Wizard cantrip.",
                        "effects": [
                            {"type": "grant_skill_proficiency", "from_choice": "subclass_Student of Arcana_skill"},
                            {"type": "grant_cantrip_choice", "spell_list": "wizard", "count": 2}
                        ],
                        "choices": [
                            {
                                "type": "select_single",
                                "name": "skill",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Arcana", "History", "Insight", "Medicine", "Persuasion", "Religion"]
                                },
                                "optional": False
                            }
                        ]
                    },
                    "Modify Magic": "You can use your Channel Divinity to alter your spells as you cast them. When you cast a spell, you can expend one use of your Channel Divinity and change the spell in one of the following ways (no action required):\n- Fortifying Spell: One target of the spell gains Temporary Hit Points equal to 2d8 plus your Cleric level.\n- Tenacious Spell: When you cast a spell that forces a creature to make a saving throw, and a creature you can see succeeds on that saving throw, roll 1d6 and subtract the number rolled from the target's first saving throw against the spell's effect."
                },
                "6": {
                    "Dispelling Recovery": "Immediately after you cast a spell with a spell slot that restores Hit Points to a creature or ends a condition on a creature, you can cast Dispel Magic as part of that action, Bonus Action, or Reaction, and without expending a spell slot. Once you use this feature, you can't use it again until you finish a Short or Long Rest. You also restore your use of it by expending a level 3+ spell slot."
                },
                "17": {
                    "Magical Mastery": "You learn four Wizard spells, one from each of levels 6, 7, 8, and 9. You thereafter always have those spells prepared. Whenever you gain a Cleric level, you can replace one of these spells with another Wizard spell of the same level."
                }
            }
        },

        # Fighter: Arcane Archer
        {
            "name": "Arcane Archer",
            "class": "Fighter",
            "source": "Arcana Unleashed",
            "description": "An Arcane Archer studies a unique elven method of archery that weaves magic into attacks to produce supernatural effects. Over the centuries, other folk have learned this technique and broadened it so it applies to ranged weapons of many kinds and to aspects of adventuring life outside of combat.",
            "features_by_level": {
                "3": {
                    "Arcane Archer Lore": {
                        "description": "You learn magical theory and secrets of nature, granting you the following benefits:\n- Cantrip: You know either the Druidcraft or the Prestidigitation cantrip. Intelligence is your spellcasting ability for it.\n- Skills: You gain proficiency in the Arcana and Nature skills (or another Fighter skill if already proficient).",
                        "effects": [
                            {"type": "grant_cantrip", "from_choice": "subclass_Arcane Archer Lore_cantrip"},
                            {"type": "grant_skill_proficiency", "from_choice": "subclass_Arcane Archer Lore_skill1"},
                            {"type": "grant_skill_proficiency", "from_choice": "subclass_Arcane Archer Lore_skill2"}
                        ],
                        "choices": [
                            {
                                "type": "select_single",
                                "name": "cantrip",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Druidcraft", "Prestidigitation"]
                                },
                                "optional": False
                            },
                            {
                                "type": "select_single",
                                "name": "skill1",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Arcana", "Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"]
                                },
                                "optional": False
                            },
                            {
                                "type": "select_single",
                                "name": "skill2",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Nature", "Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"]
                                },
                                "optional": False
                            }
                        ]
                    },
                    "Arcane Shot": {
                        "description": "You learn to unleash special magical effects with your shots. You learn two Arcane Shot options of your choice. You learn an additional Arcane Shot option when you reach Fighter levels 7, 10, 15, and 18. Each time you learn a new Arcane Shot option, you can replace one option you know with a different one.\n\nOnce per turn when you make a ranged attack using a weapon with the Ammunition property, you can apply one of your Arcane Shot options to that attack. You decide to use the option when you hit a creature and deal damage to it unless the option doesn't involve an attack roll.\n\nYou can use this feature a number of times equal to your Intelligence modifier (minimum of once). You regain all expended uses when you finish a Short or Long Rest.\n\nArcane Shot options refer to your Arcane Shot Die. Your Arcane Shot Die is a d6 (scaling to d8 at level 10, d10 at level 15, and d12 at level 18). If an option requires a saving throw, the DC equals 8 + your Intelligence modifier + your Proficiency Bonus.",
                        "effects": [
                            {
                                "type": "grant_arcane_shot_dice",
                                "die_by_level": {
                                    "3": "d6",
                                    "10": "d8",
                                    "15": "d10",
                                    "18": "d12"
                                }
                            }
                        ],
                        "choices": {
                            "type": "select_multiple",
                            "count": 2,
                            "name": "arcane_shots",
                            "source": {
                                "type": "external",
                                "file": "arcane_shots.json",
                                "list": "arcane_shots"
                            },
                            "optional": False,
                            "additional_choices_by_level": {
                                "7": {"count": 1, "replace_allowed": True},
                                "10": {"count": 1, "replace_allowed": True},
                                "15": {"count": 1, "replace_allowed": True},
                                "18": {"count": 1, "replace_allowed": True}
                            }
                        }
                    }
                },
                "7": {
                    "Curving Shot": "You learn how to direct an errant shot toward a new target. If you make a ranged attack roll with a weapon with the Ammunition property and miss, you can cause the shot to ricochet toward a new target as a Bonus Action immediately after the attack misses. The new target must be a creature you can see within the weapon's range and within 60 feet of the attack's original target. Make an attack roll against the new target.",
                    "Magical Ammunition": "You learn to imbue your ammunition with magical properties. As a Magic action, you can imbue a piece of nonmagical ammunition with one of the following magical properties and fire it at a solid surface you can see within the weapon's range. When the ammunition hits the surface, the effect activates until you remove it as a Magic action or the effect ends (destroying the ammunition). Once you use this feature, you can't do so again until you finish a Short or Long Rest, or restore your use by expending a use of Second Wind:\n- Darkening Ammunition: Magical shadows fill a 15-foot Emanation originating from the ammunition for 1 minute. Nonmagical flames are extinguished, and creatures in the Emanation have a -5 penalty to Wisdom (Perception) checks and Passive Perception.\n- Unlocking Ammunition: A burst of magic fills a 15-foot Emanation with a knocking sound audible up to 300 feet away. Any object held shut by a nonmagical lock or that is stuck/barred becomes unlocked, unstuck, or unbarred.\n- Vine Ammunition: A 120-foot-long climbable vine grows from the ammunition, lasting 10 minutes."
                },
                "10": {
                    "Ever-Ready Shot": "When you roll Initiative, you can regain one expended use of Arcane Shot."
                },
                "15": {
                    "Indomitable Teleport": "Your magical mastery lets you escape dire situations. When you use your Indomitable feature and succeed on the saving throw, you can teleport up to 60 feet to an unoccupied space you can see."
                },
                "18": {
                    "Masterful Shots": "You employ agility in your sharpshooting. When a creature you can see misses you with an attack roll, you can take a Reaction to move up to half your Speed away from the attacker without provoking Opportunity Attacks. You can then make a ranged attack roll against the attacker as part of this Reaction if within range."
                }
            }
        },

        # Monk: Warrior of the Mystic Arts
        {
            "name": "Warrior of the Mystic Arts",
            "class": "Monk",
            "source": "Arcana Unleashed",
            "description": "Warriors of the Mystic Arts wield magic to supplement their martial skill. They harness mystical focus to enhance their magical and physical abilities.",
            "spellcasting_ability": "Wisdom",
            "spell_list": "Sorcerer",
            "cantrips_by_level": {
                "3": 2, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2, "9": 2,
                "10": 3, "11": 3, "12": 3, "13": 3, "14": 3, "15": 3, "16": 3, "17": 3, "18": 3, "19": 3, "20": 3
            },
            "prepared_spells_by_level": {
                "3": 3, "4": 4, "5": 4, "6": 4, "7": 5, "8": 6, "9": 6,
                "10": 7, "11": 8, "12": 8, "13": 9, "14": 10, "15": 10, "16": 11, "17": 11, "18": 11, "19": 12, "20": 13
            },
            "spell_slots_by_level": {
                "3": [2, 0, 0, 0, 0, 0, 0, 0, 0],
                "4": [3, 0, 0, 0, 0, 0, 0, 0, 0],
                "5": [3, 0, 0, 0, 0, 0, 0, 0, 0],
                "6": [3, 0, 0, 0, 0, 0, 0, 0, 0],
                "7": [4, 2, 0, 0, 0, 0, 0, 0, 0],
                "8": [4, 2, 0, 0, 0, 0, 0, 0, 0],
                "9": [4, 2, 0, 0, 0, 0, 0, 0, 0],
                "10": [4, 3, 0, 0, 0, 0, 0, 0, 0],
                "11": [4, 3, 0, 0, 0, 0, 0, 0, 0],
                "12": [4, 3, 0, 0, 0, 0, 0, 0, 0],
                "13": [4, 3, 2, 0, 0, 0, 0, 0, 0],
                "14": [4, 3, 2, 0, 0, 0, 0, 0, 0],
                "15": [4, 3, 2, 0, 0, 0, 0, 0, 0],
                "16": [4, 3, 3, 0, 0, 0, 0, 0, 0],
                "17": [4, 3, 3, 0, 0, 0, 0, 0, 0],
                "18": [4, 3, 3, 0, 0, 0, 0, 0, 0],
                "19": [4, 3, 3, 1, 0, 0, 0, 0, 0],
                "20": [4, 3, 3, 1, 0, 0, 0, 0, 0]
            },
            "features_by_level": {
                "3": {
                    "Spellcasting": {
                        "description": "You have learned to cast Sorcerer spells. You know two Sorcerer cantrips of your choice (Wisdom is your spellcasting ability). You prepare and cast level 1+ Sorcerer spells using spell slots and Wisdom as your spellcasting ability.",
                        "feature_kind": "spellcasting_setup",
                        "effects": [
                            {"type": "grant_cantrip_choice", "spell_list": "sorcerer", "count": 2}
                        ]
                    }
                },
                "6": {
                    "Mystic Fighting Style": "When you take the Attack action on your turn, you can replace one Unarmed Strike with a casting of one of your Sorcerer cantrips that has a casting time of an action.",
                    "Mystic Focus": "You keep your magical power and martial focus in perfect balance:\n- Converting Spell Slots to Focus Points: You can expend a spell slot to regain a number of expended Focus Points equal to the slot's level (no action required).\n- Recovering Spell Slots: As a Bonus Action, you can expend Focus Points to regain an expended spell slot: 2 Focus Points for a level 1 slot, or 3 Focus Points for a level 2 slot."
                },
                "11": {
                    "Focused Strike": "When you use your Stunning Strike, whether the target succeeds or fails on the saving throw, the target has Disadvantage on saving throws against your spells until the start of your next turn."
                },
                "17": {
                    "Improved Mystic Fighting Style": "When you use Flurry of Blows, you can replace two of the Unarmed Strikes with a casting of one of your level 1 or 2 Sorcerer spells that has a casting time of an action, and you cast it as part of the same Bonus Action you use to activate Flurry of Blows."
                }
            }
        },

        # Warlock: Vestige Patron
        {
            "name": "Vestige Patron",
            "class": "Warlock",
            "source": "Arcana Unleashed",
            "description": "Your pact draws on the power of a dying god, a being once worshipped by countless followers but now abandoned and forgotten. Driven to regain its former power, the vestige shares its remaining strength with you.",
            "features_by_level": {
                "3": {
                    "Vestige Companion": "The vestige manifests as a loyal companion with the Vestige Companion stat block. It is a Celestial, Fiend, or Undead (choose when you gain this feature). It is friendly to you and your allies and obeys your commands. In combat, it shares your Initiative count and acts immediately after your turn.",
                    "Vestige Spells": {
                        "description": "The magic of your Vestige Companion ensures you always have certain spells ready. Select one of the following Cleric domains: Life, Light, Trickery, or War. The Domain Spells of your chosen domain are Warlock spells for you and are always prepared.",
                        "choices": [
                            {
                                "type": "select_single",
                                "name": "domain",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Life Domain", "Light Domain", "Trickery Domain", "War Domain"]
                                },
                                "optional": False
                            }
                        ],
                        "choice_effects": {
                            "domain": {
                                "Life Domain": [
                                    {"type": "grant_spell", "spell": "Aid", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Bless", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Cure Wounds", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Lesser Restoration", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Mass Healing Word", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Revivify", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Aura of Life", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Death Ward", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Greater Restoration", "min_level": 9, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Mass Cure Wounds", "min_level": 9, "counts_against_limit": False}
                                ],
                                "Light Domain": [
                                    {"type": "grant_spell", "spell": "Burning Hands", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Faerie Fire", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Scorching Ray", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "See Invisibility", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Daylight", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Fireball", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Arcane Eye", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Wall of Fire", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Flame Strike", "min_level": 9, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Scrying", "min_level": 9, "counts_against_limit": False}
                                ],
                                "Trickery Domain": [
                                    {"type": "grant_spell", "spell": "Charm Person", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Disguise Self", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Invisibility", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Pass without Trace", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Hypnotic Pattern", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Nondetection", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Confusion", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Dimension Door", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Dominate Person", "min_level": 9, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Modify Memory", "min_level": 9, "counts_against_limit": False}
                                ],
                                "War Domain": [
                                    {"type": "grant_spell", "spell": "Guiding Bolt", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Magic Weapon", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Shield of Faith", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Spiritual Weapon", "min_level": 3, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Crusader's Mantle", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Spirit Guardians", "min_level": 5, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Fire Shield", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Freedom of Movement", "min_level": 7, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Hold Monster", "min_level": 9, "counts_against_limit": False},
                                    {"type": "grant_spell", "spell": "Steel Wind Strike", "min_level": 9, "counts_against_limit": False}
                                ]
                            }
                        }
                    }
                },
                "6": {
                    "Vestige Power": "Your Vestige Companion now regains its use of Divine Power whenever you finish a Short or Long Rest or when you use your Magical Cunning feature. In addition, while within 30 feet of your Vestige Companion, you have Resistance to the same damage types as the vestige."
                },
                "10": {
                    "Vestige Recovery": "When your Vestige Companion would drop to 0 Hit Points, you can take a Reaction and expend a Pact Magic spell slot to instead change its Hit Points to its Hit Point maximum. The vestige then teleports to an unoccupied space you can see within 30 feet of it (once per Long Rest)."
                },
                "14": {
                    "Semblance of Life": "As a Magic action while the vestige is within 90 feet of you, you can shape-shift it for 1 hour into a powerful spirit based on its creature type: Celestial Spirit (if Celestial), Fiendish Spirit (if Fiend), or Undead Spirit (if Undead), using your Warlock spell slot level for its statistics."
                }
            }
        },

        # Wizard: Conjurer
        {
            "name": "Conjurer",
            "class": "Wizard",
            "source": "Arcana Unleashed",
            "description": "Conjurers specialize in the magical summoning of creatures and inanimate objects, as well as manipulating space itself through rapid teleportation.",
            "features_by_level": {
                "3": {
                    "Conjuration Savant": "Choose two Wizard spells from the Conjuration school, each of which must be no higher than level 2, and add them to your spellbook for free. In addition, whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell from the Conjuration school to your spellbook for free.",
                    "Benign Transposition": "As a Bonus Action, you can teleport up to 30 feet to an unoccupied space you can see. Alternatively, you can choose a willing Small or Medium creature within 30 feet of you that you can see; both you and that creature teleport, swapping spaces. You can use this feature a number of times equal to your Intelligence modifier (minimum of once), regaining all expended uses on a Long Rest. Whenever you cast a level 1+ Conjuration spell using a spell slot, you regain one expended use."
                },
                "6": {
                    "Distant Transposition": "The range of your Benign Transposition increases to 60 feet. In addition, you can target Large willing creatures with it.",
                    "Durable Summons": "Any creature that you summon or create with a Conjuration spell gains Temporary Hit Points equal to twice your Wizard level."
                },
                "10": {
                    "Focused Conjuration": "While you are maintaining Concentration on a Conjuration spell, your Concentration can't be broken as a result of taking damage."
                },
                "14": {
                    "Splintered Summons": "When you cast a Conjuration spell that summons or creates one creature, you can summon or create two of that creature instead. Each creature has half the Hit Points of the normal creature."
                }
            }
        },

        # Wizard: Enchanter
        {
            "name": "Enchanter",
            "class": "Wizard",
            "source": "Arcana Unleashed",
            "description": "Enchanters cloud minds and captivate wills, transforming hostile foes into allies and bending perceptions to their design.",
            "features_by_level": {
                "3": {
                    "Enchantment Savant": "Choose two Wizard spells from the Enchantment school, each of which must be no higher than level 2, and add them to your spellbook for free. In addition, whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell from the Enchantment school to your spellbook for free.",
                    "Enchanting Conversationalist": {
                        "description": "You gain proficiency in two of the following skills of your choice: Deception, Insight, Intimidation, or Persuasion.",
                        "choices": [
                            {
                                "type": "select_multiple",
                                "count": 2,
                                "name": "skills",
                                "description": "Choose two skill proficiencies.",
                                "source": {
                                    "type": "fixed_list",
                                    "options": ["Deception", "Insight", "Intimidation", "Persuasion"]
                                },
                                "optional": False
                            }
                        ],
                        "effects": [
                            {
                                "type": "grant_skill_proficiency",
                                "from_choice": "subclass_Enchanting Conversationalist_skills"
                            }
                        ]
                    },
                    "Hypnotic Presence": "As a Magic action, choose one creature you can see within 30 feet. If the target can see or hear you, it must succeed on a Wisdom saving throw against your spell save DC or have the Charmed condition until the end of your next turn (its Speed is 0 while Charmed). You can use this feature a number of times equal to your Intelligence modifier (minimum of once), regaining all expended uses on a Long Rest."
                },
                "6": {
                    "Split Enchantment": "When you use a spell slot to cast an Enchantment spell, such as Charm Person or Hold Person, that can be cast with a higher-level spell slot to target an additional creature, you can increase the spell's effective level by 1 for free. You can use this feature a number of times equal to your Intelligence modifier (minimum of once), regaining all expended uses on a Long Rest."
                },
                "10": {
                    "Instinctive Charm": "When a creature within 30 feet of you that you can see hits you with an attack roll, you can take a Reaction to force the attacker to make a Wisdom saving throw against your spell save DC. On a failed save, the attack misses instead, and if there is another creature within range of the attack other than the attacker, the attacker targets that creature with the triggering attack."
                },
                "14": {
                    "Alter Memories": "When you cast an Enchantment spell that imposes the Charmed condition using a spell slot, you can choose one creature targeted by the spell. That creature remains unaware of being Charmed by you. In addition, once before the spell ends, you can take a Magic action to alter its memory of the time spent Charmed."
                }
            }
        },

        # Wizard: Necromancer
        {
            "name": "Necromancer",
            "class": "Wizard",
            "source": "Arcana Unleashed",
            "description": "Necromancers command the powers of life, death, and undeath, manipulating animating energies and drawing power from forbidden secrets inscribed in their spellbooks.",
            "features_by_level": {
                "3": {
                    "Necromancy Savant": "Choose two Wizard spells from the Necromancy school, each of which must be no higher than level 2, and add them to your spellbook for free. In addition, whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell from the Necromancy school to your spellbook for free.",
                    "Necromancy Spellbook": {
                        "description": "Your spellbook's necromantic secrets grant you Resistance to Necrotic damage, and the Find Familiar spell appears in your spellbook if it isn't there already (your familiar can take the form of an Undead skeleton or zombie animal).",
                        "effects": [
                            {"type": "grant_damage_resistance", "damage_type": "Necrotic"},
                            {"type": "grant_spell", "spell": "Find Familiar", "min_level": 3, "counts_against_limit": False}
                        ]
                    }
                },
                "6": {
                    "Grave Power": "While holding your spellbook: your Exhaustion level decreases by 1 whenever you use Arcane Recovery, and your Necromancy spells ignore Resistance to Necrotic damage.",
                    "Undead Thralls": {
                        "description": "You always have Animate Dead prepared and can cast it once per Long Rest without expending a spell slot, increasing its effective level by 1. Undead created or summoned by your spells add your Wizard level to their Hit Point maximum and add your Intelligence modifier to their damage rolls.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Animate Dead", "min_level": 6, "counts_against_limit": False}
                        ]
                    }
                },
                "10": {
                    "Harvest Undead": "Immediately after you become Bloodied but aren't reduced to 0 Hit Points, you can take a Reaction to reduce an Undead creature under your control that you can see to 0 Hit Points. You then immediately regain Hit Points equal to twice the destroyed creature's CR (minimum of 10 Hit Points)."
                },
                "14": {
                    "Death's Master": "While holding your spellbook: As a Bonus Action, choose any number of Undead you created or summoned with a Necromancy spell within 60 feet; they gain Advantage on attack rolls and saving throws until the start of your next turn. In addition, you can take a Magic action to bring an Undead within 60 feet under your permanent control if it fails a Charisma saving throw (once per Long Rest)."
                }
            }
        },

        # Wizard: Transmuter
        {
            "name": "Transmuter",
            "class": "Wizard",
            "source": "Arcana Unleashed",
            "description": "Transmuters study spells that modify energy and matter. To you, the world is eminently mutable, and you become a smith at reality's forge.",
            "features_by_level": {
                "3": {
                    "Transmutation Savant": "Choose two Wizard spells from the Transmutation school, each of which must be no higher than level 2, and add them to your spellbook for free. In addition, whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell from the Transmutation school to your spellbook for free.",
                    "Transmuter's Stone": "When you finish a Long Rest, you can create a Transmuter's Stone that lasts until you use this feature again. A creature with the stone in its possession gains proficiency in Constitution saving throws and one of the following benefits: Darkvision 60 ft, Speed +10 ft, or Resistance to Acid, Cold, Fire, Lightning, or Thunder damage.",
                    "Wondrous Alteration": {
                        "description": "You always have the Alter Self spell prepared and can cast it once per Long Rest without expending a spell slot. While under the effects of Alter Self, you gain enhanced benefits for each of its options.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Alter Self", "min_level": 3, "counts_against_limit": False}
                        ]
                    }
                },
                "6": {
                    "Empowered Transmutation": "When you use a spell slot to cast a Transmutation spell that doesn't make an attack roll or force a saving throw (such as Fly or Magic Weapon), you can increase the spell's effective level by 1 for free. You can use this feature a number of times equal to your Intelligence modifier (minimum once), regaining all expended uses on a Long Rest."
                },
                "10": {
                    "Potent Stone": "When you create your Transmuter's Stone, you can choose up to two benefits. In addition, you can change either or both benefits whenever you cast a Transmutation spell using a spell slot.",
                    "Shape-Shifter": {
                        "description": "You always have the Polymorph spell prepared and can cast it once per Long Rest without expending a spell slot.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Polymorph", "min_level": 10, "counts_against_limit": False}
                        ]
                    }
                },
                "14": {
                    "Master Transmuter": "While you carry your Transmuter's Stone, you can take a Magic action to consume the reserve of magic stored inside to achieve one of the following effects: Major Transformation (transmute an object into another object), Panacea (remove all curses, diseases, and restore all Hit Points), Restore Life (cast Raise Dead without a spell slot or components), or Restore Youth (reduce apparent age by 3d10 years)."
                }
            }
        }
    ]

    # 3. Backgrounds (10)
    bg_definitions = [
        {
            "name": "Agent of the Ninth Quill",
            "description": "You were trained by the Ninth Quill, a secretive arcane espionage syndicate that operates from the shadows to protect regional stability and procure magical secrets.",
            "abilities": ["Dexterity", "Intelligence", "Charisma"],
            "feat": "Arcane Infiltrator",
            "skills": ["Arcana", "Sleight of Hand"],
            "tools": ["Thieves' Tools"],
            "equipment_a": ["Dagger", "Light Hammer", "Thieves' Tools", "Iron Spikes", "Rope", "Traveler's Clothes"],
            "gold_a": 17,
            "gold_b": 50
        },
        {
            "name": "Bejeweled Conclave Spy",
            "description": "You served the Bejeweled Conclave, an elite network of gem-mages and diplomats who trade in high-stakes secrets and glittering illusions.",
            "abilities": ["Dexterity", "Wisdom", "Charisma"],
            "feat": "Arcane Eloquence",
            "skills": ["Deception", "Perception"],
            "tools": ["Disguise Kit"],
            "equipment_a": ["Disguise Kit", "Fine Clothes", "Perfume"],
            "gold_a": 5,
            "gold_b": 50
        },
        {
            "name": "Cosmic Dawn Experiment",
            "description": "You were altered by the Bringers of Cosmic Dawn, an esoteric cabal that pushed the boundaries of transmutation to evolve mortal forms.",
            "abilities": ["Strength", "Dexterity", "Constitution"],
            "feat": "Transmuted Anatomy",
            "skills": ["Athletics", "Survival"],
            "tools": ["Alchemist's Supplies"],
            "equipment_a": ["Alchemist's Supplies", "Backpack", "Robe", "Traveler's Clothes"],
            "gold_a": 30,
            "gold_b": 50
        },
        {
            "name": "Covenant of the Grave Recruit",
            "description": "Inducted into the Covenant of the Grave, you learned morbid anatomy and funeral rites, walking the threshold between mortality and necromancy.",
            "abilities": ["Strength", "Intelligence", "Wisdom"],
            "feat": "Arcane Undertaker",
            "skills": ["History", "Medicine"],
            "tools": ["Herbalism Kit"],
            "equipment_a": ["Dagger", "Herbalism Kit", "Book (anatomy)", "Shovel"],
            "gold_a": 16,
            "gold_b": 50
        },
        {
            "name": "Crucible Storm Chaser",
            "description": "You chased living storms and geothermal arcane vents for the Crucible Keepers, mastering rapid reactions and raw magical energy.",
            "abilities": ["Strength", "Constitution", "Intelligence"],
            "feat": "Arcane Overload",
            "skills": ["Athletics", "Nature"],
            "tools": ["Glassblower's Tools"],
            "equipment_a": ["Glassblower's Tools", "Backpack", "Rope", "Traveler's Clothes"],
            "gold_a": 15,
            "gold_b": 50
        },
        {
            "name": "Familiar Trainer",
            "description": "You grew up bonding with magical creatures and familiars, understanding their subtle signs and training them to act as loyal scouts and guardians.",
            "abilities": ["Constitution", "Intelligence", "Wisdom"],
            "feat": "Familiar Friend",
            "skills": ["Animal Handling", "Arcana"],
            "tools": ["Dice Set"],
            "equipment_a": ["Quarterstaff", "Dice Set", "Bedroll", "Bell", "String", "Tinderbox", "Traveler's Clothes", "Waterskin"],
            "gold_a": 44,
            "gold_b": 50
        },
        {
            "name": "Horizon Weaver Initiate",
            "description": "You studied under the Horizon Weavers, planar pathfinders who chart invisible dimensional rifts and mend tears across the planes.",
            "abilities": ["Dexterity", "Constitution", "Wisdom"],
            "feat": "Portal Jumper",
            "skills": ["Acrobatics", "Survival"],
            "tools": ["Weaver's Tools"],
            "equipment_a": ["Shortbow", "Arrows (20)", "Weaver's Tools", "Map", "Quiver", "Rope", "Traveler's Clothes"],
            "gold_a": 18,
            "gold_b": 50
        },
        {
            "name": "Phantasmic Circus Trouper",
            "description": "You performed under the grand pavilions of the Phantasmic Circus, mesmerizing crowds with magical artistry, acrobatic flair, and phantasmagoria.",
            "abilities": ["Dexterity", "Constitution", "Charisma"],
            "feat": "Arcane Artist",
            "skills": ["Deception", "Performance"],
            "tools": ["Disguise Kit"],
            "equipment_a": ["Disguise Kit", "Playing Card Set", "Costume", "Mirror", "Traveler's Clothes"],
            "gold_a": 12,
            "gold_b": 50
        },
        {
            "name": "Seer Apprentice",
            "description": "You apprenticed under the Seers of Sea and Sky, reading portents in tide and cloud, predicting fortunes, and preparing for destiny.",
            "abilities": ["Intelligence", "Wisdom", "Charisma"],
            "feat": "Arcane Omens",
            "skills": ["History", "Insight"],
            "tools": ["Navigator's Tools"],
            "equipment_a": ["Navigator's Tools", "Candle (8)", "Ink", "Ink Pen", "Parchment (9 sheets)", "Pouch", "Tinderbox", "Traveler's Clothes"],
            "gold_a": 11,
            "gold_b": 50
        },
        {
            "name": "Ward of the Sheltering Hands",
            "description": "Raised in the healing hospices and soup kitchens of the Sheltering Hands, you learned to care for the needy and shield the vulnerable with protective wards.",
            "abilities": ["Constitution", "Wisdom", "Charisma"],
            "feat": "Arcane Safeguard",
            "skills": ["Insight", "Medicine"],
            "tools": ["Cook's Utensils"],
            "equipment_a": ["Cook's Utensils", "Blanket", "Healer's Kit", "Lamp", "Oil (3 flasks)", "Tinderbox", "Traveler's Clothes", "Waterskin"],
            "gold_a": 40,
            "gold_b": 50
        }
    ]

    backgrounds = []
    for bg in bg_definitions:
        backgrounds.append({
            "name": bg["name"],
            "description": bg["description"],
            "edition": "2024",
            "status": "active",
            "source": "Arcana Unleashed",
            "ability_score_increase": {
                "total": 3,
                "options": bg["abilities"],
                "suggested": {bg["abilities"][0]: 2, bg["abilities"][1]: 1}
            },
            "effects": [
                {
                    "type": "grant_skill_proficiency",
                    "skills": bg["skills"]
                },
                {
                    "type": "grant_origin_feat",
                    "feat": bg["feat"]
                },
                {
                    "type": "grant_tool_proficiency",
                    "tools": bg["tools"]
                }
            ],
            "starting_equipment": {
                "option_a": {
                    "items": bg["equipment_a"],
                    "gold": bg["gold_a"]
                },
                "option_b": {
                    "gold": bg["gold_b"]
                }
            }
        })

    # 4. Feats (29)
    ALL_ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
    INT_WIS_CHA = ["Intelligence", "Wisdom", "Charisma"]

    SCHOOL_ADEPTS = {
        "Abjuration Adept": {
            "spells": ["Shield", "Lesser Restoration", "Protection from Energy", "Banishment", "Mass Cure Wounds"],
            "feature_name": "Protective Ward",
            "feature_desc": "When you cast a spell from the Abjuration school using a spell slot, you or one creature you can see within 30 feet of yourself gains Temporary Hit Points equal to twice the level of spell slot expended."
        },
        "Conjuration Adept": {
            "spells": ["Entangle", "Misty Step", "Conjure Animals", "Dimension Door", "Conjure Elemental"],
            "feature_name": "Persistent Conjuration",
            "feature_desc": "While maintaining Concentration on a spell from the Conjuration school, you gain a bonus to Constitution saving throws to maintain this Concentration. This bonus is equal to the ability modifier of the score increased by this feat."
        },
        "Divination Adept": {
            "spells": ["Detect Evil and Good", "Mind Spike", "Clairvoyance", "Divination", "Scrying"],
            "feature_name": "Prescient Intervention",
            "feature_desc": "When a creature you can see within 60 feet of yourself makes a D20 Test, you can take a Reaction to give that creature Advantage or Disadvantage (your choice) on that roll. Once you use this benefit, you can't do so again until you finish a Long Rest. You can also regain use of this feature when you cast a spell from the Divination school using a spell slot."
        },
        "Enchantment Adept": {
            "spells": ["Dissonant Whispers", "Enthrall", "Hold Person", "Dominate Beast", "Modify Memory"],
            "feature_name": "Subtle Enchantments",
            "feature_desc": "When you cast a spell from the Enchantment school using a spell slot, you can cast it without any Verbal, Somatic, or Material components, except Material components that are consumed by the spell or that have a cost specified in the spell."
        },
        "Evocation Adept": {
            "spells": ["Chromatic Orb", "Shatter", "Fireball", "Vitriolic Sphere", "Wall of Force"],
            "feature_name": "Fueled Evocation",
            "feature_desc": "Once per turn when you cast an Evocation spell and deal damage, you can roll up to two of your unexpended Hit Point Dice and add the total rolled to one of the spell's damage rolls. Those Hit Point Dice are then expended."
        },
        "Illusion Adept": {
            "spells": ["Silent Image", "Phantasmal Force", "Major Image", "Hallucinatory Terrain", "Seeming"],
            "feature_name": "Masterful Illusions",
            "feature_desc": "When you cast a spell from the Illusion school using a spell slot, you can cast it without any Verbal, Somatic, or Material components, except Material components that are consumed by the spell or that have a cost specified in the spell. Additionally, creatures have Disadvantage on Intelligence (Investigation) checks made to discern the true nature of illusions created by your spells."
        },
        "Necromancy Adept": {
            "spells": ["Inflict Wounds", "Ray of Enfeeblement", "Vampiric Touch", "Blight", "Raise Dead"],
            "feature_name": "Life Manipulation",
            "feature_desc": "When you cast a spell from the Necromancy school using a spell slot, you can immediately roll up to two of your unexpended Hit Point Dice. You regain Hit Points equal to the total rolled plus the level of the spell slot expended."
        },
        "Transmutation Adept": {
            "spells": ["Jump", "Spider Climb", "Slow", "Polymorph", "Animate Objects"],
            "feature_name": "Magical Augmentation",
            "feature_desc": "On your turn when you cast a spell from the Transmutation school using a spell slot, your Speed increases by 10 feet until the end of that turn, and you can make one weapon attack or Unarmed Strike as a Bonus Action."
        }
    }

    general_feats = {}
    origin_feats = {}

    # Build 8 School Adepts
    for feat_name, adept_info in SCHOOL_ADEPTS.items():
        spells = adept_info["spells"]
        spell_levels = [1, 3, 5, 7, 9]
        general_feats[feat_name] = {
            "description": "You gain the following benefits.",
            "benefits": [
                "Ability Score Increase: Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
                f"Additional Spells: Your prowess allows you to always have certain spells at the ready. When you have spell slots of a level specified in the {feat_name} Spells table, you thereafter always have the spells listed for that level and lower prepared.",
                f"Level 1: {spells[0]}",
                f"Level 2: {spells[1]}",
                f"Level 3: {spells[2]}",
                f"Level 4: {spells[3]}",
                f"Level 5: {spells[4]}",
                f"{adept_info['feature_name']}: {adept_info['feature_desc']}"
            ],
            "category": "General",
            "prerequisite": "Level 4+, Spellcasting or Pact Magic Feature",
            "source": "Arcana Unleashed",
            "choices": [
                {
                    "type": "select_single",
                    "description": "Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
                    "name": "ability",
                    "source": {
                        "type": "fixed_list",
                        "options": INT_WIS_CHA
                    }
                }
            ],
            "choice_effects": {
                "ability": {
                    ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                    for ab in INT_WIS_CHA
                }
            },
            "effects": [
                {"type": "grant_spell", "spell": sp, "min_level": lvl, "counts_against_limit": False}
                for lvl, sp in zip(spell_levels, spells)
            ]
        }

    # Build Familiar Feats (4)
    general_feats["Elemental Familiar"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase one ability score of your choice by 1, to a maximum of 20.",
            "Elemental Energy: You learn how to imbue your familiar with elemental power. When you cast the Find Familiar spell, choose Acid, Cold, Fire, Lightning, or Thunder damage. Your familiar is imbued with this energy until you cast Find Familiar again, granting it the following benefits:\n• Elemental Resistance: Your familiar has Resistance to the chosen damage type.\n• Energy Pulse: As a Bonus Action, you command your familiar to unleash a burst of elemental energy. Your familiar must be within 120 feet of you and take a Reaction to unleash this burst. Each creature in a 5-foot Emanation originating from your familiar makes a Dexterity saving throw (DC 8 plus your spellcasting ability modifier for the Find Familiar spell and your Proficiency Bonus). On a failed save, a creature takes 2d4 damage of the chosen type, and if the creature is Medium or smaller, it has the Prone condition."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Familiar Friend Feat",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase one ability score of your choice by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ALL_ABILITIES
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in ALL_ABILITIES
            }
        }
    }

    general_feats["Otherworldly Familiar"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase one ability score of your choice by 1, to a maximum of 20.",
            "Otherworldly Power: When you cast the Find Familiar spell, you can imbue your familiar with otherworldly power. When you do, your familiar has Resistance to one damage type of your choice: Necrotic, Poison, Psychic, Radiant, or Thunder.",
            "Energy Resistance: Choose Necrotic, Poison, Psychic, Radiant, or Thunder damage. Your familiar has Resistance to that damage type.",
            "Phase Walk: Your familiar can move through other creatures and objects as if they were Difficult Terrain. It takes 1d10 Force damage if it ends its turn inside an object."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Familiar Friend Feat",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase one ability score of your choice by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ALL_ABILITIES
                }
            },
            {
                "type": "select_single",
                "description": "Choose one damage resistance for your familiar.",
                "name": "energy_resistance",
                "source": {
                    "type": "fixed_list",
                    "options": ["Necrotic", "Poison", "Psychic", "Radiant", "Thunder"]
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in ALL_ABILITIES
            }
        }
    }

    general_feats["Soothing Familiar"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase one ability score of your choice by 1, to a maximum of 20.",
            "Healing Beacon: Positive energy fills a 5-foot Emanation originating from your familiar. Whenever you or an ally inside the Emanation regains Hit Points, the creature regains additional Hit Points equal to your Proficiency Bonus.",
            "Comforting Touch: As a Magic action, your familiar can touch a creature and end either the Frightened or Poisoned condition on it."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Familiar Friend Feat",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase one ability score of your choice by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ALL_ABILITIES
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in ALL_ABILITIES
            }
        }
    }

    general_feats["Warlike Familiar"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase one ability score of your choice by 1, to a maximum of 20.",
            "Battle Familiar: You always have the Battle Familiar spell prepared. You can cast it once without expending a spell slot, and you regain the ability to cast it in that way when you finish a Long Rest.",
            "Intercept Attack: When a creature within 5 feet of your familiar is hit by an attack roll, your familiar can use its Reaction to interpose itself, causing the attack to target the familiar instead."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Familiar Friend Feat",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase one ability score of your choice by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ALL_ABILITIES
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in ALL_ABILITIES
            }
        },
        "effects": [
            {"type": "grant_spell", "spell": "Battle Familiar", "min_level": 4, "counts_against_limit": False}
        ]
    }

    # Build Other General Feats (3)
    general_feats["Magic Connoisseur"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
            "Additional Spells: Choose a level 1 and a level 2 spell from the same spell list you selected for the Magic Initiate feat. You always have those spells prepared.",
            "Spell Change: Whenever you gain a level, you can replace one of the spells you chose for this feat with another spell of the same level from the chosen list."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Magic Initiate Feat",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": INT_WIS_CHA
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in INT_WIS_CHA
            }
        }
    }

    general_feats["Spell Resistant"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase your Dexterity or Constitution score by 1, to a maximum of 20.",
            "Magical Resilience: You have Resistance to one of the following damage types (choose when you gain this feat): Necrotic, Psychic, Radiant, or Thunder.",
            "Magic Resistant: When you would fail a saving throw against a spell or magical effect, you can roll 1d4 and add it to the total, potentially turning a failure into a success."
        ],
        "category": "General",
        "prerequisite": "Level 4+",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase your Dexterity or Constitution score by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ["Dexterity", "Constitution"]
                }
            },
            {
                "type": "select_single",
                "description": "Choose one damage resistance.",
                "name": "damage_resistance",
                "source": {
                    "type": "fixed_list",
                    "options": ["Necrotic", "Psychic", "Radiant", "Thunder"]
                }
            }
        ],
        "choice_effects": {
            "ability": {
                "Dexterity": [{"type": "ability_bonus", "ability": "Dexterity", "value": 1}],
                "Constitution": [{"type": "ability_bonus", "ability": "Constitution", "value": 1}]
            },
            "damage_resistance": {
                dt: [{"type": "grant_damage_resistance", "damage_type": dt}]
                for dt in ["Necrotic", "Psychic", "Radiant", "Thunder"]
            }
        }
    }

    general_feats["Spell Subterfuge"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
            "Shrouding Spells: After you cast a spell that has a casting time of an action using a spell slot, you can take the Hide action as a Bonus Action on that turn.",
            "Sneaky Casting: If you have the Invisible condition from the Hide action, casting a spell with Verbal components does not end that condition if you succeed on a Dexterity (Stealth) check against the Passive Perception of any creature that could hear you."
        ],
        "category": "General",
        "prerequisite": "Level 4+, Spellcasting Feature",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 20.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": INT_WIS_CHA
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1}]
                for ab in INT_WIS_CHA
            }
        }
    }

    # Build Epic Boons (3)
    general_feats["Boon of Erupting Spellpower"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 30.",
            "Spell Eruption: When you cast a spell of level 1 or higher using a spell slot, you can cause a burst of arcane energy to erupt around you. Each creature of your choice within 15 feet of you takes Force damage equal to your spellcasting ability modifier plus twice the level of the spell slot expended."
        ],
        "category": "Epic Boon",
        "prerequisite": "Level 19+, Spellcasting Feature",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 30.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": INT_WIS_CHA
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1, "maximum": 30}]
                for ab in INT_WIS_CHA
            }
        }
    }

    general_feats["Boon of Magic School Mastery"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 30.",
            "School Mastery: Choose one school of magic. Spells you cast from that school cannot be countered by Counterspell, and creatures have Disadvantage on saving throws against them."
        ],
        "category": "Epic Boon",
        "prerequisite": "Level 19+, Spellcasting Feature",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase your Intelligence, Wisdom, or Charisma score by 1, to a maximum of 30.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": INT_WIS_CHA
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1, "maximum": 30}]
                for ab in INT_WIS_CHA
            }
        }
    }

    general_feats["Boon of the Iron Mind"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Ability Score Increase: Increase one ability score of your choice by 1, to a maximum of 30.",
            "Iron Will: You have Advantage on Intelligence, Wisdom, and Charisma saving throws. In addition, you are immune to the Charmed and Frightened conditions."
        ],
        "category": "Epic Boon",
        "prerequisite": "Level 19+",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "description": "Increase one ability score of your choice by 1, to a maximum of 30.",
                "name": "ability",
                "source": {
                    "type": "fixed_list",
                    "options": ALL_ABILITIES
                }
            }
        ],
        "choice_effects": {
            "ability": {
                ab: [{"type": "ability_bonus", "ability": ab, "value": 1, "maximum": 30}]
                for ab in ALL_ABILITIES
            }
        }
    }

    # Build Fighting Style Feat (1)
    arcane_warrior_cantrips = ["Dancing Lights", "Light", "Message", "Prestidigitation", "True Strike"]
    general_feats["Arcane Warrior"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Arcane Armament: You learn two cantrips of your choice from the following list: Dancing Lights, Light, Message, Prestidigitation, or True Strike. Intelligence, Wisdom, or Charisma is your spellcasting ability for them (choose when you select this style)."
        ],
        "category": "Fighting Style",
        "prerequisite": "Fighting Style Feature",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_multiple",
                "count": 2,
                "name": "cantrips",
                "description": "Choose two cantrips from the list.",
                "source": {
                    "type": "fixed_list",
                    "options": arcane_warrior_cantrips
                }
            }
        ],
        "choice_effects": {
            "cantrips": {
                c: [{"type": "grant_cantrip", "spell": c}]
                for c in arcane_warrior_cantrips
            }
        }
    }

    # Build Origin Feats (10)
    origin_feats["Arcane Artist"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Minor Illusion cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Inspiring Magic: When you cast a spell from the Illusion school, you can choose one ally within 30 feet of yourself who can see you. That ally gains Heroic Inspiration. Once you use this benefit, you can't use it again until you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Minor Illusion"}
        ]
    }

    origin_feats["Arcane Eloquence"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Friends cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Silver Tongue: You have Advantage on Charisma (Deception and Persuasion) checks made against Humanoids who are indifferent or friendly toward you."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Friends"}
        ]
    }

    origin_feats["Arcane Infiltrator"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Friends cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Cunning Diversion: You can take the Dodge action as a Bonus Action. You can use this benefit a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Friends"}
        ]
    }

    origin_feats["Arcane Omens"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Guidance cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Fateful Omen: When a creature you can see within 30 feet makes an attack roll or saving throw, you can use your Reaction to add or subtract 1d4 from the roll. Once you use this benefit, you can't do so again until you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Guidance"}
        ]
    }

    origin_feats["Arcane Overload"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Fire Bolt cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Volatile Discharge: When you deal damage with a cantrip or spell of level 1 or higher, you can cause the spell to deal extra damage equal to your Proficiency Bonus to the target or to another creature within 5 feet of it. Once you use this benefit, you can't do so again until you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Fire Bolt"}
        ]
    }

    origin_feats["Arcane Safeguard"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn the Resistance cantrip. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Warding Barrier: When you or a creature within 30 feet of you takes damage, you can take a Reaction to give the target Resistance to that damage instance. Once you use this benefit, you can't do so again until you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_cantrip", "spell": "Resistance"}
        ]
    }

    origin_feats["Arcane Undertaker"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Cantrip: You learn one Cleric or Wizard cantrip of your choice from the Necromancy school: Chill Touch, Spare the Dying, or Toll the Dead. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell (choose when you select this feat).",
            "Knowledge from the Dead: When you make an Intelligence (History) or Wisdom (Medicine) check, you can roll 1d4 and add the number rolled to the ability check.",
            "Understanding of Death: When you take the Help action to stabilize a creature with 0 Hit Points, you gain Heroic Inspiration. Once you use this benefit, you can't use it again until you finish a Long Rest."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "name": "cantrip",
                "description": "Choose one Cleric or Wizard cantrip from the Necromancy school.",
                "source": {
                    "type": "fixed_list",
                    "options": ["Chill Touch", "Spare the Dying", "Toll the Dead"]
                }
            }
        ],
        "choice_effects": {
            "cantrip": {
                c: [{"type": "grant_cantrip", "spell": c}]
                for c in ["Chill Touch", "Spare the Dying", "Toll the Dead"]
            }
        }
    }

    origin_feats["Familiar Friend"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Find Familiar: You always have Find Familiar prepared. You can cast it once without expending a spell slot or material components, and you regain the ability to cast it in that way when you finish a Long Rest.",
            "Familiar Scout: You can communicate telepathically with your familiar and perceive through its senses as long as you are on the same plane of existence."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "grant_spell", "spell": "Find Familiar", "counts_against_limit": False}
        ]
    }

    origin_feats["Portal Jumper"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Otherworldly Resilience: You have Resistance to one of the following damage types: Necrotic, Psychic, or Radiant.",
            "Portal Step: You can spend 15 feet of movement to teleport to an unoccupied space you can see within 15 feet."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "choices": [
            {
                "type": "select_single",
                "name": "damage_resistance",
                "description": "Choose one damage resistance.",
                "source": {
                    "type": "fixed_list",
                    "options": ["Necrotic", "Psychic", "Radiant"]
                }
            }
        ],
        "choice_effects": {
            "damage_resistance": {
                dt: [{"type": "grant_damage_resistance", "damage_type": dt}]
                for dt in ["Necrotic", "Psychic", "Radiant"]
            }
        }
    }

    origin_feats["Transmuted Anatomy"] = {
        "description": "You gain the following benefits.",
        "benefits": [
            "Lengthened Stride: Your Speed increases by 5 feet.",
            "Resilient Anatomy: You have Advantage on saving throws against effects that would alter your form or impose the Paralyzed or Petrified condition."
        ],
        "category": "Origin",
        "prerequisite": "None",
        "source": "Arcana Unleashed",
        "effects": [
            {"type": "increase_speed", "value": 5}
        ]
    }

    # 5. Spells (33)
    with open(DATA_DIR / "book-au.json", "r", encoding="utf-8") as f:
        book_data = json.load(f)

    spell_classes_map = {}
    def find_spells_table(obj):
        if isinstance(obj, dict):
            if obj.get("type") == "table" and obj.get("caption") == "Spells":
                return obj
            for v in obj.values():
                r = find_spells_table(v)
                if r: return r
        elif isinstance(obj, list):
            for item in obj:
                r = find_spells_table(item)
                if r: return r
        return None

    tbl = find_spells_table(book_data)
    if tbl:
        for row in tbl.get("rows", []):
            if len(row) >= 5:
                sp_name_raw = clean_text(row[1]).replace("*", "")
                classes_raw = clean_text(row[4])
                classes_list = [c.strip() for c in classes_raw.split(",") if c.strip()]
                spell_classes_map[sp_name_raw] = classes_list

    with open(DATA_DIR / "spells-au.json", "r", encoding="utf-8") as f:
        raw_spells = json.load(f)

    spells = []
    spell_class_lists = {
        "artificer": {"spells_by_level": {}},
        "bard": {"spells_by_level": {}},
        "cleric": {"spells_by_level": {}},
        "druid": {"spells_by_level": {}},
        "paladin": {"spells_by_level": {}},
        "ranger": {"spells_by_level": {}},
        "sorcerer": {"spells_by_level": {}},
        "warlock": {"spells_by_level": {}},
        "wizard": {"spells_by_level": {}}
    }

    for sp in raw_spells.get("spell", []):
        name = sp.get("name")
        lvl = sp.get("level", 1)
        school_code = sp.get("school", "A")
        school = SCHOOL_MAP.get(school_code, "Abjuration")
        casting_time = format_time(sp.get("time", []))
        range_str = format_range(sp.get("range", {}))
        components = format_components(sp.get("components", {}))
        duration = format_duration(sp.get("duration", []))
        ritual = any(d.get("ritual") for d in sp.get("duration", [])) or (sp.get("meta", {}).get("ritual", False))
        classes = spell_classes_map.get(name, ["Wizard"])
        description = entries_to_text(sp.get("entries", []))

        spell_def = {
            "name": name,
            "level": lvl,
            "school": school,
            "casting_time": casting_time,
            "range": range_str,
            "components": components,
            "duration": duration,
            "description": description,
            "classes": classes,
            "ritual": ritual,
            "source": "Arcana Unleashed"
        }
        spells.append(spell_def)

        lvl_str = str(lvl)
        for cls_name in classes:
            c_key = cls_name.lower()
            if c_key in spell_class_lists:
                if lvl_str not in spell_class_lists[c_key]["spells_by_level"]:
                    spell_class_lists[c_key]["spells_by_level"][lvl_str] = []
                spell_class_lists[c_key]["spells_by_level"][lvl_str].append(name)

    # Assemble package
    package = {
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

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {OUTPUT_PATH}")
    print(f" - {len(subclasses)} Subclasses")
    print(f" - {len(backgrounds)} Backgrounds")
    print(f" - {len(origin_feats)} Origin Feats")
    print(f" - {len(general_feats)} General/Style/Boon Feats")
    print(f" - {len(spells)} Spells")

if __name__ == "__main__":
    build()
