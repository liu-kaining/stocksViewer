"""API endpoints for stocksViewer."""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request

from app.services import cache, ai
from app.services.alphavantage import AlphaVantageError, client

api_bp = Blueprint("api", __name__)


def _make_response(data: Any = None, *, success: bool = True, status: int = 200, error: Dict[str, Any] | None = None):
    payload: Dict[str, Any] = {"success": success}
    if success:
        payload["data"] = data
    else:
        payload["error"] = error or {"message": "Unknown error"}
    return jsonify(payload), status


@api_bp.get("/quote")
def get_quote():
    symbol = request.args.get("symbol", "").upper()
    if not symbol:
        return _make_response(success=False, status=400, error={"code": "INVALID_SYMBOL", "message": "Symbol is required"})
    try:
        result = cache.get_quote(symbol)
    except AlphaVantageError as exc:
        return _make_response(success=False, status=429, error={"code": "ALPHAVANTAGE_ERROR", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _make_response(success=False, status=500, error={"code": "SERVER_ERROR", "message": str(exc)})
    return _make_response(result)


@api_bp.get("/history")
def get_history():
    symbol = request.args.get("symbol", "").upper()
    interval = request.args.get("interval", "daily")
    range_key = request.args.get("range", "1M")
    adjusted = request.args.get("adjusted", "true").lower() == "true"
    if not symbol:
        return _make_response(success=False, status=400, error={"code": "INVALID_SYMBOL", "message": "Symbol is required"})
    try:
        result = cache.get_historical(symbol, interval, range_key, adjusted)
    except AlphaVantageError as exc:
        return _make_response(success=False, status=429, error={"code": "ALPHAVANTAGE_ERROR", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _make_response(success=False, status=500, error={"code": "SERVER_ERROR", "message": str(exc)})
    return _make_response(result)


@api_bp.get("/indicator")
def get_indicator():
    symbol = request.args.get("symbol", "").upper()
    indicator = request.args.get("indicator", "").upper()
    interval = request.args.get("interval", "daily")
    params = {k: v for k, v in request.args.items() if k not in {"symbol", "indicator", "interval"}}
    if not symbol or not indicator:
        return _make_response(
            success=False,
            status=400,
            error={"code": "INVALID_PARAMETERS", "message": "Symbol and indicator are required"},
        )
    try:
        result = cache.get_indicator(symbol, indicator, interval, params)
    except AlphaVantageError as exc:
        return _make_response(success=False, status=429, error={"code": "ALPHAVANTAGE_ERROR", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _make_response(success=False, status=500, error={"code": "SERVER_ERROR", "message": str(exc)})
    return _make_response(result)


@api_bp.get("/settings")
def get_settings():
    config = current_app.config["STOCKS_VIEWER_CONFIG"].data
    return _make_response(config)


@api_bp.post("/settings")
def update_settings():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return _make_response(success=False, status=400, error={"code": "INVALID_PAYLOAD", "message": "JSON body must be a dictionary"})
    manager = current_app.config["STOCKS_VIEWER_CONFIG"]
    updated = manager.update(payload)
    return _make_response(updated)


@api_bp.post("/settings/test")
def test_settings():
    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider")
    if provider not in {"alphavantage", "finnhub", "deepseek", "qwen"}:
        return _make_response(
            success=False,
            status=400,
            error={"code": "INVALID_PROVIDER", "message": "Provider must be alphavantage, deepseek, or qwen"},
        )
    config = current_app.config["STOCKS_VIEWER_CONFIG"].data
    if provider in {"deepseek", "qwen"}:
        provider_config = config.get("ai", {}).get(provider, {})
    elif provider == "finnhub":
        provider_config = config.get("finnhub", {})
    else:
        provider_config = config.get("alphavantage", {})
    if provider == "alphavantage":
        try:
            client.fetch_quote("IBM")
            result = {"success": True, "message": "Alpha Vantage 请求成功"}
        except AlphaVantageError as exc:
            result = {"success": False, "message": str(exc)}
        except Exception as exc:  # noqa: BLE001
            result = {"success": False, "message": str(exc)}
    elif provider == "finnhub":
        try:
            from app.services.finnhub import client as finnhub_client, FinnhubError

            finnhub_client.fetch_quote("AAPL")
            result = {"success": True, "message": "Finnhub 请求成功"}
        except FinnhubError as exc:
            result = {"success": False, "message": str(exc)}
        except Exception as exc:  # noqa: BLE001
            result = {"success": False, "message": str(exc)}
    else:
        result = ai.test_provider(provider, provider_config)
    return _make_response(result)


@api_bp.post("/cache/clear_history")
def clear_history():
    cache.clear_historical()
    return _make_response({"status": "cleared"})

