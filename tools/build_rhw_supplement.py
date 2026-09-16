import json
import os
import sys
from pathlib import Path

# Set stdout encoding
sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUTPUT_PATH = REPO_ROOT / "supplements" / "ravenloft-the-horrors-within.json"

all_skills = [
    "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
    "History", "Insight", "Intimidation", "Investigation", "Medicine",
    "Nature", "Perception", "Performance", "Persuasion", "Religion",
    "Sleight of Hand", "Stealth", "Survival"
]

package = {
    "manifest": {
        "id": "ravenloft-the-horrors-within",
        "title": "Ravenloft: The Horrors Within",
        "publisher": "Wizards of the Coast",
        "version": "1.0.0",
        "compatibility": "2024",
        "description": "Character options from Ravenloft: The Horrors Within: 7 subclasses (Reanimator Artificer, College of Spirits Bard, Grave Domain Cleric, Hollow Warden Ranger, Phantom Rogue, Shadow Sorcery Sorcerer, Undead Patron Warlock), 4 species (Dhampir, Hexblood, Lupin, Reborn), 4 backgrounds (Haunted One, Investigator, Mist Wanderer, Spirit Medium), and 11 feats (Sharp Eye, Survivor, Aberrant Anatomy, Echoing Soul, Gathered Whispers, Living Shadow, Mist Walker, Second Skin, Symbiotic Being, Touch of Death, Watchers).",
        "dependencies": [
            "core-phb-2024"
        ]
    },
    "subclasses": [
        {
            "name": "Reanimator",
            "class": "Artificer",
            "description": "Reanimators unravel the boundaries between life and death through galvanism, anatomical modifications, and mad science. They assemble and animate artificial companions and master morbid medical procedures to bolster allies and scourge foes.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Reanimator Spells": {
                        "description": "You always have certain spells prepared after reaching particular levels in this class, as shown in the Reanimator Spells table.",
                        "effects": [
                            {"type": "grant_spell", "spell": "False Life", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Spare the Dying", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Witch Bolt", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Blindness/Deafness", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Enhance Ability", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Animate Dead", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Lightning Bolt", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Blight", "min_level": 13, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Death Ward", "min_level": 13, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Antilife Shell", "min_level": 17, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Raise Dead", "min_level": 17, "counts_against_limit": False}
                        ]
                    },
                    "Reanimator's Skill Set": "You gain proficiency with Alchemist's Supplies (or another artisan's tools if you already have it).\nJolt to Life: When casting Spare the Dying, you can modify it to revive the target. The target regains HP equal to your Artificer level. Creatures in a 10-foot Emanation around the target must make a Dexterity saving throw against your spell save DC or take Lightning damage (2d4, increasing to 3d4 at level 11 and 4d4 at level 17), or half damage on success. You can use this benefit a number of times equal to your Intelligence modifier (minimum of 1), and regain all expended uses after a Long Rest.",
                    "Reanimated Companion": "Using artisan's tools, you take a Magic action to create a Reanimated Companion in an unoccupied space within 5 feet. It is Friendly, acts on your turn, and can move and use its reaction on its own. It takes the Dodge action unless you command it to take an action as a Bonus Action. It has HP equal to 5 + five times your Artificer level, AC equal to 10 + your Intelligence modifier, and uses your Proficiency Bonus. It has Blindsight 60 ft, resistance to Necrotic and Poison, immunity to Lightning damage, and condition immunity to Charmed, Exhaustion, and Poisoned. It can attack with Dreadful Swipe (1d4 + Int mod necrotic damage, target cannot make opportunity attacks until start of its next turn). It has Lightning Absorption (regains HP equal to lightning damage dealt) and Death Burst (explodes when it dies, dealing 2d4 necrotic damage to creatures in 10-ft emanation on a failed Dex save). It lasts until you Long Rest, dismiss it as a Magic action, or die. You can only have one at a time."
                },
                "5": {
                    "Strange Modifications": "When you create your Reanimated Companion, it gains modifications of your choice. You choose 1 option at 5th level, 2 options at 9th level, and 3 options at 15th level:\n- Arcane Conduit: You can cast spells as though you were in the companion's space, using your own senses. Once per turn when you deal damage with an Evocation or Necromancy Artificer spell, you can add your Intelligence modifier to one damage roll if your companion is within 120 feet.\n- Ferocity: The damage die of your companion's Dreadful Swipe increases to 1d6.\n- Bloated (Requires Level 9+): The companion becomes Large. On a Dreadful Swipe hit, it pushes a Large or smaller target up to 10 feet away. You add your Intelligence modifier to its Death Burst damage.\n- Gaunt (Requires Level 9+): The companion's Speed and Climb Speed become 45 feet (can spider climb). Creatures of your choice starting their turn in a 10-foot Emanation from it must succeed on a Wisdom save against your spell save DC or be Frightened until their next turn.\n- Moist (Requires Level 9+): The companion gains a Swim Speed equal to its Speed and can squeeze through 1-inch gaps. Attackers within 10 feet that hit it take Acid damage equal to your Intelligence modifier."
                },
                "9": {
                    "Improved Reanimation": "The damage of your companion's Death Burst increases to 4d4. Necrotic damage dealt by your companion ignores Resistance. In addition, you gain access to the Bloated, Gaunt, and Moist options for Strange Modifications."
                },
                "15": {
                    "Refined Reanimation": "You can cast Raise Dead once per Long Rest without expending a spell slot or requiring material components, using your artisan's tools as the spellcasting focus.\nLife Transfer: As a Reaction when you or your companion takes damage, you can destroy the companion to heal Hit Points equal to its current Hit Points (this also triggers its Death Burst)."
                }
            }
        },
        {
            "name": "College of Spirits",
            "class": "Bard",
            "description": "Bards of the College of Spirits commune with the departed and weave ghostly tales of heroes, villains, and mysterious forces into potent arcane magic.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Channeler": "You learn the Guidance cantrip; its range is 60 feet when you cast it. You gain proficiency with the Playing Cards gaming set. You can use playing cards, a crystal, orb, candle, or ink pen as a spellcasting focus for your Bard spells.",
                    "Spirits from Beyond": "When you use a Bonus Action to give Bardic Inspiration, you can roll the die to channel a spirit from beyond. It stays channeled until unleashed or you finish a Short or Long Rest.\nControlled Channeling: As a Bonus Action, you can expend a use of Bardic Inspiration to choose a specific spirit from the Spirits from Beyond table whose number is less than or equal to the highest number on your Bardic Inspiration die.\nUnleash Spirit: As a Magic action, you unleash the channeled spirit on a creature you can see within 30 feet. Any saving throw required uses your Bard spell save DC:\n1. Beloved: Target regains HP equal to 1 roll of your BI die + Charisma modifier.\n2. Sharpshooter: Target takes Force damage equal to 1 roll of your BI die + Charisma modifier.\n3. Avenger: Until end of your next turn, any creature that hits the target with a melee attack takes Force damage equal to 1 roll of your BI die.\n4. Renegade: Target can immediately use a Reaction to teleport up to 30 feet to an unoccupied space it can see.\n5. Fortune Teller: Target has Advantage on D20 Tests until start of your next turn.\n6. Wayfarer: Target gains Temporary HP equal to 1 roll of your BI die + Bard level, and its Speed increases by 10 feet while having these THP.\n7. Trickster: Target makes a Wisdom save; fails take Psychic damage equal to 2 rolls of your BI die and are Charmed until start of your next turn (half damage on success).\n8. Shade: Target becomes Invisible until end of its next turn or it attacks/casts a spell. When the invisibility ends, creatures in a 5-foot Emanation must succeed on a Constitution save or take Necrotic damage equal to 2 rolls of your BI die.\n9. Arsonist: Target makes a Dexterity save, taking Fire damage equal to 4 rolls of your BI die on a failure, or half on success.\n10. Coward: Target and chosen creatures in a 30-foot Emanation must make a Wisdom save or be Frightened until start of your next turn (Speed halved, can take an Action or Bonus Action, not both).\n11. Brute: Chosen creatures in a 30-foot Emanation must make a Strength save or take Thunder damage equal to 3 rolls of your BI die and have the Prone condition (half damage on success).\n12. Priest: Target regains HP equal to 2 rolls of your BI die, and one condition ends (Blinded, Charmed, Deafened, Paralyzed, Poisoned, or Stunned)."
                },
                "6": {
                    "Empowered Channeling": "Power from Beyond: Once per turn when you cast a Bard spell with a spell slot that deals damage or restores Hit Points, you can roll 1d6 and add the number rolled to one damage roll of the spell or to the Hit Points restored.\nSpiritual Manifestation: You always have Spirit Guardians prepared. Once per Long Rest, you can cast it without expending a spell slot. Once per Short or Long Rest when you cast it, you can modify it so you and your allies in the spell's emanation have Half Cover."
                },
                "14": {
                    "Mystical Connection": "Whenever you roll on the Spirits from Beyond table, you can roll the die twice and choose which of the two effects to channel. If you roll the same number on both dice, you can ignore that number and choose any effect on the table."
                }
            }
        },
        {
            "name": "Grave Domain",
            "class": "Cleric",
            "description": "Gods of the grave watch over the line between life and death. Clerics of these deities take comfort in the natural cycle of mortality, ensuring that souls pass peacefully to the afterlife while hunting undead abominations.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Grave Domain Spells": {
                        "description": "When you reach a Cleric level specified in the Grave Domain Spells table, you thereafter always have the listed spells prepared.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Detect Evil and Good", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "False Life", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Gentle Repose", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Ray of Enfeeblement", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Revivify", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Vampiric Touch", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Blight", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Death Ward", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Dispel Evil and Good", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Raise Dead", "min_level": 9, "counts_against_limit": False}
                        ]
                    },
                    "Circle of Mortality": "You learn the Spare the Dying cantrip, and you can cast it as a Bonus Action. When you cast a spell or use Channel Divinity to restore Hit Points to a creature with 0 Hit Points, you maximize any dice rolled to restore HP.\nIn addition, once per turn when you deal damage to a creature that is missing any of its Hit Points, the creature takes extra Necrotic damage equal to 1d4 (increasing to 1d6 at 11th level).",
                    "Channel Divinity: Path to the Grave": "As a Bonus Action, you can expend one use of Channel Divinity to mark a creature you can see within 30 feet with a curse of mortality. Until the start of your next turn, the creature has Disadvantage on attack rolls and saving throws. When you or an ally hits the cursed creature with an attack, you can end the curse early (no action required) to cause the attack to deal extra Necrotic or Radiant damage (your choice) equal to your Cleric level."
                },
                "6": {
                    "Sentinel at Death's Door": "As a Reaction when you or a Bloodied ally within 60 feet of you is hit by an attack roll, you can halve the damage taken from that attack. If the attack was a critical hit, any additional effects triggered by the critical hit are canceled. You can use this feature a number of times equal to your Wisdom modifier (minimum of 1), and regain all expended uses after a Long Rest."
                },
                "17": {
                    "Divine Reaper": "Enhanced Necromancy: When you cast a Necromancy spell of level 5 or lower or a spell from your Grave Domain Spells table that targets only one creature, you can expend a use of Channel Divinity to target a second creature in range with the same spell (you must provide material components for both targets if required).\nKeeper of Souls: When an enemy within 60 feet of you dies, you or one ally within 60 feet regains Hit Points equal to twice your Cleric level. You can use this feature once per Short or Long Rest, or restore its use by expending a spell slot of level 6 or higher."
                }
            }
        },
        {
            "name": "Hollow Warden",
            "class": "Ranger",
            "description": "Hollow Wardens draw upon the cursed and primordial woodcraft of dark domains, letting the creeping rot and ancient brambles infuse their flesh with supernatural endurance and harrowing dread.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Hollow Warden Spells": {
                        "description": "When you reach a Ranger level specified in the Hollow Warden Spells table, you thereafter always have the listed spells prepared.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Wrathful Smite", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Alter Self", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Phantom Steed", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Dominate Beast", "min_level": 13, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Steel Wind Strike", "min_level": 17, "counts_against_limit": False}
                        ]
                    },
                    "Wrath of the Wild": "As a Bonus Action, you can expend one use of your Favored Enemy feature to transform into a harrowing warden of the wild for 1 minute. It ends early if you are Incapacitated, die, or dismiss it (no action required). While transformed, you gain the following benefits:\n- Ancient Armor: You gain a +1 bonus to Armor Class (increasing to +2 at 11th level).\n- Prowling Retribution: As a Reaction when a creature within 5 feet of you deals damage to you or an ally, you can make an Opportunity Attack against that creature.\n- Unnerving Aura: When you transform and at the start of each of your turns while transformed, each enemy in a 10-foot Emanation from you must make a Wisdom saving throw against your spell save DC or have the Frightened condition until the start of your next turn."
                },
                "7": {
                    "Hungering Might": "You gain a bonus to Constitution saving throws equal to your Wisdom modifier (minimum of +1).\nIn addition, once per turn while transformed by Wrath of the Wild, when you hit a creature with an attack and you are Bloodied, you regain Hit Points equal to 1d10 plus your Wisdom modifier."
                },
                "11": {
                    "Rot and Violence": "Your Wrath of the Wild improves:\n- Menacing Aura: Creatures that fail the saving throw against your Unnerving Aura cannot regain Hit Points and cannot take Reactions until the start of your next turn.\n- Strangling Roots: When you hit a creature with a weapon attack, you can apply either the Sap or Slow weapon mastery property to that attack, in addition to the weapon's normal mastery property."
                },
                "15": {
                    "Ancient Might": "You have Immunity to the Exhaustion condition.\n- Ominous Strikes: Your attack rolls against Frightened targets deal extra damage equal to your Wisdom modifier.\n- Persistent Wrath: If you are reduced to 0 Hit Points while transformed and not killed outright, you instead drop to Hit Points equal to twice your Ranger level. Once you use this benefit, you can't use it again until you finish a Long Rest, unless you expend a level 4+ spell slot to restore it."
                }
            }
        },
        {
            "name": "Phantom",
            "class": "Rogue",
            "description": "Many rogues walk a fine line between life and death, undertaking risks that lose them companions and take their own lives to the brink. Shrouded in death, Phantoms walk that line and draw upon restless spirits to gain knowledge, haunt their foes, and cheat mortality.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Whispers of the Dead": "Whenever you finish a Short or Long Rest, you gain one skill or tool proficiency of your choice from ghostly presence. This proficiency lasts until you finish another Short or Long Rest and choose a different one.",
                    "Wails from the Grave": "Immediately after you deal Sneak Attack damage to a creature on your turn, you can target a second creature that you can see within 30 feet of the first creature. Roll a number of Sneak Attack dice equal to half the number of dice you rolled for Sneak Attack (rounded up). The second creature takes Necrotic damage equal to the total roll. You can use this feature a number of times equal to your Dexterity modifier (minimum of once), and regain all expended uses after a Long Rest (or by destroying a soul trinket at level 9+)."
                },
                "9": {
                    "Tokens of the Departed": "When a creature within 30 feet of you dies, you can take a Reaction to trap a wisp of its soul, creating a soul trinket (a Tiny physical token). You can carry a maximum of 2 trinkets (3 at level 13, 4 at level 17), and regain up to 2 destroyed trinkets after a Long Rest.\nWhile you have at least one soul trinket on your person, you have Advantage on Death saving throws and Constitution saving throws.\nAs a Magic action, you can destroy a soul trinket to cast Augury (requiring no components, Constitution is your spellcasting ability) or to ask the departed soul a single question.\nYou can also destroy a trinket to use Wails from the Grave without expending a use of that feature.",
                    "Voice of Death": "You can cast Speak with Dead once per Short or Long Rest without expending a spell slot or spell components. Dexterity is your spellcasting ability for it. You can target one of your soul trinkets instead of a corpse to question that spirit."
                },
                "13": {
                    "Ghost Walk": "As a Bonus Action, you assume a spectral form for 10 minutes or until ended. While in this form, you gain a Fly Speed of 10 feet with hover, attack rolls against you have Disadvantage, and you can move through creatures and objects as Difficult Terrain (taking 1d10 Force damage if you end your turn inside an object). You can use this feature once per Long Rest, or by destroying one of your soul trinkets."
                },
                "17": {
                    "Death's Friend": "Death's Lament: When you use Wails from the Grave, you deal its necrotic damage to both the original target of your Sneak Attack and the second creature.\nDraw of Death: When you roll Initiative and have no soul trinkets, a soul trinket mysteriously appears in your hand."
                }
            }
        },
        {
            "name": "Shadow Sorcery",
            "class": "Sorcerer",
            "description": "You are a creature of shadow, your innate magic suffused with the morbid power of the Shadowfell or sinister dread. Darkness clings to you, shielding you from lethal harm and manifesting hound-like terrors that stalk your quarry.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Shadow Sorcery Spells": {
                        "description": "When you reach a Sorcerer level specified in the Shadow Sorcery Spells table, you thereafter always have the listed spells prepared.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Bane", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Darkness", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Inflict Wounds", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Pass without Trace", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Hunger of Hadar", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Nondetection", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Greater Invisibility", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Phantasmal Killer", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Contagion", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Creation", "min_level": 9, "counts_against_limit": False}
                        ]
                    },
                    "Power of Shadow": "Eyes of the Dark: You have Darkvision with a range of 120 feet and Blindsight with a range of 10 feet. You can also see normally through darkness created by your own spells.\nStrength of the Grave: When damage reduces you to 0 Hit Points and doesn't kill you outright, you can make a Charisma saving throw (DC 5 + the damage taken). On a successful save, you drop to Hit Points equal to your Charisma modifier plus your Sorcerer level instead. You can use this benefit once per Long Rest."
                },
                "6": {
                    "Beasts of Ill Omen": "By expending 3 Sorcery Points, you can cast Summon Beast as a Bonus Action without expending a spell slot or material components. The summoned beast is formed of writhing shadows. While an enemy is within 5 feet of the beast, that enemy has Disadvantage on saving throws against your Sorcerer spells. You can cast it this way without requiring Concentration, but the duration is 1 minute for that casting, and the spell ends early if you cast it again."
                },
                "14": {
                    "Shadow Walk": "While you are in Dim Light or Darkness, you can take a Bonus Action to magically teleport up to 120 feet to an unoccupied space you can see that is also in Dim Light or Darkness."
                },
                "18": {
                    "Umbral Form": "When you activate your Innate Sorcery, you can adopt a shadowy, umbral form for its duration. While in this form, you gain Resistance to all damage except Force and Radiant damage, and you gain Incorporeal Movement: you can move through other creatures and objects as if they were Difficult Terrain (taking 1d10 Force damage if you end your turn inside an object). You can use this feature once per Long Rest, or by spending 6 Sorcery Points."
                }
            }
        },
        {
            "name": "The Undead",
            "class": "Warlock",
            "description": "You have made a pact with a deathless entity from the Domains of Dread or beyond—a master of undeath such as Strahd von Zarovich, Azalin Rex, Lord Soth, or a powerful mummy lord. Your patron bestows horrific power to freeze mortal hearts and slip beyond the grasp of death.",
            "source": "Ravenloft: The Horrors Within",
            "features_by_level": {
                "3": {
                    "Undead Spells": {
                        "description": "The magic of your patron ensures you always have certain spells ready; when you reach a Warlock level specified in the Undead Spells table, you thereafter always have the listed spells prepared.",
                        "effects": [
                            {"type": "grant_spell", "spell": "Bane", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Ray of Sickness", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Blindness/Deafness", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Phantasmal Force", "min_level": 3, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Speak with Dead", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Summon Undead", "min_level": 5, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Greater Invisibility", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Phantasmal Killer", "min_level": 7, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Antilife Shell", "min_level": 9, "counts_against_limit": False},
                            {"type": "grant_spell", "spell": "Cloudkill", "min_level": 9, "counts_against_limit": False}
                        ]
                    },
                    "Form of Dread": "As a Bonus Action, you manifest an aspect of your patron's dreadful power for 1 minute (ends early if you are Incapacitated or die). While transformed:\n- You gain Temporary Hit Points equal to 1d10 plus your Warlock level.\n- You have Immunity to the Frightened condition.\n- Once per turn when you hit a creature with an attack roll, you can force it to make a Wisdom saving throw against your spell save DC. On a failed save, the creature is Frightened of you until the end of your next turn.\nYou can use this feature a number of times equal to your Charisma modifier (minimum of once), and regain all expended uses after a Long Rest."
                },
                "6": {
                    "Grave Touched": "Necrotic damage dealt by your attacks, Warlock spells, and features ignores Resistance. Once per turn when you cast a damage-dealing spell, you can change the spell's damage type to Necrotic.\nDreaded Necrosis: Once per turn when you hit with an attack and deal Necrotic damage while in your Form of Dread, you can roll one additional damage die of Necrotic damage.\nUndead Endurance: You don't need to sleep, and magic can't put you to sleep. You also don't gain Exhaustion from dehydration, malnutrition, or suffocation."
                },
                "10": {
                    "Necrotic Husk": "You gain Resistance to Necrotic damage, and you have Immunity to Necrotic damage while in your Form of Dread.\nUnholy Resuscitation: When you are reduced to 0 Hit Points and not killed outright, you can instead drop to Hit Points equal to twice your Warlock level and gain 1 level of Exhaustion. Each creature of your choice in a 30-foot Emanation must make a Constitution saving throw against your spell save DC, taking 2d10 + your Charisma modifier Necrotic damage on a failure, or half on a success. You can use this once per Short or Long Rest."
                },
                "14": {
                    "Superior Dread": "While transformed by your Form of Dread, you gain these benefits:\n- Dread Resistance: Resistance to Bludgeoning, Piercing, and Slashing damage.\n- Ghostly Flight: You gain a Fly Speed equal to your Speed with hover. You can move through creatures and objects as Difficult Terrain (taking 1d10 Force damage if you end your turn inside an object).\n- Profane Casting: You can cast Conjuration and Necromancy Warlock spells without Verbal, Somatic, or Material components (unless costly or consumed)."
                }
            }
        }
    ],
    "species": [
        {
            "name": "Dhampir",
            "description": "Poised between the worlds of the living and the undead, dhampirs retain their grip on mortality while possessing the supernatural grace, hunger, and speed of vampires. They often wage eternal struggles against their vampiric impulses or channel them against monsters.",
            "creature_type": "Humanoid",
            "size": "Medium or Small",
            "size_description": "Medium (about 4–7 feet tall) or Small (about 3–4 feet tall), chosen when you select this species",
            "speed": 35,
            "darkvision": 60,
            "languages": [
                "Common"
            ],
            "source": "Ravenloft: The Horrors Within",
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
                "Trace of Undeath": {
                    "description": "You have Resistance to Necrotic damage.",
                    "effects": [
                        {
                            "type": "grant_damage_resistance",
                            "damage_type": "Necrotic"
                        }
                    ]
                },
                "Spider Climb": {
                    "description": "You have a Climb Speed equal to your Speed. When you reach character level 3, you can also move up, down, and across vertical surfaces and on ceilings while leaving your hands free."
                },
                "Vampiric Bite": {
                    "description": "When you hit with the damage option of an Unarmed Strike, you can bite with your fangs, dealing 1d4 + Constitution modifier Piercing damage instead of the bludgeoning damage normal for an Unarmed Strike. A number of times per Long Rest equal to your Proficiency Bonus, if the target is not a Construct or Undead, you can empower yourself: you either regain Hit Points or gain a bonus to your next ability check or attack roll within 1 minute, equal to the Piercing damage dealt."
                }
            }
        },
        {
            "name": "Hexblood",
            "description": "Infused with eldritch fey magic by hags, ancient crones, or dark rituals, hexbloods manifest crown-like irises, elder-bark horns, and eerie fey senses. Though marked by sinister influences, many seek their own destinies apart from their dark origins.",
            "creature_type": "Fey",
            "size": "Medium or Small",
            "size_description": "Medium (about 4–7 feet tall) or Small (about 3–4 feet tall), chosen when you select this species",
            "speed": 30,
            "darkvision": 60,
            "languages": [
                "Common"
            ],
            "source": "Ravenloft: The Horrors Within",
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
                "Fey Creature Type": {
                    "description": "Your creature type is Fey rather than Humanoid."
                },
                "Eerie Token": {
                    "description": "As a Bonus Action once per Long Rest, you can harmlessly pull off a lock of hair, a nail, or a tooth to create a Tiny magical token. While the token exists, you can use a Magic action to send a telepathic message (up to 25 words) to its holder if within 10 miles. Alternatively, you can use a Magic action to see and hear through the token for up to 1 minute as if you were in its space, after which the token is destroyed."
                },
                "Hex Magic": {
                    "description": "You always have the Disguise Self and Hex spells prepared. You can cast each once per Long Rest without using a spell slot, and you can also cast them using any spell slots you have. Intelligence, Wisdom, or Charisma is your spellcasting ability for these spells (choose when you select this species).",
                    "effects": [
                        {
                            "type": "grant_spell",
                            "spell": "Disguise Self",
                            "level": 1,
                            "free_uses": 1,
                            "recovery": "long_rest"
                        },
                        {
                            "type": "grant_spell",
                            "spell": "Hex",
                            "level": 1,
                            "free_uses": 1,
                            "recovery": "long_rest"
                        }
                    ]
                }
            }
        },
        {
            "name": "Lupin",
            "description": "Canine humanoids blessed—or cursed—with the bloodline of lycanthropes and noble wolves, lupins are vigilant trackers and fierce pack defenders. Their heightened senses and savage jaws make them formidable hunters of the unnatural.",
            "creature_type": "Humanoid",
            "size": "Medium or Small",
            "size_description": "Medium (about 4–7 feet tall) or Small (about 3–4 feet tall), chosen when you select this species",
            "speed": 30,
            "darkvision": 60,
            "languages": [
                "Common"
            ],
            "source": "Ravenloft: The Horrors Within",
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
                "Werewolf Instincts": {
                    "description": "You gain proficiency in one of the following skills of your choice: Perception, Stealth, or Survival.",
                    "type": "choice",
                    "choices": {
                        "type": "select_single",
                        "count": 1,
                        "source": {
                            "type": "fixed_list",
                            "options": [
                                "Perception",
                                "Stealth",
                                "Survival"
                            ]
                        }
                    },
                    "choice_effects": {
                        "Perception": [{"type": "grant_skill_proficiency", "skills": ["Perception"]}],
                        "Stealth": [{"type": "grant_skill_proficiency", "skills": ["Stealth"]}],
                        "Survival": [{"type": "grant_skill_proficiency", "skills": ["Survival"]}]
                    }
                },
                "Feral Pounce": {
                    "description": "Your Unarmed Strikes deal Slashing damage instead of Bludgeoning damage. Once per turn, when you hit with an Unarmed Strike during the Attack action, you can use both the Damage and the Shove options."
                },
                "Howl": {
                    "description": "As a Bonus Action, you unleash a terrifying howl. Chosen creatures within 15 feet of you must make a Wisdom saving throw (DC 8 + your Constitution modifier + your Proficiency Bonus). On a failed save, a creature has Disadvantage on attack rolls and saving throws until the start of your next turn. You can use this trait a number of times equal to your Proficiency Bonus, and regain all expended uses when you finish a Long Rest."
                }
            }
        },
        {
            "name": "Reborn",
            "description": "Reborn have died and returned, yet remain in a state between life and death. Some are stitched together from grave remnants, while others were preserved by necromantic artifice or returned by the capricious whims of the Dark Powers with fading memories of past lives.",
            "creature_type": "Humanoid",
            "size": "Medium or Small",
            "size_description": "Medium (about 4–7 feet tall) or Small (about 3–4 feet tall), chosen when you select this species",
            "speed": 30,
            "darkvision": 60,
            "languages": [
                "Common"
            ],
            "source": "Ravenloft: The Horrors Within",
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
                "Escaped Death": {
                    "description": "You have Advantage on Death Saving Throws."
                },
                "Everlasting": {
                    "description": "You do not suffer Exhaustion from dehydration, malnutrition, or suffocation. You do not need to sleep, and magic cannot put you to sleep. You can finish a Long Rest in 4 hours of motionless inactivity."
                },
                "Knowledge from a Past Life": {
                    "description": "You gain proficiency in one skill of your choice. In addition, a number of times per Long Rest equal to your Proficiency Bonus, when you fail an ability check, you can roll 1d6 and add it to the result, potentially turning the failure into a success.",
                    "type": "choice",
                    "choices": {
                        "type": "select_single",
                        "count": 1,
                        "source": {
                            "type": "fixed_list",
                            "options": all_skills
                        }
                    },
                    "choice_effects": {
                        skill: [{"type": "grant_skill_proficiency", "skills": [skill]}] for skill in all_skills
                    }
                },
                "Strange Endurance": {
                    "description": "You have Resistance to Cold, Necrotic, or Poison damage (choose when you select this species).",
                    "type": "choice",
                    "choices": {
                        "type": "select_single",
                        "count": 1,
                        "source": {
                            "type": "fixed_list",
                            "options": [
                                "Cold",
                                "Necrotic",
                                "Poison"
                            ]
                        }
                    },
                    "choice_effects": {
                        "Cold": [{"type": "grant_damage_resistance", "damage_type": "Cold"}],
                        "Necrotic": [{"type": "grant_damage_resistance", "damage_type": "Necrotic"}],
                        "Poison": [{"type": "grant_damage_resistance", "damage_type": "Poison"}]
                    }
                }
            }
        }
    ],
    "backgrounds": [
        {
            "name": "Haunted One",
            "description": "You are haunted by the events of your past. Whether it was a lone terrible incident or an accumulation of painful moments, you bear the unshakable weight of what happened to you. It cannot be slain with a sword or banished via magic. Nevertheless, you persist.",
            "edition": "2024",
            "status": "active",
            "source": "Ravenloft: The Horrors Within",
            "ability_score_increase": {
                "total": 3,
                "options": [
                    "Constitution",
                    "Wisdom",
                    "Charisma"
                ],
                "suggested": {
                    "Wisdom": 2,
                    "Constitution": 1
                }
            },
            "effects": [
                {
                    "type": "grant_skill_proficiency",
                    "skills": [
                        "Arcana",
                        "Survival"
                    ]
                },
                {
                    "type": "grant_origin_feat",
                    "feat": "Survivor"
                },
                {
                    "type": "grant_tool_proficiency",
                    "tools": [
                        "Gaming Set"
                    ]
                }
            ],
            "starting_equipment": {
                "option_a": {
                    "items": [
                        "Gaming Set",
                        "Crowbar",
                        "Holy Water (flask)",
                        "Mirror",
                        "Oil (2 flasks)",
                        "Signal Whistle",
                        "Tinderbox",
                        "Torches (5)",
                        "Traveler's Clothes",
                        "Waterskin"
                    ],
                    "gold": 14
                },
                "option_b": {
                    "gold": 50
                }
            }
        },
        {
            "name": "Investigator",
            "description": "You relentlessly seek the truth. Perhaps you witnessed something remarkable or terrible and now desire to unravel its mystery, or maybe you are motivated by universal justice and honesty. Whether investigating local crimes or eldritch conspiracies, you are driven to reveal what others keep hidden.",
            "edition": "2024",
            "status": "active",
            "source": "Ravenloft: The Horrors Within",
            "ability_score_increase": {
                "total": 3,
                "options": [
                    "Intelligence",
                    "Wisdom",
                    "Charisma"
                ],
                "suggested": {
                    "Intelligence": 2,
                    "Wisdom": 1
                }
            },
            "effects": [
                {
                    "type": "grant_skill_proficiency",
                    "skills": [
                        "Insight",
                        "Investigation"
                    ]
                },
                {
                    "type": "grant_origin_feat",
                    "feat": "Sharp Eye"
                },
                {
                    "type": "grant_tool_proficiency",
                    "tools": [
                        "Disguise Kit"
                    ]
                }
            ],
            "starting_equipment": {
                "option_a": {
                    "items": [
                        "Disguise Kit",
                        "Manacles",
                        "Shovel",
                        "Traveler's Clothes",
                        "Vial (3)"
                    ],
                    "gold": 16
                },
                "option_b": {
                    "gold": 50
                }
            }
        },
        {
            "name": "Mist Wanderer",
            "description": "You once knew a home. But one day, the Mists rose and drew you into a Domain of Dread. Ever since, you have wandered between domains, braving the mercurial Mists as you search for a way home. You find solace in communities of fellow wanderers throughout the Mists.",
            "edition": "2024",
            "status": "active",
            "source": "Ravenloft: The Horrors Within",
            "ability_score_increase": {
                "total": 3,
                "options": [
                    "Dexterity",
                    "Constitution",
                    "Wisdom"
                ],
                "suggested": {
                    "Constitution": 2,
                    "Wisdom": 1
                }
            },
            "effects": [
                {
                    "type": "grant_skill_proficiency",
                    "skills": [
                        "Stealth",
                        "Survival"
                    ]
                },
                {
                    "type": "grant_origin_feat",
                    "feat": "Mist Walker"
                },
                {
                    "type": "grant_tool_proficiency",
                    "tools": [
                        "Artisan's Tools"
                    ]
                }
            ],
            "starting_equipment": {
                "option_a": {
                    "items": [
                        "Artisan's Tools",
                        "Lamp",
                        "Oil (5 flasks)",
                        "Rope (hempen, 50 ft)",
                        "Tinderbox",
                        "Traveler's Clothes"
                    ],
                    "gold": 30
                },
                "option_b": {
                    "gold": 50
                }
            }
        },
        {
            "name": "Spirit Medium",
            "description": "Through strange rituals and fateful encounters, you have discovered that you bear a unique connection to the spirits of the dead and damned. Your body is a conduit for such spirits, granting prescient insight from beyond at a haunting cost.",
            "edition": "2024",
            "status": "active",
            "source": "Ravenloft: The Horrors Within",
            "ability_score_increase": {
                "total": 3,
                "options": [
                    "Constitution",
                    "Intelligence",
                    "Wisdom"
                ],
                "suggested": {
                    "Wisdom": 2,
                    "Constitution": 1
                }
            },
            "effects": [
                {
                    "type": "grant_skill_proficiency",
                    "skills": [
                        "Insight",
                        "Religion"
                    ]
                },
                {
                    "type": "grant_origin_feat",
                    "feat": "Echoing Soul"
                },
                {
                    "type": "grant_tool_proficiency",
                    "tools": [
                        "Gaming Set"
                    ]
                }
            ],
            "starting_equipment": {
                "option_a": {
                    "items": [
                        "Dagger",
                        "Gaming Set",
                        "Basket",
                        "Bell",
                        "Candle (8)",
                        "Ink (1 ounce)",
                        "Ink Pen",
                        "Paper (5 sheets)",
                        "Tinderbox",
                        "Traveler's Clothes"
                    ],
                    "gold": 32
                },
                "option_b": {
                    "gold": 50
                }
            }
        }
    ],
    "feats": {
        "origin_feats": {
            "Sharp Eye": {
                "description": "You gain the following benefits:",
                "benefits": [
                    "Search and Study Advantage. When you take the Search or Study action, you can give yourself Advantage on any ability check made as part of that action.",
                    "Recover Uses. You can use this feature a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest. If the check fails, the use of this feature is not expended."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within"
            },
            "Survivor": {
                "description": "You gain the following benefits:",
                "benefits": [
                    "Hypervigilance. Whenever you roll Initiative, you can reroll the d20 if the number rolled is 9 or lower. You must use the new roll.",
                    "Steel Yourself. When you fail a saving throw to avoid or end the Charmed or Frightened condition, you can take a Reaction to add a bonus to the roll equal to your Proficiency Bonus, potentially causing it to succeed. Once you take this Reaction, you can't do so again until you finish a Long Rest."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within"
            },
            "Aberrant Anatomy": {
                "description": "Exposure to alien horrors has warped your physical form in supernatural ways. You gain the following benefits:",
                "benefits": [
                    "Breathless. You can hold your breath for 1 hour.",
                    "Extrasensory Perception. You have proficiency in the Perception skill. You also gain Expertise in that skill. In addition, you have Blindsight with a range of 15 feet.",
                    "Warping Flesh. Immediately after you make a D20 Test and roll a 1 on the d20, make a Constitution saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you have the Stunned condition until the end of your next turn."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_darkvision",
                        "range": 15
                    }
                ]
            },
            "Echoing Soul": {
                "description": "You experience echoes from a past or alternate life. You gain the following benefits:",
                "benefits": [
                    "Channelled Prowess. You gain proficiency in two skills of your choice. In addition, choose one skill you have proficiency in; you gain Expertise in that skill. Whenever you finish a Long Rest, you can change this choice of Expertise.",
                    "Inherent Tongues. You know one additional language of your choice, chosen from the Player's Handbook.",
                    "Intrusive Echoes. Immediately after you make a D20 Test and roll a 1 on the d20, make a Constitution saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you have the Incapacitated condition until the end of your next turn, and your Speed is halved while incapacitated in this way."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "choices": [
                    {
                        "type": "select_multiple",
                        "count": 2,
                        "description": "Choose proficiency in two skills.",
                        "name": "skills",
                        "source": {
                            "type": "reference",
                            "target": "skills"
                        }
                    },
                    {
                        "type": "select_single",
                        "count": 1,
                        "description": "Choose one skill you have proficiency in to gain Expertise.",
                        "name": "expertise",
                        "source": {
                            "type": "reference",
                            "target": "skills"
                        }
                    },
                    {
                        "type": "select_single",
                        "count": 1,
                        "description": "Choose one additional language.",
                        "name": "language",
                        "source": {
                            "type": "reference",
                            "target": "languages"
                        }
                    }
                ]
            },
            "Gathered Whispers": {
                "description": "You are haunted by a cacophony of whispering spirits only you can hear. You gain the following benefits:",
                "benefits": [
                    "Spirit Whispers. You learn the Message spell and can cast it without Material components. You always have the Augury spell prepared and can cast it once per Long Rest without a spell slot or components, or using any spell slots you have. Intelligence, Wisdom, or Charisma is your spellcasting ability for these spells.",
                    "Unearthly Scream. When you are hit by an attack roll, you can take a Reaction to add your Proficiency Bonus to your AC against that attack, potentially causing it to miss. You can use this benefit a number of times equal to your Proficiency Bonus, and regain all expended uses when you finish a Long Rest.",
                    "Voices from Beyond. Immediately after you make a D20 Test and roll a 1 on the d20, make a Wisdom saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you have the Deafened condition until the end of your next turn, and have Disadvantage on ability checks and attack rolls while deafened."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_cantrip",
                        "spell": "Message"
                    },
                    {
                        "type": "grant_spell",
                        "spell": "Augury",
                        "level": 2,
                        "free_uses": 1,
                        "recovery": "long_rest"
                    }
                ]
            },
            "Living Shadow": {
                "description": "The shadow you cast is animate and ever-present, sometimes acting according to its own will. You gain the following benefits:",
                "benefits": [
                    "Grasping Shadow. You learn the Mage Hand spell and can cast it without spell components. Intelligence, Wisdom, or Charisma is your spellcasting ability for it.",
                    "Lengthened Strike. When you make a melee attack roll as part of the Attack or Magic action on your turn, you can increase your reach for that attack by 10 feet. You can use this feature a number of times equal to your Proficiency Bonus, and regain all expended uses when you finish a Long Rest.",
                    "Ominous Will. Immediately after you make a D20 Test and roll a 1 on the d20, make a Wisdom saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you have the Incapacitated condition until the start of your next turn, at which point you roll on the Shadow's Will table to determine your action."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_cantrip",
                        "spell": "Mage Hand"
                    }
                ]
            },
            "Mist Walker": {
                "description": "You know how to slip through the Mists' grasp at a dangerous price. You gain the following benefits:",
                "benefits": [
                    "Domain Traveler. When you enter the Mists intent on reaching a specific domain whose name you know, you are treated as possessing a Mist talisman keyed to that domain.",
                    "Mist Walk. When you take damage or fail a saving throw to avoid or end the Grappled or Restrained condition, you can take a Reaction to teleport up to 15 feet to an unoccupied space you can see. You can use this feature a number of times equal to your Proficiency Bonus, and regain all expended uses when you finish a Long Rest.",
                    "Poisoned Roots. When you finish a Long Rest, the area within a 10-mile radius siphons your vitality. Whenever you finish a Short Rest in that area, make a Constitution saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you gain no benefits from finishing that rest."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within"
            },
            "Second Skin": {
                "description": "There is another side of you that most people never see. You gain the following benefits:",
                "benefits": [
                    "Alternate Form. You always have the Alter Self spell prepared. You can cast it once per Long Rest without a spell slot, components, or Concentration. You can also cast it using any spell slots you have. Intelligence, Wisdom, or Charisma is your spellcasting ability for it.",
                    "Involuntary Change. When you select this feat, choose a change catalyst. When you encounter that catalyst, at the start of your next turn, make a Charisma saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you immediately cast Alter Self without a spell slot via Alternate Form (or are Stunned until the start of your next turn if already expended)."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_spell",
                        "spell": "Alter Self",
                        "level": 2,
                        "free_uses": 1,
                        "recovery": "long_rest"
                    }
                ]
            },
            "Symbiotic Being": {
                "description": "A second being resides within your body, offering knowledge while furthering its own agenda. You gain the following benefits:",
                "benefits": [
                    "Second Mind. You gain proficiency in one skill of your choice from Arcana, Deception, History, Insight, Intimidation, Investigation, Nature, Perception, Persuasion, or Religion. You also learn one additional language of your choice.",
                    "Sustained Symbiosis. When you fail a saving throw, you can take a Reaction and expend one of your Hit Dice. Roll the die and add the number rolled to the saving throw, potentially turning the failure into a success. You can use this feature a number of times equal to your Proficiency Bonus, and regain all expended uses when you finish a Long Rest.",
                    "Symbiotic Agenda. Immediately after you make a D20 Test and roll a 1 on the d20, make a Charisma saving throw (DC 13 plus your Proficiency Bonus). On a failed save, you have the Charmed condition for 1d12 hours and must follow the symbiote's commands (repeating the save whenever you take damage)."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within"
            },
            "Touch of Death": {
                "description": "Deathly power resides within you, bursting out at the slightest provocation. You gain the following benefits:",
                "benefits": [
                    "Death Touch. You learn the Chill Touch cantrip and can cast it without spell components. Necrotic damage you deal with this spell ignores Resistance. Intelligence, Wisdom, or Charisma is your spellcasting ability for this spell.",
                    "Pull of the Grave. You have Disadvantage on Death Saving Throws."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_cantrip",
                        "spell": "Chill Touch"
                    }
                ]
            },
            "Watchers": {
                "description": "Something unnatural is always watching you, taking the form of scurrying vermin and eerie watchers. You gain the following benefits:",
                "benefits": [
                    "Borrowed Eyes. You always have Beast Sense and Speak with Animals prepared. You can cast each once per Long Rest without a spell slot, and can also cast them using any spell slots you have. Intelligence, Wisdom, or Charisma is your spellcasting ability for them.",
                    "Heightened Suspicion. Whenever you take the Search action, you can roll 1d4 and add the number rolled to any ability check made as part of that action.",
                    "Incessant Watchers. You have Disadvantage on saving throws made against the Scrying spell. In addition, immediately after you make a D20 Test and roll a 1 on the d20, make a Wisdom saving throw (DC 13 plus your Proficiency Bonus) or have Disadvantage on D20 Tests for 1 minute (save repeats at the end of each turn)."
                ],
                "category": "Origin",
                "prerequisite": "None",
                "source": "Ravenloft: The Horrors Within",
                "effects": [
                    {
                        "type": "grant_spell",
                        "spell": "Beast Sense",
                        "level": 2,
                        "free_uses": 1,
                        "recovery": "long_rest"
                    },
                    {
                        "type": "grant_spell",
                        "spell": "Speak with Animals",
                        "level": 1,
                        "free_uses": 1,
                        "recovery": "long_rest"
                    }
                ]
            }
        }
    }
}

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(package, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {OUTPUT_PATH}")
