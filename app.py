"""
D&D 2024 Character Creator - Main Application
Flask web application for creating D&D 2024 characters.

All routes are organized into blueprint modules in the routes/ directory.
"""

from flask import Flask, session
import logging
import os
import secrets
from typing import Dict, Any, Optional
from routes import register_routes

from modules.data_loader import DataLoader
from modules.character_builder import CharacterBuilder

# ==================== Logging Configuration ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("character_creator.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ==================== Flask App Initialization ====================


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _environment_name() -> str:
    return os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or "development"


def _is_production() -> bool:
    return _environment_name().strip().lower() in {"production", "prod"}


def _is_development() -> bool:
    return _environment_name().strip().lower() in {"development", "dev", "local"}


def _secret_key_from_environment() -> str:
    secret_key = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
    if secret_key:
        return secret_key

    if _is_production():
        raise RuntimeError("SECRET_KEY or FLASK_SECRET_KEY must be set in production")
    else:
        logger.warning("Using an ephemeral Flask secret key; set SECRET_KEY for persistent sessions")
    return secrets.token_urlsafe(32)


def _debug_enabled() -> bool:
    return _is_development() and _is_truthy(os.environ.get("FLASK_DEBUG"))


def _run_config() -> Dict[str, Any]:
    return {
        "debug": _debug_enabled(),
        "host": os.environ.get("HOST", "127.0.0.1"),
        "port": int(os.environ.get("PORT", "5000")),
    }


app = Flask(__name__)
app.secret_key = _secret_key_from_environment()
app.config["DEBUG"] = _debug_enabled()


# Enable CORS for the Vite dev server when running in development. In
# production, CORS is not needed.
if _is_development():
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173"]}})
    except ImportError:
        # flask-cors is optional; only required when running the SPA dev server.
        pass

# Initialize data loaders (available to all blueprints)
app.data_loader = DataLoader()

# ==================== Logging Helper Functions ====================


def log_route_processing(
    route_name: str,
    choices_made: Dict[str, Any],
    builder_before: Optional[CharacterBuilder],
    builder_after: Optional[CharacterBuilder],
):
    """Log route processing with choices made and builder changes."""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Route: {route_name}")
    logger.info(f"{'=' * 80}")

    # Log choices made in this route
    if choices_made:
        logger.info("Choices made:")
        for key, value in choices_made.items():
            if isinstance(value, list):
                logger.info(f"  {key}: [{', '.join(str(v) for v in value)}]")
            else:
                logger.info(f"  {key}: {value}")
    else:
        logger.info("No choices made in this route")

    # Log builder state changes
    if builder_before and builder_after:
        log_builder_changes(builder_before, builder_after)
    elif builder_after:
        logger.info("\nBuilder created (new session)")
        log_builder_state(builder_after)

    logger.info(f"{'=' * 80}\n")


