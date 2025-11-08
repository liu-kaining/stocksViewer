"""Cache management for quotes, historical and indicator data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.config.manager import config_manager
from app.db import models
from app.services.alphavantage import AlphaVantageError, client as av_client
from app.services.finnhub import FinnhubError, client as fh_client


def _now_utc() -> datetime:
    return datetime.utcnow()


def get_quote(symbol: str) -> Dict[str, Any]:
    provider = _current_provider()
    ttl_seconds = config_manager.data.get("cache", {}).get("quote_ttl_sec", 60)
    cached = models.get_recent_quote(symbol)
    if (
        cached
        and cached.get("provider") == provider
        and _is_cache_valid(cached.get("fetched_at"), ttl_seconds)
    ):
        return {
            **cached,
            "source": "cache",
        }

    quote, overview = _fetch_quote_and_overview(symbol, provider)
    response = {
        "symbol": symbol,
        "price": _try_float(quote.get("price")),
        "change": _try_float(quote.get("change")),
        "change_percent": quote.get("change_percent"),
        "volume": quote.get("volume"),
        "timestamp": quote.get("latest_trading_day"),
        "company_overview": {
            "name": overview.get("name"),
            "description": overview.get("description"),
            "industry": overview.get("industry"),
            "market_cap": overview.get("market_cap"),
            "pe_ratio": overview.get("pe_ratio"),
            "website": overview.get("website"),
        },
        "fetched_at": _now_utc().isoformat(),
        "provider": provider,
    }
    models.upsert_recent_quote(symbol, response)
    return {
        **response,
        "source": "live",
    }


def get_historical(symbol: str, interval: str, range_key: str, adjusted: bool) -> Dict[str, Any]:
    provider = _current_provider()
    cached = models.get_historical_entry(symbol, interval, range_key, adjusted)
    if cached and cached.get("provider") == provider:
        return {
            **cached,
            "source": "cache",
        }

    outputsize = "compact" if range_key in {"1D", "1W", "1M", "3M"} else "full"
    notice = None
    used_adjusted = adjusted
    series_payload: Dict[str, Any]
    if provider == "alphavantage":
        try:
            series_payload = av_client.fetch_time_series(symbol, interval, outputsize, adjusted, range_key)
        except AlphaVantageError as exc:
            message = str(exc).lower()
            if (
                adjusted
                and interval.startswith("intraday")
                and "premium" in message
            ):
                series_payload = av_client.fetch_time_series(symbol, interval, outputsize, False, range_key)
                used_adjusted = False
                notice = "当前账号不支持复权分时数据，已改用未复权数据。"
            else:
                raise
    else:
        try:
            series_payload = fh_client.fetch_time_series(symbol, interval, outputsize, False, range_key)
        except FinnhubError as exc:
            raise AlphaVantageError(str(exc)) from exc
        used_adjusted = False

    filtered_series = _slice_series(series_payload["series"], range_key)
    as_of_date = filtered_series[-1]["timestamp"] if filtered_series else None
    record = {
        "symbol": symbol,
        "interval": interval,
        "range": range_key,
        "adjusted": used_adjusted,
        "series": filtered_series,
        "as_of_date": as_of_date,
        "fetched_at": _now_utc().isoformat(),
        "provider": provider,
    }
    models.upsert_historical_entry(symbol, interval, range_key, used_adjusted, as_of_date or "", record)
    if notice:
        record["notice"] = notice
    return {
        **record,
        "source": "live",
    }


def clear_historical() -> None:
    models.delete_historical_data()


def get_indicator(symbol: str, indicator: str, interval: str, params: Dict[str, Any]) -> Dict[str, Any]:
    provider = _current_provider()
    cached = models.get_indicator_entry(symbol, indicator, interval, params)
    if cached and cached.get("provider") == provider:
        return {
            **cached,
            "source": "cache",
        }
    if provider == "alphavantage":
        payload = av_client.fetch_indicator(symbol, indicator, interval, params)
    else:
        try:
            payload = fh_client.fetch_indicator(symbol, indicator, interval, params)
        except FinnhubError as exc:
            raise AlphaVantageError(str(exc)) from exc
    series = payload.get("series", [])
    as_of_date = series[-1]["timestamp"] if series else None
    record = {
        "symbol": symbol,
        "indicator": indicator,
        "interval": interval,
        "params": params,
        "series": series,
        "as_of_date": as_of_date,
        "fetched_at": _now_utc().isoformat(),
        "provider": provider,
    }
    models.upsert_indicator_entry(symbol, indicator, interval, params, as_of_date or "", record)
    return {
        **record,
        "source": "live",
    }


def clear_all() -> None:
    models.delete_recent_quotes()
    models.delete_historical_data()
    models.delete_indicator_data()


# ---------------------------------------------------------------------------
# helpers


def _current_provider() -> str:
    return config_manager.data.get("data", {}).get("provider", "alphavantage")


def _fetch_quote_and_overview(symbol: str, provider: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if provider == "alphavantage":
        return av_client.fetch_quote(symbol), av_client.fetch_overview(symbol)
    try:
        quote = fh_client.fetch_quote(symbol)
        overview = fh_client.fetch_overview(symbol)
        return quote, overview
    except FinnhubError as exc:
        raise AlphaVantageError(str(exc)) from exc


def _is_cache_valid(fetched_at: str | None, ttl_seconds: int) -> bool:
    if not fetched_at:
        return False
    try:
        fetched_time = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    return fetched_time + timedelta(seconds=ttl_seconds) > _now_utc()


def _slice_series(series: List[Dict[str, Any]], range_key: str) -> List[Dict[str, Any]]:
    if not series:
        return []
    # Alpha Vantage 返回按时间倒序，因此转换为按时间升序更便于前端绘图
    ordered = list(reversed(series))
    if range_key == "1D":
        return ordered[-1:]
    lookups = {
        "1W": 5,
        "1M": 22,
        "3M": 66,
        "1Y": 252,
    }
    if range_key in lookups:
        return ordered[-lookups[range_key] :]
    return ordered


def _try_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

