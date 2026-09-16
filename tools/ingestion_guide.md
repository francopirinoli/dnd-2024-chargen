# D&D 2024 Rulebook Supplement Ingestion Guide

This guide outlines how to extract content from 1st-party or 3rd-party D&D supplements (PDFs, physical books, or text) and convert them into modular, schema-compliant JSON packages ready for the D&D 2024 Character Builder.

---

## 1. Overview of the Ingestion Pipeline

```
Rulebook (PDF / Text)
       │
       ▼
[Step 1: Section Extraction]  (PyMuPDF / pdftotext / Copy Text)
       │
       ▼
[Step 2: LLM Structuring]     (Prompt LLM with JSON Schema & Examples)
       │
       ▼
[Step 3: Schema Validation]   (python tools/validate_supplement.py <file.json>)
       │
       ▼
[Step 4: Package & Install]   (Upload in UI or drop into supplements/ folder)
```

---

## 2. Supplement Package Structure

Every supplement package is a single JSON document (or folder) conforming to `models/supplement_schema.json`:

```json
{
  "manifest": {
    "id": "my-supplement-slug",
    "title": "My Supplement Name",
    "publisher": "Author or Publisher",
    "version": "1.0.0",
    "compatibility": "2024",
    "description": "Brief description of the content.",
    "dependencies": ["core-phb-2024"]
  },
  "subclasses": [ ... ],
  "species": [ ... ],
  "backgrounds": [ ... ],
  "spells": [ ... ],
  "feats": {
    "origin_feats": { ... },
    "general_feats": { ... }
  },
  "spell_class_lists": {
    "cleric": {
      "spells_by_level": {
        "1": ["My New Spell"]
      }
    }
  }
}
```

See [tools/sample_supplement.json](sample_supplement.json) for a complete working example.

---

## 3. Step-by-Step Ingestion Workflow

### Step 1: Text Extraction
Extract the raw text of the subclasses, species, spells, or backgrounds from your PDF or digital source.
Tip: Extract section by section (e.g. one subclass at a time) to ensure the highest accuracy.

### Step 2: Prompting an LLM for Structured Conversion
Feed the raw text into an LLM (Gemini, Claude, GPT) using the following prompt template:

#### Prompt Template for Subclasses:
> "You are an expert D&D 2024 data converter. Convert the following subclass text into a JSON object matching this schema:
> - `name`: string (e.g. 'Beer Domain')
> - `class`: string (one of: Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard)
> - `source`: string (e.g. 'Tome of Heroes')
> - `description`: string (short summary)
> - `features_by_level`: object where keys are level strings ('3', '6', '10', '14') and values are OBJECTS mapping feature name to concise mechanics description (NEVER arrays).
> Text:
> [PASTE SUBCLASS TEXT HERE]"

#### Prompt Template for Species:
> "Convert this species text into a D&D 2024 species JSON:
> - `name`: string
> - `source`: string
> - `description`: string
> - `creature_type`: string (e.g. 'Humanoid')
> - `size`: string ('Small', 'Medium', or 'Small or Medium')
> - `speed`: integer (e.g. 30)
> - `languages`: array of strings (e.g. ['Common'])
> - `traits`: object mapping trait name to description string
> Note: 2024 species do NOT include ability score bonuses (those belong to backgrounds).
> Text:
> [PASTE SPECIES TEXT HERE]"

#### Prompt Template for Spells:
> "Convert this spell text into a D&D 2024 spell JSON:
> - `name`: string
> - `source`: string
> - `level`: integer (0 for cantrip, 1-9 for leveled spells)
> - `school`: string ('Abjuration', 'Conjuration', 'Divination', 'Enchantment', 'Evocation', 'Illusion', 'Necromancy', 'Transmutation')
> - `casting_time`: string
> - `range`: string
> - `components`: array of strings, e.g. ['V', 'S', 'M (a small crystal)']
> - `duration`: string
> - `ritual`: boolean
> - `classes`: array of class names that have this spell on their list
> - `description`: string
> Text:
> [PASTE SPELL TEXT HERE]"

### Step 3: Run the CLI Validator
Assemble the JSON into your supplement file (e.g., `my_supplement.json`) and run:
```bash
python tools/validate_supplement.py my_supplement.json
```
The validator will check your file against all D&D 2024 schema requirements and print any missing or malformed fields.

### Step 4: Loading Into the Character Creator
Once validated, you can load your supplement into the application in two ways:
1. **Directly via the Web UI**: Click "Sources & Supplements" on the homepage or wizard, click "Import Supplement (.json)", and select your file.
2. **Server-Side Drop-in**: Copy the `.json` file into the `supplements/` folder in the project root. The server will detect and index it on the next request.
