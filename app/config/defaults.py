"""Default configuration schema for stocksViewer application."""

from __future__ import annotations

DEFAULT_CONFIG: dict[str, object] = {
    "data": {
        "provider": "alphavantage",
    },
    "alphavantage": {
        "api_key": "",
        "default_range": "1M",
        "default_interval": "daily",
        "auto_refresh_sec": 60,
    },
    "finnhub": {
        "api_key": "",
    },
    "cache": {
        "history_ttl_days": 365,
        "quote_ttl_sec": 60,
        "indicator_ttl_sec": 300,
    },
    "ai": {
        "deepseek": {
            "enabled": False,
            "api_key": "",
            "endpoint": "",
            "model": "",
        },
        "qwen": {
            "enabled": False,
            "api_key": "",
            "endpoint": "",
            "model": "",
        },
        "insight_prompt": "",
    },
    "ui": {
        "theme": "light",
        "show_ai_panel": False,
    },
}


def get_default_config() -> dict[str, object]:
    """Return a deep copy of the default configuration schema."""
    from copy import deepcopy

    return deepcopy(DEFAULT_CONFIG)

