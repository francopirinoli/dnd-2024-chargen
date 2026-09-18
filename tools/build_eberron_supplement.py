import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(".").resolve()
sys.path.insert(0, str(REPO_ROOT))

from modules.supplement_manager import get_supplement_manager

with open(r'C:\Users\Ventas\.gemini\antigravity\brain\689aface-04ea-4698-95fa-ef2b1cc59d75\scratch\scraped_eberron.json', 'r', encoding='utf-8') as f:
    scraped = json.load(f)

# Helper to clean description
def clean_text(t: str) -> str:
    # remove source line if present
    lines = t.strip().split('\n')
    clean_lines = []
    for l in lines:
        if l.strip().startswith("Source:"):
            continue
        clean_lines.append(l)
    return '\n'.join(clean_lines).strip()

manifest = {
    "id": "eberron-forge-of-the-artificer",
    "title": "Eberron: Forge of the Artificer",
    "publisher": "Wizards of the Coast",
    "version": "1.0.0",
    "compatibility": "2024",
    "description": "Character options from Eberron: Forge of the Artificer: the Artificer class (5 subclasses: Alchemist, Armorer, Artillerist, Battle Smith, Cartographer), 5 species (Changeling, Kalashtar, Khoravar, Shifter with 4 lineages, Warforged), 17 backgrounds, 28 feats, and the Homunculus Servant spell.",
    "dependencies": ["core-phb-2024"]
}

# 1. Artificer Class
artificer_class = {
    "name": "Artificer",
    "description": "Masters of invention, Artificers use ingenuity and magic to unlock extraordinary capabilities in objects. They see magic as a complex system waiting to be decoded and then harnessed in their spells and inventions.",
    "hit_die": 8,
    "primary_ability": "Intelligence",
    "saving_throw_proficiencies": ["Constitution", "Intelligence"],
    "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
    "weapon_proficiencies": ["Simple weapons"],
    "tool_proficiencies": ["Thieves' Tools", "Tinker's Tools", "Artisan's Tools"],
    "skill_proficiencies_count": 2,
    "skill_options": [
        "Arcana", "History", "Investigation", "Medicine", "Nature", "Perception", "Sleight of Hand"
    ],
    "subclass_selection_level": 3,
    "spellcasting_ability": "Intelligence",
    "spellcasting_type": "half",
    "spellcasting_focus": ["Thieves' Tools", "Tinker's Tools", "Artisan's Tools"],
    "proficiency_bonus_by_level": {
        "1": 2, "2": 2, "3": 2, "4": 2,
        "5": 3, "6": 3, "7": 3, "8": 3,
        "9": 4, "10": 4, "11": 4, "12": 4,
        "13": 5, "14": 5, "15": 5, "16": 5,
        "17": 6, "18": 6, "19": 6, "20": 6
    },
    "cantrips_by_level": {
        "1": 2, "2": 2, "3": 2, "4": 2,
        "5": 2, "6": 2, "7": 2, "8": 2,
        "9": 2, "10": 3, "11": 3, "12": 3,
        "13": 3, "14": 4, "15": 4, "16": 4,
        "17": 4, "18": 4, "19": 4, "20": 4
    },
    "prepared_spells_by_level": {
        "1": 2, "2": 3, "3": 4, "4": 5,
        "5": 6, "6": 6, "7": 7, "8": 7,
        "9": 9, "10": 9, "11": 10, "12": 10,
        "13": 11, "14": 11, "15": 12, "16": 12,
        "17": 14, "18": 14, "19": 15, "20": 15
    },
    "spell_slots_by_level": {
        "1":  [2, 0, 0, 0, 0, 0, 0, 0, 0],
        "2":  [2, 0, 0, 0, 0, 0, 0, 0, 0],
        "3":  [3, 0, 0, 0, 0, 0, 0, 0, 0],
        "4":  [3, 0, 0, 0, 0, 0, 0, 0, 0],
        "5":  [4, 2, 0, 0, 0, 0, 0, 0, 0],
        "6":  [4, 2, 0, 0, 0, 0, 0, 0, 0],
        "7":  [4, 3, 0, 0, 0, 0, 0, 0, 0],
        "8":  [4, 3, 0, 0, 0, 0, 0, 0, 0],
        "9":  [4, 3, 2, 0, 0, 0, 0, 0, 0],
        "10": [4, 3, 2, 0, 0, 0, 0, 0, 0],
        "11": [4, 3, 3, 0, 0, 0, 0, 0, 0],
        "12": [4, 3, 3, 0, 0, 0, 0, 0, 0],
        "13": [4, 3, 3, 1, 0, 0, 0, 0, 0],
        "14": [4, 3, 3, 1, 0, 0, 0, 0, 0],
        "15": [4, 3, 3, 2, 0, 0, 0, 0, 0],
        "16": [4, 3, 3, 2, 0, 0, 0, 0, 0],
        "17": [4, 3, 3, 3, 1, 0, 0, 0, 0],
        "18": [4, 3, 3, 3, 1, 0, 0, 0, 0],
        "19": [4, 3, 3, 3, 2, 0, 0, 0, 0],
        "20": [4, 3, 3, 3, 2, 0, 0, 0, 0]
    },
    "features_by_level": {
        "1": {
            "Spellcasting": {
                "description": "You produce your Artificer spells through tools. You can use Thieves' Tools, Tinker's Tools, or another kind of Artisan's Tools with which you have proficiency as a Spellcasting Focus. You prepare the list of level 1+ spells available to cast, starting with two level 1 Artificer spells, and know two Artificer cantrips. You can change your cantrips whenever you finish a Long Rest.",
                "feature_kind": "spellcasting_setup"
            },
            "Tinker's Magic": {
                "description": "You learn the Prestidigitation and Mending cantrips. In addition, you can touch a Tiny nonmagical object as a Magic action and invest it with a minor magical property that lasts indefinitely: emitting light (5 ft bright/5 ft dim), playing a recorded message of up to 6 seconds on tap, emitting an odor or sound, or displaying a static visual effect. You can have active objects equal to your Intelligence modifier (minimum 1).",
                "effects": [
                    {"type": "grant_cantrip", "spell": "Prestidigitation", "counts_against_limit": False},
                    {"type": "grant_cantrip", "spell": "Mending", "counts_against_limit": False}
                ]
            }
        },
        "2": {
            "Replicate Magic Item": "You learn how to replicate certain magic items. You know four plans from the Replicate Magic Item Plans table. Whenever you finish a Long Rest, you can touch a number of nonmagical objects equal to the number in the Magic Items column of the Artificer Features table and turn them into your chosen magic items. The items remain magical until you die or end the effect."
        },
        "3": {
            "Artificer Subclass": {
                "description": "You choose an Artificer subclass: Alchemist, Armorer, Artillerist, Battle Smith, or Cartographer. Your subclass grants you features at Artificer levels 3, 5, 9, and 15.",
                "feature_kind": "subclass_pick"
            },
            "The Right Tool for the Job": "With Tinker's Tools in hand, you can magically produce one set of Artisan's Tools or Thieves' Tools in an unoccupied space within 5 feet of yourself as a Magic action. This creation requires 1 hour of uninterrupted work, which can coincide with a Short or Long Rest."
        },
        "4": {
            "Ability Score Improvement": {
                "description": "You gain the Ability Score Improvement feat or another feat of your choice for which you qualify.",
                "feature_kind": "asi"
            }
        },
        "5": {
            "Subclass Feature": {
                "description": "You gain a feature from your Artificer subclass.",
                "feature_kind": "subclass_feature_slot"
            }
        },
        "6": {
            "Magic Item Tinker": "Your expertise with magic items deepens. You can attune to up to four magic items at once. In addition, your proficiency bonus is doubled for any ability check that uses your proficiency with a tool."
        },
        "7": {
            "Flash of Genius": "When you or another creature you can see within 30 feet of you makes an ability check or a saving throw, you can take a Reaction to add your Intelligence modifier (minimum of +1) to the roll. You can use this feature a number of times equal to your Intelligence modifier (minimum of once), and you regain all expended uses when you finish a Long Rest."
        },
        "8": {
            "Ability Score Improvement": {
                "description": "You gain the Ability Score Improvement feat or another feat of your choice for which you qualify.",
                "feature_kind": "asi"
            }
        },
        "9": {
            "Subclass Feature": {
                "description": "You gain a feature from your Artificer subclass.",
                "feature_kind": "subclass_feature_slot"
            }
        },
        "10": {
            "Magic Item Adept": "You can attune to up to five magic items at once. In addition, if you craft a magic item with a rarity of Common or Uncommon, it takes a quarter of the normal time and costs half as much."
        },
        "11": {
            "Spell-Storing Item": "Whenever you finish a Long Rest, you can touch one Simple or Martial weapon or an item that you can use as a Spellcasting Focus, and store a level 1 or 2 spell in it from the Artificer spell list that has a casting time of 1 action. A creature holding the item can use a Magic action to cast the stored spell from it using your spellcasting ability modifier. The spell can be cast from the item a number of times equal to twice your Intelligence modifier (minimum of twice)."
        },
        "12": {
            "Ability Score Improvement": {
                "description": "You gain the Ability Score Improvement feat or another feat of your choice for which you qualify.",
                "feature_kind": "asi"
            }
        },
        "13": {},
        "14": {
            "Advanced Artifice": "You ignore all species, class, spell, and level requirements on attuning to or using a magic item. You also learn one additional plan from the Replicate Magic Item Plans table."
        },
        "15": {
            "Subclass Feature": {
                "description": "You gain a feature from your Artificer subclass.",
                "feature_kind": "subclass_feature_slot"
            }
        },
        "16": {
            "Ability Score Improvement": {
                "description": "You gain the Ability Score Improvement feat or another feat of your choice for which you qualify.",
                "feature_kind": "asi"
            }
        },
        "17": {},
        "18": {
            "Magic Item Master": "You can attune to up to six magic items at once."
        },
        "19": {
            "Epic Boon": {
                "description": "You gain an Epic Boon feat or another feat of your choice for which you qualify. Boon of Siberys is recommended.",
                "feature_kind": "asi"
            }
        },
        "20": {
            "Soul of Artifice": "You gain a +1 bonus to all saving throws per magic item you are currently attuned to. In addition, if you're reduced to 0 Hit Points but not killed outright, you can use your Reaction to end one of your Artificer infusions or replications, causing you to drop to 1 Hit Point instead of 0."
        }
    },
    "starting_equipment": {
        "option_a": {
            "items": [
                "Studded Leather Armor",
                "Dagger",
                "Thieves' Tools",
                "Tinker's Tools",
                "Dungeoneer's Pack"
            ],
            "gold": 16
        },
        "option_b": {
            "gold": 150
        }
    },
    "multiclassing": {
        "hit_die_granted": 8,
        "armor_training": ["Light", "Medium", "Shields"],
        "weapon_training": ["Simple"],
        "tool_training": ["Thieves' Tools", "Tinker's Tools"],
        "skill_proficiencies": None,
        "saving_throw_proficiencies": [],
        "other_proficiencies": [],
        "notes": None,
        "source_text": "As a Multiclass Character: Gain the following traits from the Core Artificer Traits table: Hit Point Die, training with Light and Medium armor and Shields, and proficiency with Thieves' Tools and Tinker's Tools. Gain the Artificer's level 1 features, which are listed in the Artificer Features table. See the multiclassing rules to determine your available spell slots."
    }
}

