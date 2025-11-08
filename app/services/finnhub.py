"""Finnhub API client abstraction."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List

import requests

from app.config.manager import config_manager

API_BASE = "https://finnhub.io/api/v1"


class FinnhubError(RuntimeError):
    """Raised when Finnhub returns an error."""


class FinnhubClient:
    """Encapsulate Finnhub API access."""

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        data = self._request("quote", {"symbol": symbol})
        return {
            "symbol": symbol,
            "price": data.get("c"),
            "change": data.get("d"),
            "change_percent": f"{data.get('dp')}%" if data.get("dp") is not None else None,
            "volume": data.get("v"),
            "latest_trading_day": self._ts_to_date(data.get("t")),
        }

    def fetch_overview(self, symbol: str) -> Dict[str, Any]:
        data = self._request("stock/profile2", {"symbol": symbol})
        if not data:
            raise FinnhubError("未获取到公司概览数据")
        return {
            "symbol": data.get("ticker"),
            "name": data.get("name"),
            "description": data.get("description"),
            "industry": data.get("finnhubIndustry"),
            "market_cap": data.get("marketCapitalization"),
            "pe_ratio": data.get("peBasicExclExtraTTM"),
            "website": data.get("weburl"),
        }

    def fetch_time_series(
        self,
        symbol: str,
        interval: str,
        outputsize: str = "compact",
        adjusted: bool = False,
        range_key: str | None = None,
    ) -> Dict[str, Any]:
        resolution = self._resolution(interval)
        lookback_days = self._lookback_days(range_key)
        now = int(time.time())
        start = now - lookback_days * 24 * 60 * 60
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start,
            "to": now,
        }
        data = self._request("stock/candle", params)
        if data.get("s") != "ok":
            raise FinnhubError("Finnhub 无可用历史数据")
        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])
        series: List[Dict[str, Any]] = []
        for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
            series.append(
                {
                    "timestamp": self._ts_to_iso(ts),
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "adjusted_close": c,
                    "volume": v,
                }
            )
        return {
            "symbol": symbol,
            "interval": interval,
            "range": range_key,
            "series": series,
        }

    def fetch_indicator(
        self,
        symbol: str,
        indicator: str,
        interval: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        resolution = self._resolution(interval)
        query = {"symbol": symbol, "resolution": resolution, "indicator": indicator.lower()}
        query.update(params)
        data = self._request("indicator", query)
        if data.get("s") != "ok":
            raise FinnhubError("Finnhub 未返回指标数据")
        timestamps = data.get("t", [])
        indicator_keys = [k for k, v in data.items() if isinstance(v, list) and k != "t"]
        series: List[Dict[str, Any]] = []
        for idx, ts in enumerate(timestamps):
            entry: Dict[str, Any] = {"timestamp": self._ts_to_iso(ts)}
            for key in indicator_keys:
                values = data.get(key, [])
                if idx < len(values):
                    entry[key] = values[idx]
            series.append(entry)
        return {"symbol": symbol, "indicator": indicator.upper(), "interval": interval, "series": series}

    # ------------------------------------------------------------------
    # helpers

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        token = self._resolve_api_key()
        if not token:
            raise FinnhubError("请先在系统配置中填写 Finnhub API Key")
        merged = dict(params)
        merged["token"] = token
        response = requests.get(f"{API_BASE}/{path}", params=merged, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # type: ignore[attr-defined]
            status = exc.response.status_code if exc.response is not None else ""
            message = exc.response.text if exc.response is not None else str(exc)
            raise FinnhubError(f"Finnhub 请求失败（{status}）：{message}") from exc
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            raise FinnhubError(data["error"])
        return data

    @staticmethod
    def _resolution(interval: str) -> str:
        if interval.startswith("intraday"):
            step = interval.split("_", 1)[-1]
            return step.replace("min", "")
        mapping = {
            "daily": "D",
            "weekly": "W",
            "monthly": "M",
        }
        return mapping.get(interval, "D")

    @staticmethod
    def _lookback_days(range_key: str | None) -> int:
        mapping = {
            "1D": 2,
            "1W": 14,
            "1M": 60,
            "3M": 200,
            "1Y": 400,
            "MAX": 5 * 365,
        }
        if range_key and range_key in mapping:
            return mapping[range_key]
        return 120

    def _resolve_api_key(self) -> str | None:
        configured = config_manager.data.get("finnhub", {}).get("api_key")
        if configured:
            return configured
        return os.getenv("FINNHUB_API_KEY")

    @staticmethod
    def _ts_to_iso(timestamp: int | None) -> str | None:
        if not timestamp:
            return None
        return datetime.utcfromtimestamp(timestamp).isoformat()

    @staticmethod
    def _ts_to_date(timestamp: int | None) -> str | None:
        if not timestamp:
            return None
        return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")


client = FinnhubClient()


