"""
Supplements API Blueprint

Provides endpoints to list, inspect, validate, install, and remove modular
supplements (both 1st-party and 3rd-party).
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, abort
from modules.supplement_manager import get_supplement_manager

supplements_bp = Blueprint("supplements", __name__, url_prefix="/supplements")


@supplements_bp.get("")
def list_supplements():
    """List all available modules and supplements."""
    mgr = get_supplement_manager()
    mgr.reload_all()
    return jsonify({
        "supplements": mgr.list_supplements()
    })


@supplements_bp.post("/validate")
def validate_supplement():
    """Validate a supplement JSON package without installing it."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Payload must be a valid JSON object.")

    mgr = get_supplement_manager()
    valid, errors = mgr.validate_package(data)
    manifest = data.get("manifest", {})

    feats_data = data.get("feats", {})
    feats_count = len(feats_data.get("origin_feats", {})) + len(feats_data.get("general_feats", {}))
    counts = {
        "classes": len(data.get("classes", [])),
        "subclasses": len(data.get("subclasses", [])),
        "species": len(data.get("species", [])),
        "species_variants": len(data.get("species_variants", [])),
        "backgrounds": len(data.get("backgrounds", [])),
        "spells": len(data.get("spells", [])),
        "feats": feats_count,
    }

    return jsonify({
        "valid": valid,
        "errors": errors,
        "manifest": manifest,
        "counts": counts,
    })


@supplements_bp.post("/install")
def install_supplement():
    """Install a new supplement package into the supplements directory."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Payload must be a valid JSON object.")

    mgr = get_supplement_manager()
    success, message, manifest = mgr.install_supplement(data)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({
        "success": True,
        "message": message,
        "manifest": manifest,
    })


@supplements_bp.delete("/<supplement_id>")
def delete_supplement(supplement_id: str):
    """Uninstall and remove a 3rd party supplement."""
    mgr = get_supplement_manager()
    success, message = mgr.uninstall_supplement(supplement_id)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    return jsonify({
        "success": True,
        "message": message,
    })