def log_builder_changes(before: CharacterBuilder, after: CharacterBuilder):
    """Log changes between two builder states."""
    before_data = before.to_json()
    after_data = after.to_json()

    changes = []

    # Check for changes in main fields
    for key in [
        "name",
        "class",
        "subclass",
        "species",
        "lineage",
        "background",
        "level",
        "step",
    ]:
        before_val = before_data.get(key)
        after_val = after_data.get(key)
        if before_val != after_val:
            changes.append(f"  {key}: {before_val} → {after_val}")

    # Check ability scores
    before_abilities = before_data.get("ability_scores", {})
    after_abilities = after_data.get("ability_scores", {})
    if before_abilities != after_abilities:
        changes.append(f"  ability_scores: {before_abilities} → {after_abilities}")

    # Check proficiencies
    before_skills = set(before_data.get("skill_proficiencies", []))
    after_skills = set(after_data.get("skill_proficiencies", []))
    new_skills = after_skills - before_skills
    if new_skills:
        changes.append(f"  +skill_proficiencies: {list(new_skills)}")

    # Check effects
    before_effects_count = len(before_data.get("effects", []))
    after_effects_count = len(after_data.get("effects", []))
    if before_effects_count != after_effects_count:
        new_effects = after_effects_count - before_effects_count
        changes.append(
            f"  effects: {before_effects_count} → {after_effects_count} (+{new_effects})"
        )
        # Log new effects
        if new_effects > 0:
            recent_effects = after_data.get("effects", [])[-new_effects:]
            for effect in recent_effects:
                effect_type = effect.get("type", "unknown")
                effect_source = effect.get("source", "unknown")
                changes.append(f"    - {effect_type} from {effect_source}")

    # Check spells
    before_prepared = set(before_data.get("spells", {}).get("prepared", []))
    after_prepared = set(after_data.get("spells", {}).get("prepared", []))
    new_prepared = after_prepared - before_prepared
    if new_prepared:
        changes.append(f"  +spells.prepared: {list(new_prepared)}")

    # Check languages
    before_langs = set(before_data.get("languages", []))
    after_langs = set(after_data.get("languages", []))
    new_langs = after_langs - before_langs
    if new_langs:
        changes.append(f"  +languages: {list(new_langs)}")

    # Check choices_made
    before_choices = before_data.get("choices_made", {})
    after_choices = after_data.get("choices_made", {})
    for key in after_choices:
        if key not in before_choices or before_choices[key] != after_choices[key]:
            changes.append(f"  choices_made.{key}: {after_choices[key]}")

    if changes:
        logger.info("\nBuilder changes:")
        for change in changes:
            logger.info(change)
    else:
        logger.info("\nNo builder changes detected")


def log_builder_state(builder: CharacterBuilder):
    """Log current builder state summary."""
    data = builder.to_json()
    logger.info("Current builder state:")
    logger.info(f"  Name: {data.get('name', 'N/A')}")
    logger.info(f"  Class: {data.get('class', 'N/A')} (Level {data.get('level', 1)})")
    logger.info(f"  Subclass: {data.get('subclass', 'N/A')}")
    logger.info(f"  Species: {data.get('species', 'N/A')}")
    logger.info(f"  Lineage: {data.get('lineage', 'N/A')}")
    logger.info(f"  Background: {data.get('background', 'N/A')}")
    logger.info(f"  Step: {data.get('step', 'N/A')}")
    logger.info(f"  Effects: {len(data.get('effects', []))}")
    logger.info(f"  Skill Proficiencies: {len(data.get('skill_proficiencies', []))}")
    logger.info(f"  Languages: {len(data.get('languages', []))}")


# Make logging helpers available to blueprints
app.log_route_processing = log_route_processing
app.log_builder_changes = log_builder_changes
app.log_builder_state = log_builder_state























# ==================== Route Registration ====================

try:
    register_routes(app)
    logger.info("API routes registered successfully")
except Exception as e:
    logger.error(f"Error registering routes: {e}")
    raise

# ==================== React SPA serving (Phase 7) ====================
#
# In production, the React SPA's built bundle (`frontend/dist/`) is
# served from the Flask root. Any path not claimed by a blueprint
 # (`/api/v1/*`, `/static/*`) falls through
# to `index.html` so client-side routing handles it.
#
# In development, you typically run `npm run dev` (Vite on :5173) and
# Flask serves only the API; this catch-all just returns a friendly
# message until you've run `npm run build`.

from pathlib import Path
from flask import send_from_directory, jsonify

_SPA_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    """Serve the built React SPA, or a friendly placeholder."""
    if not _SPA_DIR.exists() or not (_SPA_DIR / "index.html").exists():
        return jsonify({
            "error": "React SPA bundle not built.",
            "hint": "Run `npm run build` in frontend/, or use the Vite dev "
                    "server at http://localhost:5173 during development.",
            "api": "/api/v1/health",
        }), 503

    # Serve a real asset if it exists (e.g. /assets/index-abc.js).
    if path:
        candidate = _SPA_DIR / path
        if candidate.is_file():
            return send_from_directory(_SPA_DIR, path)

    # Otherwise serve index.html so client-side routing takes over.
    return send_from_directory(_SPA_DIR, "index.html")


# ==================== Application Entry Point ====================

if __name__ == "__main__":
    app.run(**_run_config())
