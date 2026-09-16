"""Routes package for the D&D Character Creator.

After Phase 1 cleanup, this package only manages the REST API v1 blueprint.
Legacy Jinja routes have been removed.
"""

from flask import Flask


def register_routes(app: Flask):
    """
    Register API blueprints with the Flask app.

    After Phase 1 cleanup, only the REST API v1 blueprint is registered.
    The React SPA uses this API exclusively via stateless JSON endpoints.

    Args:
        app: The Flask application instance
    """
    from routes.api import api_v1_bp

    app.register_blueprint(api_v1_bp)
