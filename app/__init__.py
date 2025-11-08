"""Flask application factory for stocksViewer."""

from __future__ import annotations

from flask import Flask

from app.config.manager import config_manager
from app.db import models


def create_app() -> Flask:
    """Application factory."""
    models.initialize_schema()
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Inject configuration manager into app context
    config_manager.refresh()
    app.config["STOCKS_VIEWER_CONFIG"] = config_manager

    from app.routes.views import views_bp
    from app.routes.api import api_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

