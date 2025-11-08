"""View routes for HTML pages."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def home() -> str:
    config = current_app.config["STOCKS_VIEWER_CONFIG"].data
    return render_template("index.html", config=config)


@views_bp.route("/settings")
def settings() -> str:
    config = current_app.config["STOCKS_VIEWER_CONFIG"].data
    return render_template("settings.html", config=config)

