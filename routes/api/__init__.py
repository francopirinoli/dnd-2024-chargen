"""REST API v1 for the D&D Character Creator React frontend.

This package exposes a stateless JSON API (no Flask session usage) that
serves three concerns:

* `catalog` — read-only access to game data (classes, species, etc.).
* `character` — stateless character build/preview using `CharacterBuilder`.
* `wizard` — declarative metadata about wizard steps and choice cascades
  used by the React frontend to render the creation flow generically.
"""

from flask import Blueprint

from .catalog import catalog_bp
from .character import character_bp
from .wizard import wizard_bp
from .supplements import supplements_bp

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1_bp.register_blueprint(catalog_bp)
api_v1_bp.register_blueprint(character_bp)
api_v1_bp.register_blueprint(wizard_bp)
api_v1_bp.register_blueprint(supplements_bp)


@api_v1_bp.get("/health")
def health():
    from flask import jsonify
    return jsonify({"status": "ok", "version": "v1"})


__all__ = ["api_v1_bp"]
