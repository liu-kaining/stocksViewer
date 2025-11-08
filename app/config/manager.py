"""Configuration management utilities."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from copy import deepcopy
from typing import Any
import sqlite3

from app.db import models
from app.config.defaults import get_default_config


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overrides.items():
        if (
            key in result
            and isinstance(result[key], MutableMapping)
            and isinstance(value, MutableMapping)
        ):
            result[key] = _deep_merge(result[key], value)  # type: ignore[assignment]
        else:
            result[key] = value
    return result


class ConfigManager:
    """Load and persist configuration using SQLite storage."""

    def __init__(self) -> None:
        self._config = get_default_config()
        self.refresh()

    @property
    def data(self) -> dict[str, Any]:
        return deepcopy(self._config)

    def refresh(self) -> None:
        try:
            stored = models.fetch_all_configs()
        except sqlite3.OperationalError:
            # Tables may not be initialized yet; keep defaults until schema is ready.
            return
        merged = get_default_config()
        for key, raw_value in stored.items():
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                continue
            if key in merged and isinstance(merged[key], MutableMapping):
                merged[key] = _deep_merge(merged[key], parsed)  # type: ignore[assignment]
            else:
                merged[key] = parsed
        self._config = merged

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged = _deep_merge(self._config, payload)
        previous_provider = self._config.get("data", {}).get("provider")
        new_provider = merged.get("data", {}).get("provider")
        for key, value in merged.items():
            if isinstance(value, (dict, list)):
                models.upsert_config(key, json.dumps(value))
        if previous_provider and new_provider and previous_provider != new_provider:
            from app.services import cache

            cache.clear_all()
        self._config = merged
        return self.data


config_manager = ConfigManager()

