"""
dex_provider.py
لایه داده میم‌کوین‌های فقط-DEX - V1.3.1.

این ماژول برای کوین‌هایی که در Binance لیست نشده‌اند استفاده می‌شود:
- DexScreener: نقدینگی pool، حجم، buys/sells ratio
- GeckoTerminal: OHLCV تاریخی برای بک‌تست

هر دو کاملاً رایگان و بدون نیاز به کلید API.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from .config import settings
from .rate_limiter import get_rate_limiter


logger = logging.getLogger(settings.PROJECT_SLUG)


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass
class DexPoolData:
    """داده یک pool از DexScreener."""
    pair_address: str
    chain: str
    dex: str
    base_token_symbol: str
    base_token_address: str
    price_usd: float
    liquidity_usd: float
    volume_24h: float
    volume_6h: float
    volume_1h: float
    txns_24h_buys: int
    txns_24h_sells: int
    price_change_24h: float
    fdv: Optional[float] = None
    market_cap: Optional[float] = None
    pair_created_at: Optional[str] = None
    notes: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# DexScreener Client
# --------------------------------------------------------------------------- #
class DexScreenerClient:
    """کلاینت DexScreener API - رایگان، بدون کلید."""

    def __init__(self) -> None:
        self.base_url = settings.DEXSCREENER_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": f"{settings.PROJECT_SLUG}/{settings.PROJECT_VERSION} (public data)",
        })

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """درخواست GET با rate limiter."""
        url = f"{self.base_url}{path}"
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                if not get_rate_limiter().acquire(timeout=30.0):
                    continue
                resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    wait = settings.REQUEST_DELAY * attempt
                    logger.warning("DexScreener rate limited, sleeping %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.HTTPError,
                    requests.exceptions.RequestException) as exc:
                logger.warning("DexScreener attempt %d/%d failed: %s",
                               attempt, settings.MAX_RETRIES, exc)
                time.sleep(settings.REQUEST_DELAY)
        return None

    def search_token(self, query: str) -> List[Dict[str, Any]]:
        """جستجوی توکن در DexScreener."""
        data = self._get("/latest/dex/search", params={"q": query})
        if not data or not isinstance(data, dict):
            return []
        return data.get("pairs", []) or data.get("tokens", [])

    def get_token_pools(self, token_address: str) -> List[Dict[str, Any]]:
        """دریافت تمام poolهای یک توکن."""
        data = self._get(f"/latest/dex/tokens/{token_address}")
        if not data or not isinstance(data, dict):
            return []
        return data.get("pairs", [])

    def parse_pool(self, pair_data: Dict[str, Any]) -> Optional[DexPoolData]:
        """تبدیل داده خام DexScreener به DexPoolData."""
        try:
            base_token = pair_data.get("baseToken", {})
            liquidity = pair_data.get("liquidity", {}) or {}
            volume = pair_data.get("volume", {}) or {}
            txns = pair_data.get("txns", {}) or {}
            txns_24h = txns.get("h24", {}) if isinstance(txns, dict) else {}
            price_change = pair_data.get("priceChange", {}) or {}
            price_change_24h = price_change.get("h24", 0) if isinstance(price_change, dict) else 0

            return DexPoolData(
                pair_address=pair_data.get("pairAddress", ""),
                chain=pair_data.get("chainId", ""),
                dex=pair_data.get("dexId", ""),
                base_token_symbol=base_token.get("symbol", ""),
                base_token_address=base_token.get("address", ""),
                price_usd=float(pair_data.get("priceUsd", 0) or 0),
                liquidity_usd=float(liquidity.get("usd", 0) or 0),
                volume_24h=float(volume.get("h24", 0) or 0),
                volume_6h=float(volume.get("h6", 0) or 0),
                volume_1h=float(volume.get("h1", 0) or 0),
                txns_24h_buys=int(txns_24h.get("buys", 0)) if isinstance(txns_24h, dict) else 0,
                txns_24h_sells=int(txns_24h.get("sells", 0)) if isinstance(txns_24h, dict) else 0,
                price_change_24h=float(price_change_24h or 0),
                fdv=float(pair_data.get("fdv", 0)) if pair_data.get("fdv") else None,
                market_cap=float(pair_data.get("marketCap", 0)) if pair_data.get("marketCap") else None,
                pair_created_at=pair_data.get("pairCreatedAt"),
                notes=[],
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("Failed to parse DexScreener pool: %s", exc)
            return None

    def get_best_pool(self, symbol: str) -> Optional[DexPoolData]:
        """
        دریافت بهترین pool برای یک نماد.
        بهترین = بیشترین نقدینگی.
        """
        pools_data = self.search_token(symbol)
        if not pools_data:
            return None

        # فیلتر نماد
        matching_pools = []
        for pd in pools_data:
            base = pd.get("baseToken", {}).get("symbol", "").upper()
            if base == symbol.upper():
                parsed = self.parse_pool(pd)
                if parsed:
                    matching_pools.append(parsed)

        if not matching_pools:
            return None

        # انتخاب pool با بیشترین نقدینگی
        matching_pools.sort(key=lambda p: p.liquidity_usd, reverse=True)
        best = matching_pools[0]

        # یادداشت‌های تحلیلی
        if best.liquidity_usd > 1_000_000:
            best.notes.append(f"نقدینگی DEX بالا: ${best.liquidity_usd:,.0f}")
        elif best.liquidity_usd < 100_000:
            best.notes.append(f"نقدینکی DEX پایین: ${best.liquidity_usd:,.0f}")

        total_txns = best.txns_24h_buys + best.txns_24h_sells
        if total_txns > 0:
            buy_ratio = best.txns_24h_buys / total_txns
            if buy_ratio > 0.65:
                best.notes.append(f"خریداران بیشتر در DEX ({buy_ratio*100:.0f}%)")
            elif buy_ratio < 0.35:
                best.notes.append(f"فروشندگان بیشتر در DEX ({(1-buy_ratio)*100:.0f}%)")

        if best.volume_24h > 1_000_000:
            best.notes.append(f"حجم 24h DEX بالا: ${best.volume_24h:,.0f}")

        return best


# --------------------------------------------------------------------------- #
# GeckoTerminal Client
# --------------------------------------------------------------------------- #
class GeckoTerminalClient:
    """کلاینت GeckoTerminal API - رایگان، بدون کلید."""

    def __init__(self) -> None:
        self.base_url = settings.GECKOTERMINAL_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": f"{settings.PROJECT_SLUG}/{settings.PROJECT_VERSION} (public data)",
        })

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """درخواست GET با rate limiter."""
        url = f"{self.base_url}{path}"
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                if not get_rate_limiter().acquire(timeout=30.0):
                    continue
                resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    wait = settings.REQUEST_DELAY * attempt * 2
                    logger.warning("GeckoTerminal rate limited, sleeping %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.HTTPError,
                    requests.exceptions.RequestException) as exc:
                logger.warning("GeckoTerminal attempt %d/%d failed: %s",
                               attempt, settings.MAX_RETRIES, exc)
                time.sleep(settings.REQUEST_DELAY)
        return None

    def get_trending_pools(self) -> List[Dict[str, Any]]:
        """دریافت poolهای ترندینگ."""
        data = self._get("/networks/trending_pools")
        if not data or not isinstance(data, dict):
            return []
        return data.get("data", [])

    def get_pool_ohlcv(self, network: str, pool_address: str,
                      timeframe: str = "hour",
                      limit: int = 100) -> List[List[float]]:
        """
        دریافت OHLCV تاریخی یک pool.

        timeframe: 'minute', 'hour', 'day'
        برمی‌گرداند: [[timestamp, open, high, low, close, volume], ...]
        """
        params = {"limit": limit}
        # برای چندبره‌ای، از پارامتر aggregate استفاده می‌کنیم
        path = f"/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
        data = self._get(path, params=params)
        if not data or not isinstance(data, dict):
            return []
        return data.get("data", {}).get("ohlcv_list", []) or []