# 2. Subclasses
subclasses = [
    {
        "name": "Alchemist",
        "class": "Artificer",
        "description": "An Alchemist is an expert at combining reagents to produce mystical effects. Alchemists use their creations to give life and to leech it away. Alchemy is the oldest of Artificer traditions, and its versatility has long been valued during times of war and peace.",
        "source": "Eberron: Forge of the Artificer",
        "features_by_level": {
            "3": {
                "Tools of the Trade": {
                    "description": "You gain proficiency with Alchemist's Supplies. If you already have this proficiency, you gain proficiency with one other type of Artisan's Tools of your choice.",
                    "effects": [
                        {"type": "grant_tool_proficiency", "tools": ["Alchemist's Supplies"]}
                    ]
                },
                "Alchemist Spells": {
                    "description": "You always have certain spells prepared after you reach particular levels in this class: Healing Word, Ray of Sickness (Level 3); Flaming Sphere, Melf's Acid Arrow (Level 5); Gaseous Form, Mass Healing Word (Level 9); Death Ward, Vitriolic Sphere (Level 13); Cloudkill, Raise Dead (Level 17).",
                    "spells": {
                        "3": ["Healing Word", "Ray of Sickness"],
                        "5": ["Flaming Sphere", "Melf's Acid Arrow"],
                        "9": ["Gaseous Form", "Mass Healing Word"],
                        "13": ["Death Ward", "Vitriolic Sphere"],
                        "17": ["Cloudkill", "Raise Dead"]
                    },
                    "effects": [
                        {"type": "grant_spell", "spell": "Healing Word", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Ray of Sickness", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Flaming Sphere", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Melf's Acid Arrow", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Gaseous Form", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Mass Healing Word", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Death Ward", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Vitriolic Sphere", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Cloudkill", "min_level": 17, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Raise Dead", "min_level": 17, "counts_against_limit": False}
                    ]
                },
                "Experimental Elixir": "Whenever you finish a Long Rest while holding Alchemist's Supplies, you can use that tool to magically produce two elixirs in empty flasks you touch. Roll on the Experimental Elixir table for each elixir's effect (Healing, Swiftness, Resilience, Boldness, Flight, Transformation). You can create additional elixirs by expending a spell slot of level 1 or higher for each one."
            },
            "5": {
                "Alchemical Savant": "Whenever you cast a spell using your Alchemist's Supplies as the Spellcasting Focus, you gain a bonus to one roll of the spell that restores Hit Points or deals Acid, Fire, Necrotic, or Poison damage. The bonus equals your Intelligence modifier (minimum of +1)."
            },
            "9": {
                "Restorative Reagents": "You can incorporate restorative reagents into some of your works: whenever a creature drinks an Experimental Elixir you created, the creature gains Temporary Hit Points equal to 2d6 plus your Intelligence modifier (minimum 1). In addition, you can cast Lesser Restoration without expending a spell slot a number of times equal to your Intelligence modifier per Long Rest."
            },
            "15": {
                "Chemical Mastery": "You gain Resistance to Acid damage and Poison damage, and you have Immunity to the Poisoned condition. You can also cast Greater Restoration and Heal once per Long Rest each without expending a spell slot and without preparing the spells."
            }
        }
    },
    {
        "name": "Armorer",
        "class": "Artificer",
        "description": "An Artificer who specializes as an Armorer modifies armor to function almost like a second skin. The armor is enhanced to hone the Artificer's magic, unleash potent attacks, and generate a formidable defense.",
        "source": "Eberron: Forge of the Artificer",
        "features_by_level": {
            "3": {
                "Tools of the Trade": {
                    "description": "You gain proficiency with Heavy armor and Smith's Tools. If you already have Smith's Tools proficiency, you gain proficiency with one other type of Artisan's Tools of your choice.",
                    "effects": [
                        {"type": "grant_armor_proficiency", "proficiencies": ["Heavy armor"]},
                        {"type": "grant_tool_proficiency", "tools": ["Smith's Tools"]}
                    ]
                },
                "Armorer Spells": {
                    "description": "You always have certain spells prepared after you reach particular levels in this class: Magic Missile, Thunderwave (Level 3); Mirror Image, Shatter (Level 5); Hypnotic Pattern, Lightning Bolt (Level 9); Fire Shield, Greater Invisibility (Level 13); Passwall, Wall of Force (Level 17).",
                    "spells": {
                        "3": ["Magic Missile", "Thunderwave"],
                        "5": ["Mirror Image", "Shatter"],
                        "9": ["Hypnotic Pattern", "Lightning Bolt"],
                        "13": ["Fire Shield", "Greater Invisibility"],
                        "17": ["Passwall", "Wall of Force"]
                    },
                    "effects": [
                        {"type": "grant_spell", "spell": "Magic Missile", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Thunderwave", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Mirror Image", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Shatter", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Hypnotic Pattern", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Lightning Bolt", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Fire Shield", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Greater Invisibility", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Passwall", "min_level": 17, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Wall of Force", "min_level": 17, "counts_against_limit": False}
                    ]
                },
                "Arcane Armor": "As a Magic action while holding Smith's Tools, you can turn a suit of armor you are wearing into Arcane Armor. While you wear it, you gain the following benefits: if the armor normally has a Strength requirement, the arcane armor lacks this requirement; you can use the arcane armor as a Spellcasting Focus for your Artificer spells; the armor attaches to you and can't be removed against your will; it expands to cover your entire body; and you can don or doff it as an action.",
                "Armor Model": "You can customize your Arcane Armor into one of two models: Guardian (Thunder Gauntlets, Defensive Field) or Infiltrator (Lightning Launcher, Powered Steps, Dampening Field). You can change the model whenever you finish a Short or Long Rest."
            },
            "5": {
                "Extra Attack": "You can attack twice, instead of once, whenever you take the Attack action on your turn."
            },
            "9": {
                "Improved Armorer": "Your Arcane Armor now counts as separate items for the purpose of your Infuse Item / Replicate Magic Item feature: armor (chest piece), boots, helmet, and the armor's special weapon. In addition, the maximum number of items you can infuse/replicate increases by 2, but those extra items must be part of your Arcane Armor."
            },
            "15": {
                "Perfected Armor": "Your Arcane Armor gains additional benefits based on its model: Guardian (Tinkered Pull reaction when Huge or smaller creature ends turn within 30 ft) or Infiltrator (creatures hit by Lightning Launcher are marked, granting attack Advantage and extra lightning damage)."
            }
        }
    },
    {
        "name": "Artillerist",
        "class": "Artificer",
        "description": "An Artillerist specializes in using magic to hurl energy, projectiles, and explosions on a battlefield. This destructive power was valued by all armies in the Last War.",
        "source": "Eberron: Forge of the Artificer",
        "features_by_level": {
            "3": {
                "Tools of the Trade": {
                    "description": "You gain proficiency with Woodcarver's Tools. If you already have this proficiency, you gain proficiency with one other type of Artisan's Tools of your choice.",
                    "effects": [
                        {"type": "grant_tool_proficiency", "tools": ["Woodcarver's Tools"]}
                    ]
                },
                "Artillerist Spells": {
                    "description": "You always have certain spells prepared after you reach particular levels in this class: Shield, Thunderwave (Level 3); Scorching Ray, Shatter (Level 5); Fireball, Wind Wall (Level 9); Ice Storm, Wall of Fire (Level 13); Cone of Cold, Wall of Force (Level 17).",
                    "spells": {
                        "3": ["Shield", "Thunderwave"],
                        "5": ["Scorching Ray", "Shatter"],
                        "9": ["Fireball", "Wind Wall"],
                        "13": ["Ice Storm", "Wall of Fire"],
                        "17": ["Cone of Cold", "Wall of Force"]
                    },
                    "effects": [
                        {"type": "grant_spell", "spell": "Shield", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Thunderwave", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Scorching Ray", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Shatter", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Fireball", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Wind Wall", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Ice Storm", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Wall of Fire", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Cone of Cold", "min_level": 17, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Wall of Force", "min_level": 17, "counts_against_limit": False}
                    ]
                },
                "Eldritch Cannon": "Using Smith's Tools or Woodcarver's Tools, you can take a Magic action to create a Small or Tiny Eldritch Cannon. The cannon lasts for 1 hour or until it is destroyed or you dismiss it. On each of your turns, you can take a Bonus Action to command the cannon to activate (Flamethrower, Force Ballista, or Protector)."
            },
            "5": {
                "Arcane Firearm": "You can turn a wand, staff, or rod into an Arcane Firearm using Woodcarver's Tools. When you cast an Artificer spell through the firearm, roll a 1d8 and add the number to one of the spell's damage rolls."
            },
            "9": {
                "Explosive Cannon": "Every Eldritch Cannon you create is more destructive: its damage rolls increase by 1d8. As an action, you can command the cannon to detonate if you are within 60 feet of it, dealing 3d8 Force damage to creatures within 20 feet on a failed Dex save."
            },
            "15": {
                "Fortified Position": "You can now have two cannons at the same time and activate both with the same Bonus Action. In addition, you and your allies have Half Cover while within 10 feet of a cannon."
            }
        }
    },
    {
        "name": "Battle Smith",
        "class": "Artificer",
        "description": "Armies require protection, and someone needs to put things back together if defenses fail. A combination of protector and medic, a Battle Smith is an expert at defending others and repairing materiel and personnel.",
        "source": "Eberron: Forge of the Artificer",
        "features_by_level": {
            "3": {
                "Tools of the Trade": {
                    "description": "You gain proficiency with Martial weapons and Smith's Tools. If you already have Smith's Tools proficiency, you gain proficiency with one other type of Artisan's Tools of your choice.",
                    "effects": [
                        {"type": "grant_weapon_proficiency", "proficiencies": ["Martial weapons"]},
                        {"type": "grant_tool_proficiency", "tools": ["Smith's Tools"]}
                    ]
                },
                "Battle Smith Spells": {
                    "description": "You always have certain spells prepared after you reach particular levels in this class: Heroism, Shield (Level 3); Shining Smite, Warding Bond (Level 5); Aura of Vitality, Conjure Barrage (Level 9); Aura of Purity, Fire Shield (Level 13); Banishing Smite, Mass Cure Wounds (Level 17).",
                    "spells": {
                        "3": ["Heroism", "Shield"],
                        "5": ["Shining Smite", "Warding Bond"],
                        "9": ["Aura of Vitality", "Conjure Barrage"],
                        "13": ["Aura of Purity", "Fire Shield"],
                        "17": ["Banishing Smite", "Mass Cure Wounds"]
                    },
                    "effects": [
                        {"type": "grant_spell", "spell": "Heroism", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Shield", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Shining Smite", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Warding Bond", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Aura of Vitality", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Conjure Barrage", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Aura of Purity", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Fire Shield", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Banishing Smite", "min_level": 17, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Mass Cure Wounds", "min_level": 17, "counts_against_limit": False}
                    ]
                },
                "Battle Ready": "When you attack with a magic weapon, you can use your Intelligence modifier, instead of Strength or Dexterity, for the attack and damage rolls.",
                "Steel Defender": "Your tinkering produces a faithful automaton companion: the Steel Defender. It obeys your commands and takes its turn immediately after yours in combat. You can command it to attack or take other actions as a Bonus Action."
            },
            "5": {
                "Extra Attack": "You can attack twice, instead of once, whenever you take the Attack action on your turn."
            },
            "9": {
                "Arcane Jolt": "Whenever you hit a target with a magic weapon attack or your Steel Defender hits a target, you can channel magical energy to deal an extra 2d6 Force damage to the target or heal 2d6 Hit Points to a creature within 30 feet. You can use this energy a number of times equal to your Intelligence modifier per Long Rest."
            },
            "15": {
                "Improved Defender": "Your Arcane Jolt and Steel Defender become more powerful: Arcane Jolt deals 4d6 damage or restores 4d6 HP. Your Steel Defender gains a +2 bonus to AC, and when it uses Deflect Attack, it also deals 1d4 + your Int modifier Force damage to the attacker."
            }
        }
    },
    {
        "name": "Cartographer",
        "class": "Artificer",
        "description": "Cartographers are the premier navigators and reconnaissance agents. Using their creations, Cartographers can highlight threats, safeguard allies, and carve portals to distant locations.",
        "source": "Eberron: Forge of the Artificer",
        "features_by_level": {
            "3": {
                "Tools of the Trade": {
                    "description": "You gain proficiency with Calligrapher's Supplies and Cartographer's Tools. If you already have one of these proficiencies, you gain proficiency with one other type of Artisan's Tools of your choice (or with two other types if you have both). In addition, when you scribe a Spell Scroll using the crafting rules, the amount of time required is halved.",
                    "effects": [
                        {"type": "grant_tool_proficiency", "tools": ["Calligrapher's Supplies", "Cartographer's Tools"]}
                    ]
                },
                "Cartographer Spells": {
                    "description": "You always have certain spells prepared after you reach particular levels in this class: Faerie Fire, Guiding Bolt, Healing Word (Level 3); Locate Object, Mind Spike (Level 5); Call Lightning, Clairvoyance (Level 9); Banishment, Locate Creature (Level 13); Scrying, Teleportation Circle (Level 17).",
                    "spells": {
                        "3": ["Faerie Fire", "Guiding Bolt", "Healing Word"],
                        "5": ["Locate Object", "Mind Spike"],
                        "9": ["Call Lightning", "Clairvoyance"],
                        "13": ["Banishment", "Locate Creature"],
                        "17": ["Scrying", "Teleportation Circle"]
                    },
                    "effects": [
                        {"type": "grant_spell", "spell": "Faerie Fire", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Guiding Bolt", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Healing Word", "min_level": 3, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Locate Object", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Mind Spike", "min_level": 5, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Call Lightning", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Clairvoyance", "min_level": 9, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Banishment", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Locate Creature", "min_level": 13, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Scrying", "min_level": 17, "counts_against_limit": False},
                        {"type": "grant_spell", "spell": "Teleportation Circle", "min_level": 17, "counts_against_limit": False}
                    ]
                },
                "Adventurer's Atlas": "Whenever you finish a Long Rest while holding Cartographer's Tools, you can use that tool to create a set of magical maps by touching at least two creatures (one of whom can be yourself), up to a maximum number of creatures equal to 1 plus your Intelligence modifier (minimum of two creatures). Each target receives a magical map that constantly updates to show the relative position of all map holders. Map holders add 1d4 to Initiative rolls and can target each other regardless of sight or cover if within range.",
                "Mapping Magic": "You can cast Faerie Fire without expending a spell slot a number of times equal to your Intelligence modifier per Long Rest. In addition, you can spend half your Speed to teleport up to 10 feet or within 5 feet of a creature within 30 feet holding one of your Adventurer's Atlas maps."
            },
            "5": {
                "Guided Precision": "Once per turn, whenever you cast a spell from your Cartographer Spells list or hit a creature affected by your Faerie Fire with an attack roll, you can add your Intelligence modifier to one damage roll. In addition, taking damage can't cause you to lose Concentration on Faerie Fire."
            },
            "9": {
                "Ingenious Movement": "When you use your Flash of Genius, you or a willing creature of your choice that you can see within 30 feet of yourself can teleport up to 30 feet to an unoccupied space you can see as part of that same Reaction."
            },
            "15": {
                "Superior Atlas": "Your Adventurer's Atlas improves: when a map holder would be reduced to 0 Hit Points, that creature can destroy its map to drop to twice your Artificer level in HP instead and teleport within 5 feet of another map holder. If you are a map holder, you can cast Find the Path once per Long Rest without expending a spell slot or material components."
            }
        }
    }
]

# 3. Species
species_list = [
    {
        "name": "Changeling",
        "description": "With ever-changing appearances, changelings reside in many societies undetected. Each changeling can supernaturally adopt any face they like. For some changelings, a new face may reveal an aspect of their soul.",
        "creature_type": "Fey",
        "size": "Medium or Small",
        "size_description": "Medium (about 4–7 feet tall) or Small (about 2–4 feet tall), chosen when you select this species",
        "speed": 30,
        "languages": ["Common"],
        "source": "Eberron: Forge of the Artificer",
        "traits": {
            "Changeling Instincts": {
                "description": "Thanks to your connection to the fey realm, you gain proficiency in two of the following skills of your choice: Deception, Insight, Intimidation, Performance, or Persuasion.",
                "type": "choice",
                "choices": {
                    "type": "select_multiple",
                    "count": 2,
                    "source": {
                        "type": "fixed_list",
                        "options": ["Deception", "Insight", "Intimidation", "Performance", "Persuasion"]
                    }
                }
            },
            "Shape-Shifter": {
                "description": "As an action, you can shape-shift to change your appearance and your voice, including coloration, hair length, sex, height, weight, and size between Medium and Small. While shape-shifted with this trait, you have Advantage on Charisma checks. You stay in the new form until you take an action to revert to your true form."
            }
        }
    },
    {
        "name": "Kalashtar",
        "description": "Kalashtar are created from the union of humanity and renegade spirits called quori from the plane of dreams. This connection grants kalashtar minor psionic abilities, as well as protection from psionic attacks.",
        "creature_type": "Aberration",
        "size": "Medium",
        "size_description": "Medium (about 6–7 feet tall)",
        "speed": 30,
        "languages": ["Common", "Quori"],
        "source": "Eberron: Forge of the Artificer",
        "traits": {
            "Dual Mind": {
                "description": "You have Advantage on Wisdom and Charisma saving throws."
            },
            "Mental Discipline": {
                "description": "You have Resistance to Psychic damage.",
                "effects": [
                    {
                        "type": "grant_damage_resistance",
                        "damage_type": "Psychic"
                    }
                ]
            },
            "Mind Link": {
                "description": "You have telepathy with a range in feet equal to 10 times your level. When you're using this trait to speak telepathically to a creature, you can take a Magic action to give that creature the ability to speak telepathically with you for 1 hour or until you take another Magic action to end this effect."
            },
            "Severed from Dreams": {
                "description": "You can't be the target of the Dream spell. In addition, when you finish a Long Rest, you gain proficiency in one skill of your choice. This proficiency lasts until you finish another Long Rest."
            }
        }
    },
    {
        "name": "Khoravar",
        "description": "Over the course of centuries, those descended from both humans and elves have developed their own communities and traditions in Khorvaire. Khoravar dislike the term 'half-elf', viewing themselves as the bridge between cultures and worlds.",
        "creature_type": "Humanoid",
        "size": "Medium or Small",
        "size_description": "Medium (about 4–6 feet tall) or Small (about 2–4 feet tall), chosen when you select this species",
        "speed": 30,
        "darkvision": 60,
        "languages": ["Common", "Elvish"],
        "source": "Eberron: Forge of the Artificer",
        "traits": {
            "Darkvision": {
                "description": "You have Darkvision with a range of 60 feet.",
                "effects": [
                    {
                        "type": "grant_darkvision",
                        "range": 60
                    }
                ]
            },
            "Fey Ancestry": {
                "description": "You have Advantage on saving throws you make to avoid or end the Charmed condition.",
                "effects": [
                    {
                        "type": "grant_save_advantage",
                        "condition": "Charmed"
                    }
                ]
            },
            "Fey Gift": {
                "description": "You know the Friends cantrip. Whenever you finish a Long Rest, you can replace that cantrip with a different cantrip from the Cleric, Druid, or Wizard spell list. Intelligence, Wisdom, or Charisma is your spellcasting ability for the spell you cast with this trait (chosen when you select this species)."
            },
            "Lethargy Resilience": {
                "description": "When you fail a saving throw to avoid or end the Unconscious condition, you can succeed instead. Once you use this trait, you can't do so again until you finish 1d4 Long Rests."
            },
            "Skill Versatility": {
                "description": "You gain proficiency in one skill or with one tool of your choice. Whenever you finish a Long Rest, you can replace it with another skill or tool proficiency."
            }
        }
    },
    {
        "name": "Shifter",
        "description": "Shifters - sometimes called 'weretouched' - descend from people who contracted full or partial lycanthropy. Humanoids with a bestial aspect, shifters can enhance their animalistic features temporarily in a process they call shifting.",
        "creature_type": "Humanoid",
        "size": "Medium or Small",
        "size_description": "Medium (about 4–7 feet tall) or Small (about 2–4 feet tall), chosen when you select this species",
        "speed": 30,
        "darkvision": 60,
        "languages": ["Common"],
        "source": "Eberron: Forge of the Artificer",
        "lineages": ["Beasthide", "Longtooth", "Swiftstride", "Wildhunt"],
        "traits": {
            "Darkvision": {
                "description": "You have Darkvision with a range of 60 feet.",
                "effects": [
                    {
                        "type": "grant_darkvision",
                        "range": 60
                    }
                ]
            },
            "Bestial Instincts": {
                "description": "Channeling the beast within, you gain proficiency in one of the following skills of your choice: Acrobatics, Athletics, Intimidation, or Survival.",
                "type": "choice",
                "choices": {
                    "type": "select_single",
                    "count": 1,
                    "source": {
                        "type": "fixed_list",
                        "options": ["Acrobatics", "Athletics", "Intimidation", "Survival"]
                    }
                },
                "choice_effects": {
                    "Acrobatics": [{"type": "grant_skill_proficiency", "skills": ["Acrobatics"]}],
                    "Athletics": [{"type": "grant_skill_proficiency", "skills": ["Athletics"]}],
                    "Intimidation": [{"type": "grant_skill_proficiency", "skills": ["Intimidation"]}],
                    "Survival": [{"type": "grant_skill_proficiency", "skills": ["Survival"]}]
                }
            },
            "Shifting": {
                "description": "As a Bonus Action, you can shape-shift to assume a more bestial appearance. This transformation lasts for 1 minute or until you revert to your normal appearance as a Bonus Action. When you shift, you gain Temporary Hit Points equal to 2 times your Proficiency Bonus. You can shift a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest."
            }
        }
    },
    {
        "name": "Warforged",
        "description": "Warforged are mechanical beings built as weapons to fight in the Last War. An unexpected breakthrough produced sentient beings made from wood and metal that nevertheless can feel pain and emotion.",
        "creature_type": "Construct",
        "size": "Medium or Small",
        "size_description": "Medium (about 6–8 feet tall) or Small (about 3–4 feet tall), chosen when you select this species",
        "speed": 30,
        "languages": ["Common"],
        "source": "Eberron: Forge of the Artificer",
        "traits": {
            "Construct Resilience": {
                "description": "You have Resistance to Poison damage. You also have Advantage on saving throws to avoid or end the Poisoned condition.",
                "effects": [
                    {
                        "type": "grant_damage_resistance",
                        "damage_type": "Poison"
                    },
                    {
                        "type": "grant_save_advantage",
                        "condition": "Poisoned"
                    }
                ]
            },
            "Integrated Protection": {
                "description": "You gain a +1 bonus to your Armor Class. In addition, armor you have donned can't be removed against your will while you're alive."
            },
            "Sentry's Rest": {
                "description": "You don't need to sleep, and magic can't put you to sleep. You can finish a Long Rest in 6 hours if you spend those hours in an inactive, motionless state. During this time, you appear inert but remain conscious."
            },
            "Specialized Design": {
                "description": "You gain one skill proficiency and one tool proficiency of your choice."
            },
            "Tireless": {
                "description": "You don't gain Exhaustion levels from dehydration, malnutrition, or suffocation."
            }
        }
    }
]

# 4. Species Variants (Lineages for Shifter)
species_variants = [
    {
        "name": "Beasthide",
        "parent_species": "Shifter",
        "description": "Stoic and solid, a beasthide shifter manifests tough hides and dense muscle when shifted.",
        "traits": {
            "Beasthide Shifting": {
                "description": "Whenever you shift, you gain 1d6 additional Temporary Hit Points. While shifted, you have a +1 bonus to your Armor Class."
            }
        }
    },
    {
        "name": "Longtooth",
        "parent_species": "Shifter",
        "description": "Fierce and aggressive, a longtooth shifter manifests elongated canine fangs when shifted.",
        "traits": {
            "Longtooth Shifting": {
                "description": "When you shift and as a Bonus Action on your other turns while shifted, you can use your elongated fangs to make an Unarmed Strike. If you hit with this Unarmed Strike and deal damage, you can deal Piercing damage equal to 1d6 plus your Strength modifier, instead of the normal damage of an Unarmed Strike."
            }
        }
    },
    {
        "name": "Swiftstride",
        "parent_species": "Shifter",
        "description": "Graceful and quick, a swiftstride shifter possesses feline agility and sudden bursts of speed.",
        "traits": {
            "Swiftstride Shifting": {
                "description": "While you are shifted, your Speed increases by 10 feet. Additionally, you can move up to 10 feet as a Reaction when a creature ends its turn within 5 feet of you. This reactive movement doesn't provoke Opportunity Attacks."
            }
        }
    },
    {
        "name": "Wildhunt",
        "parent_species": "Shifter",
        "description": "Sharp and vigilant, a wildhunt shifter possesses peerless senses and awareness.",
        "traits": {
            "Wildhunt Shifting": {
                "description": "While shifted, you have Advantage on Wisdom checks. Additionally, no creature within 30 feet of you can have Advantage on an attack roll against you unless you have the Incapacitated condition."
            }
        }
    }
]

# 5. Backgrounds (17)
bg_data_map = {
    "Aberrant Heir": {
        "description": "Your aberrant dragonmark has made life challenging since it manifested. You might have hidden it successfully for most of your life or managed to avoid notice. Alternatively, you might have encountered suspicion and fear, perhaps coupled with the outright antagonism of one or more dragonmarked houses.",
        "scores": ["Strength", "Constitution", "Charisma"],
        "suggested": {"Constitution": 2, "Charisma": 1},
        "feat": "Aberrant Dragonmark",
        "skills": ["History", "Intimidation"],
        "tool": "Disguise Kit",
        "eq_a": ["Dagger", "Disguise Kit", "Costume", "Traveler's Clothes"],
        "gold_a": 16
    },
    "Archaeologist": {
        "description": "You've made a lifelong study of the lost and fallen cultures of the past, visiting their ruins, deciphering their written records, and examining their surviving masterworks.",
        "scores": ["Dexterity", "Intelligence", "Wisdom"],
        "suggested": {"Intelligence": 2, "Wisdom": 1},
        "feat": "Skilled",
        "skills": ["History", "Survival"],
        "tool": "Cartographer's Tools",
        "eq_a": ["Cartographer's Tools", "Bullseye Lantern", "Map", "Map or Scroll Case", "Shovel", "Tent", "Traveler's Clothes"],
        "gold_a": 17
    },
    "House Agent": {
        "description": "You are connected to one of the dragonmarked houses, serving as the hands, feet, and eyes of house leadership in the world.",
        "scores": ["Strength", "Intelligence", "Charisma"],
        "suggested": {"Charisma": 2, "Intelligence": 1},
        "feat": "Lucky",
        "skills": ["Investigation", "Persuasion"],
        "tool": "Artisan's Tools",
        "eq_a": ["Artisan's Tools", "Fine Clothes"],
        "gold_a": 20
    },
    "House Cannith Heir": {
        "description": "As a scion of House Cannith, you carry a proud legacy of making and invention, creating wonders of the modern world.",
        "scores": ["Strength", "Dexterity", "Intelligence"],
        "suggested": {"Intelligence": 2, "Dexterity": 1},
        "feat": "Mark of Making",
        "skills": ["Investigation", "Sleight of Hand"],
        "tool": "Artisan's Tools",
        "eq_a": ["Artisan's Tools", "Crowbar", "Fine Clothes", "Pouch (2)"],
        "gold_a": 17
    },
    "House Deneith Heir": {
        "description": "As an heir of House Deneith, you've been trained for combat and the defense of others, upholding duty, honor, and law.",
        "scores": ["Strength", "Constitution", "Wisdom"],
        "suggested": {"Strength": 2, "Constitution": 1},
        "feat": "Mark of Sentinel",
        "skills": ["Insight", "Perception"],
        "tool": "Gaming Set",
        "eq_a": ["Spear", "Shortbow", "Arrow (20)", "Gaming Set", "Fine Clothes", "Healer's Kit", "Quiver"],
        "gold_a": 1
    },
    "House Ghallanda Heir": {
        "description": "Thanks to your connections to House Ghallanda, you grew up accustomed to creature comforts, lively conversation, good drink, and delicious food.",
        "scores": ["Dexterity", "Wisdom", "Charisma"],
        "suggested": {"Charisma": 2, "Dexterity": 1},
        "feat": "Mark of Hospitality",
        "skills": ["Insight", "Persuasion"],
        "tool": "Cook's Utensils",
        "eq_a": ["Cook's Utensils", "Fine Clothes", "Iron Pot", "Lamp", "Oil (5 flasks)", "Perfume"],
        "gold_a": 26
    },
    "House Jorasco Heir": {
        "description": "House Jorasco teaches that illness and injury stalk the living. You've been taught ways to combat these scourges, both magically and medically.",
        "scores": ["Dexterity", "Constitution", "Wisdom"],
        "suggested": {"Wisdom": 2, "Constitution": 1},
        "feat": "Mark of Healing",
        "skills": ["Medicine", "Stealth"],
        "tool": "Herbalism Kit",
        "eq_a": ["Herbalism Kit", "Fine Clothes", "Healer's Kit"],
        "gold_a": 25
    },
    "House Kundarak Heir": {
        "description": "As an heir of House Kundarak, you take great pride in safeguarding the valuables of Khorvaire with locks, wards, and banking expertise.",
        "scores": ["Strength", "Constitution", "Intelligence"],
        "suggested": {"Intelligence": 2, "Constitution": 1},
        "feat": "Mark of Warding",
        "skills": ["Arcana", "Investigation"],
        "tool": "Thieves' Tools",
        "eq_a": ["Thieves' Tools", "Fine Clothes"],
        "gold_a": 10
    },
    "House Lyrandar Heir": {
        "description": "As an heir of House Lyrandar, the wind is your ally, the sea and sky your dominion, piloting ships and airships across Khorvaire.",
        "scores": ["Strength", "Dexterity", "Charisma"],
        "suggested": {"Charisma": 2, "Dexterity": 1},
        "feat": "Mark of Storm",
        "skills": ["Acrobatics", "Nature"],
        "tool": "Navigator's Tools",
        "eq_a": ["Navigator's Tools", "Fine Clothes"],
        "gold_a": 10
    },
    "House Medani Heir": {
        "description": "As a member of House Medani, your life revolves around predicting threats to clients and defending against them before danger strikes.",
        "scores": ["Dexterity", "Intelligence", "Wisdom"],
        "suggested": {"Wisdom": 2, "Intelligence": 1},
        "feat": "Mark of Detection",
        "skills": ["Insight", "Investigation"],
        "tool": "Disguise Kit",
        "eq_a": ["Disguise Kit", "Fine Clothes"],
        "gold_a": 10
    },
    "House Orien Heir": {
        "description": "Before the Last War, Orien's trade roads and lightning rails were the lifeblood of Khorvaire. You keep goods and passengers moving across the land.",
        "scores": ["Dexterity", "Constitution", "Intelligence"],
        "suggested": {"Dexterity": 2, "Constitution": 1},
        "feat": "Mark of Passage",
        "skills": ["Acrobatics", "Athletics"],
        "tool": "Cartographer's Tools",
        "eq_a": ["Cartographer's Tools", "Fine Clothes", "Map", "Map or Scroll Case"],
        "gold_a": 18
    },
    "House Phiarlan Heir": {
        "description": "As a child of House Phiarlan, you combine artistic performance and entertainment with the gathering of secrets and intelligence.",
        "scores": ["Dexterity", "Wisdom", "Charisma"],
        "suggested": {"Charisma": 2, "Dexterity": 1},
        "feat": "Mark of Shadow",
        "skills": ["Deception", "Stealth"],
        "tool": "Disguise Kit",
        "eq_a": ["Disguise Kit", "Fine Clothes"],
        "gold_a": 10
    },
    "House Sivis Heir": {
        "description": "For thirty centuries, House Sivis has kept communication flowing, words recorded, and disputes settled among the dragonmarked houses and sovereigns.",
        "scores": ["Intelligence", "Wisdom", "Charisma"],
        "suggested": {"Intelligence": 2, "Charisma": 1},
        "feat": "Mark of Scribing",
        "skills": ["History", "Perception"],
        "tool": "Calligrapher's Supplies",
        "eq_a": ["Calligrapher's Supplies", "Fine Clothes", "Ink", "Ink Pen (5)", "Paper (30 sheets)", "Parchment (9 sheets)"],
        "gold_a": 8
    },
    "House Tharashk Heir": {
        "description": "In House Tharashk you learned self-reliance, prospecting, tracking, and bounty hunting from an early age.",
        "scores": ["Constitution", "Intelligence", "Wisdom"],
        "suggested": {"Wisdom": 2, "Constitution": 1},
        "feat": "Mark of Finding",
        "skills": ["Perception", "Survival"],
        "tool": "Gaming Set",
        "eq_a": ["Gaming Set", "Climber's Kit", "Fine Clothes", "Hunting Trap", "Manacles"],
        "gold_a": 2
    },
    "House Thuranni Heir": {
        "description": "Formed in the Shadow Schism, House Thuranni pairs shadow artistry and musical performance with discerning covert observation.",
        "scores": ["Dexterity", "Intelligence", "Charisma"],
        "suggested": {"Dexterity": 2, "Charisma": 1},
        "feat": "Mark of Shadow",
        "skills": ["Performance", "Stealth"],
        "tool": "Musical Instrument",
        "eq_a": ["Musical Instrument", "Costume", "Fine Clothes"],
        "gold_a": 13
    },
    "House Vadalis Heir": {
        "description": "You grew up with respect for family and nature, mastering animal breeding, care, and understanding the mysteries of the natural world.",
        "scores": ["Constitution", "Wisdom", "Charisma"],
        "suggested": {"Wisdom": 2, "Constitution": 1},
        "feat": "Mark of Handling",
        "skills": ["Animal Handling", "Nature"],
        "tool": "Herbalism Kit",
        "eq_a": ["Herbalism Kit", "Fine Clothes", "Net"],
        "gold_a": 29
    },
    "Inquisitive": {
        "description": "You have honed your talents of investigation and deduction—fueled by a boundless curiosity—to explore mysteries, find missing people, and solve crimes.",
        "scores": ["Constitution", "Intelligence", "Charisma"],
        "suggested": {"Intelligence": 2, "Constitution": 1},
        "feat": "Alert",
        "skills": ["Insight", "Investigation"],
        "tool": "Thieves' Tools",
        "eq_a": ["Thieves' Tools", "Bullseye Lantern", "Crowbar", "Oil (10 flasks)", "Traveler's Clothes"],
        "gold_a": 10
    }
}

backgrounds = []
for bg_name, b_info in bg_data_map.items():
    bg = {
        "name": bg_name,
        "description": b_info["description"],
        "edition": "2024",
        "status": "active",
        "source": "Eberron: Forge of the Artificer",
        "ability_score_increase": {
            "total": 3,
            "options": b_info["scores"],
            "suggested": b_info["suggested"]
        },
        "effects": [
            {
                "type": "grant_skill_proficiency",
                "skills": b_info["skills"]
            },
            {
                "type": "grant_origin_feat",
                "feat": b_info["feat"]
            },
            {
                "type": "grant_tool_proficiency",
                "tools": [b_info["tool"]]
            }
        ],
        "starting_equipment": {
            "option_a": {
                "items": b_info["eq_a"],
                "gold": b_info["gold_a"]
            },
            "option_b": {
                "gold": 50
            }
        }
    }
    backgrounds.append(bg)

# 6. Feats (13 Dragonmark origin feats, 14 general feats, 1 epic boon)
origin_feats = {}
for k, v in scraped['dragonmark_feats'].items():
    title = k.replace('-', ' ').title()
    text = clean_text(v['text'])
    # Parse benefits
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    desc = lines[0] if lines else ""
    benefits = []
    for line in lines[1:]:
        if line.startswith("Dragonmark Feat"):
            continue
        if line.startswith("Prerequisite:"):
            continue
        benefits.append(line)
    if not benefits:
        benefits = [desc]
    origin_feats[title] = {
        "description": desc,
        "benefits": benefits,
        "category": "Origin",
        "prerequisite": "Eberron Campaign, Can't Have Another Dragonmark Feat",
        "source": "Eberron: Forge of the Artificer"
    }

general_feats = {}
for k, v in scraped['general_feats'].items():
    title = k.replace('-', ' ').title()
    text = clean_text(v['text'])
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    desc = lines[0] if lines else ""
    prereq = "Level 4+"
    benefits = []
    for line in lines[1:]:
        if "Prerequisite:" in line:
            prereq = line.split("Prerequisite:")[1].strip(" )")
            continue
        benefits.append(line)
    if not benefits:
        benefits = [desc]
    general_feats[title] = {
        "description": desc,
        "benefits": benefits,
        "category": "General",
        "prerequisite": prereq,
        "source": "Eberron: Forge of the Artificer"
    }

# Boon of Siberys
boon_data = scraped['epic_boons']['boon-of-siberys']
boon_text = clean_text(boon_data['text'])
boon_lines = [l.strip() for l in boon_text.split('\n') if l.strip()]
boon_desc = boon_lines[0] if boon_lines else ""
boon_benefits = [l for l in boon_lines[1:] if not l.startswith("Epic Boon") and not l.startswith("Prerequisite:")]
general_feats["Boon of Siberys"] = {
    "description": boon_desc,
    "benefits": boon_benefits or [boon_desc],
    "category": "Epic Boon",
    "prerequisite": "Level 19+, Eberron Campaign",
    "source": "Eberron: Forge of the Artificer"
}

feats = {
    "origin_feats": origin_feats,
    "general_feats": general_feats
}

# 7. Spell: Homunculus Servant
hs_text = clean_text(scraped['spells']['homunculus-servant']['text'])
spells = [
    {
        "name": "Homunculus Servant",
        "level": 2,
        "school": "Conjuration",
        "casting_time": "1 hour",
        "range": "10 feet",
        "components": ["V", "S", "M (a gem worth 100+ GP)"],
        "duration": "Instantaneous",
        "description": hs_text,
        "classes": ["Artificer"],
        "ritual": True,
        "source": "Eberron: Forge of the Artificer"
    }
]

# 8. Spell Class Lists: Artificer
spell_class_lists = {
    "artificer": {
        "cantrips": [
            "Acid Splash", "Blade Ward", "Fire Bolt", "Guidance", "Light",
            "Mage Hand", "Mending", "Message", "Poison Spray",
            "Prestidigitation", "Ray of Frost", "Resistance",
            "Shocking Grasp", "Spare the Dying", "Thorn Whip", "Thunderclap",
            "True Strike"
        ],
        "spells_by_level": {
            "1": [
                "Alarm", "Cure Wounds", "Detect Magic", "Disguise Self",
                "Expeditious Retreat", "Faerie Fire", "False Life", "Feather Fall",
                "Grease", "Identify", "Jump", "Longstrider", "Purify Food and Drink",
                "Sanctuary", "Shield of Faith"
            ],
            "2": [
                "Aid", "Alter Self", "Arcane Lock", "Blur", "Continual Flame",
                "Darkvision", "Enhance Ability", "Enlarge/Reduce", "Heat Metal",
                "Homunculus Servant", "Invisibility", "Lesser Restoration",
                "Levitate", "Magic Mouth", "Magic Weapon", "Protection from Poison",
                "Rope Trick", "See Invisibility", "Spider Climb", "Web"
            ],
            "3": [
                "Blink", "Create Food and Water", "Dispel Magic", "Elemental Weapon",
                "Fly", "Gaseous Form", "Glyph of Warding", "Haste",
                "Protection from Energy", "Revivify", "Water Breathing", "Water Walk"
            ],
            "4": [
                "Arcane Eye", "Elemental Bane", "Fabricate", "Fire Shield",
                "Freedom of Movement", "Otiluke's Resilient Sphere", "Stone Shape", "Stoneskin"
            ],
            "5": [
                "Animate Objects", "Bigby's Hand", "Creation", "Greater Restoration",
                "Wall of Stone"
            ]
        }
    }
}

package = {
    "manifest": manifest,
    "classes": [artificer_class],
    "subclasses": subclasses,
    "species": species_list,
    "species_variants": species_variants,
    "backgrounds": backgrounds,
    "feats": feats,
    "spells": spells,
    "spell_class_lists": spell_class_lists
}

target_file = REPO_ROOT / "supplements" / "eberron-forge-of-the-artificer.json"
with open(target_file, "w", encoding="utf-8") as f:
    json.dump(package, f, indent=2, ensure_ascii=False)

print(f"Wrote supplement package to {target_file}")

mgr = get_supplement_manager()
valid, errors = mgr.validate_package(package)
if valid:
    print("VALIDATION SUCCESS: Package is strictly schema-compliant!")
else:
    print(f"VALIDATION FAILED with {len(errors)} error(s):")
    for e in errors:
        print(" -", e)
    sys.exit(1)
