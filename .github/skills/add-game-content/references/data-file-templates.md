# Data File Templates

## Class Template

```json
{
  "name": "",
  "description": "",
  "hit_die": 8,
  "primary_ability": "",
  "saving_throw_proficiencies": ["", ""],
  "subclass_selection_level": 3,
  "armor_proficiencies": [],
  "weapon_proficiencies": [],
  "proficiency_bonus_by_level": {
    "1": 2, "2": 2, "3": 2, "4": 2,
    "5": 3, "6": 3, "7": 3, "8": 3,
    "9": 4, "10": 4, "11": 4, "12": 4,
    "13": 5, "14": 5, "15": 5, "16": 5,
    "17": 6, "18": 6, "19": 6, "20": 6
  },
  "features_by_level": {
    "1": {}
  }
}
```

## Subclass Template

```json
{
  "name": "",
  "class": "",
  "description": "",
  "source": "Player's Handbook 2024",
  "features_by_level": {
    "3": {}
  }
}
```

## Species Template

```json
{
  "name": "",
  "creature_type": "Humanoid",
  "size": "Medium",
  "speed": 30,
  "traits": {},
  "languages": ["Common"]
}
```

## Background Template

```json
{
  "name": "",
  "ability_score_increase": {
    "total": 3,
    "options": [],
    "suggested": {}
  },
  "feat": "",
  "skill_proficiencies": [],
  "starting_equipment": {}
}
```

## Spell Definition Template

```json
{
  "name": "",
  "level": 0,
  "school": "",
  "casting_time": "1 action",
  "range": "",
  "components": "V, S",
  "duration": "Instantaneous",
  "description": "",
  "classes": [],
  "source": "Player's Handbook 2024"
}
```

## Feat Template

```json
{
  "name": "",
  "category": "General",
  "prerequisite": null,
  "description": "",
  "effects": []
}
```
