"""AI provider integration stubs for DeepSeek and Qwen."""

from __future__ import annotations

from typing import Any, Dict


def test_provider(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": False, "message": f"{provider} testing not implemented"}


def generate_insight(symbol: str, context: Dict[str, Any]) -> Dict[str, Any]:
    return {"enabled": False, "message": "AI insight generation not yet implemented"}

