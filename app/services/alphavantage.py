"""Alpha Vantage API client abstraction."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict

import requests

from app.config.manager import config_manager

API_BASE_URL = "https://www.alphavantage.co/query"
RATE_LIMIT_PER_MINUTE = 5


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage returns an error or throttling notice."""


class AlphaVantageClient:
    """Encapsulate Alpha Vantage API access and rate limiting."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._call_times: deque[float] = deque(maxlen=RATE_LIMIT_PER_MINUTE)

    # ------------------------------------------------------------------
    # public request helpers

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        data = self._request({"function": "GLOBAL_QUOTE", "symbol": symbol})
        quote = data.get("Global Quote") or {}
        if not quote:
            raise AlphaVantageError("未获取到有效的行情数据")
        return {
            "symbol": quote.get("01. symbol"),
            "price": quote.get("05. price"),
            "change": quote.get("09. change"),
            "change_percent": quote.get("10. change percent"),
            "volume": quote.get("06. volume"),
            "latest_trading_day": quote.get("07. latest trading day"),
        }

    def fetch_overview(self, symbol: str) -> Dict[str, Any]:
        data = self._request({"function": "OVERVIEW", "symbol": symbol})
        if not data:
            raise AlphaVantageError("未获取到公司概览数据")
        return {
            "symbol": data.get("Symbol"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "industry": data.get("Industry"),
            "market_cap": data.get("MarketCapitalization"),
            "pe_ratio": data.get("PERatio"),
            "website": data.get("Website"),
        }

    def fetch_time_series(
        self,
        symbol: str,
        interval: str,
        outputsize: str = "compact",
        adjusted: bool = True,
        range_key: str | None = None,
    ) -> Dict[str, Any]:
        params = self._time_series_params(interval, adjusted)
        params.update({"symbol": symbol, "outputsize": outputsize})
        payload = self._request(params)
        time_series = self._extract_time_series(payload)
        as_of = next(iter(time_series.keys()), None)
        return {
            "symbol": symbol,
            "interval": interval,
            "range": range_key,
            "adjusted": adjusted,
            "as_of": as_of,
            "series": [self._format_bar(timestamp, values) for timestamp, values in time_series.items()],
        }

    def fetch_indicator(
        self,
        symbol: str,
        indicator: str,
        interval: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        av_params = {
            "function": indicator.upper(),
            "symbol": symbol,
            "interval": interval,
            "datatype": "json",
        }
        av_params.update(params)
        payload = self._request(av_params)
        series_key = next((key for key in payload.keys() if "Technical Analysis" in key), None)
        if not series_key:
            raise AlphaVantageError("未获取到指标数据")
        data_series = payload.get(series_key, {})
        return {
            "symbol": symbol,
            "indicator": indicator.upper(),
            "interval": interval,
            "series": [
                {
                    "timestamp": ts,
                    **{k.lower(): float(v) for k, v in values.items()},
                }
                for ts, values in data_series.items()
            ],
        }

    # ------------------------------------------------------------------
    # internal helpers

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = self._resolve_api_key()
        if not api_key:
            raise AlphaVantageError("请先在系统配置中填写 Alpha Vantage API Key")
        merged = dict(params)
        merged["apikey"] = api_key
        self._respect_rate_limit()
        response = requests.get(API_BASE_URL, params=merged, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "Note" in data:
            raise AlphaVantageError("Alpha Vantage 限流，请稍后再试")
        if "Information" in data:
            raise AlphaVantageError(data["Information"])
        if "Error Message" in data:
            raise AlphaVantageError(data["Error Message"])
        return data

    def _respect_rate_limit(self) -> None:
        with self._lock:
            now = time.time()
            if len(self._call_times) == RATE_LIMIT_PER_MINUTE:
                earliest = self._call_times[0]
                elapsed = now - earliest
                if elapsed < 60:
                    time.sleep(60 - elapsed)
            self._call_times.append(time.time())

    def _resolve_api_key(self) -> str | None:
        configured = config_manager.data.get("alphavantage", {}).get("api_key")
        if configured:
            return configured
        return os.getenv("ALPHAVANTAGE_API_KEY")

    @staticmethod
    def _time_series_params(interval: str, adjusted: bool) -> Dict[str, Any]:
        if interval.startswith("intraday"):
            step = interval.split("_", 1)[-1]
            return {
                "function": "TIME_SERIES_INTRADAY",
                "interval": step,
                "adjusted": "true" if adjusted else "false",
            }
        mapping = {
            "daily": "TIME_SERIES_DAILY",
            "weekly": "TIME_SERIES_WEEKLY",
            "monthly": "TIME_SERIES_MONTHLY",
        }
        function = mapping.get(interval, "TIME_SERIES_DAILY")
        if interval == "daily" and adjusted:
            function = "TIME_SERIES_DAILY_ADJUSTED"
        if interval == "weekly" and adjusted:
            function = "TIME_SERIES_WEEKLY_ADJUSTED"
        if interval == "monthly" and adjusted:
            function = "TIME_SERIES_MONTHLY_ADJUSTED"
        return {"function": function}

    @staticmethod
    def _extract_time_series(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        for key, value in payload.items():
            if "Time Series" in key:
                return value
        raise AlphaVantageError("返回数据中没有找到时间序列")

    @staticmethod
    def _format_bar(timestamp: str, values: Dict[str, Any]) -> Dict[str, Any]:
        def _float(key: str) -> float | None:
            raw = values.get(key)
            try:
                return float(raw) if raw is not None else None
            except (TypeError, ValueError):
                return None

        return {
            "timestamp": timestamp,
            "open": _float("1. open"),
            "high": _float("2. high"),
            "low": _float("3. low"),
            "close": _float("4. close"),
            "adjusted_close": _float("5. adjusted close") or _float("4. close"),
            "volume": values.get("6. volume") or values.get("5. volume"),
        }


client = AlphaVantageClient()

