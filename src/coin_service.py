"""
coin_service.py
دریافت لیست کوین‌ها و داده‌های تاریخی از CoinGecko.
Fetches coin lists and historical data from CoinGecko.

V1.1.0 - اضافه شدن دسته‌بندی میم‌کوین و کش (cache) فایل.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import settings
from .rate_limiter import get_rate_limiter


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Cache ساده فایل
# --------------------------------------------------------------------------- #
class FileCache:
    """کش ساده مبتنی بر فایل برای کاهش درخواست‌های API."""

    def __init__(self, cache_dir: str, ttl_seconds: int = 3600) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds

    def _key(self, *args) -> str:
        """تولید کلید کش از آرگومان‌ها."""
        raw = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, *args) -> Optional[Any]:
        """دریافت داده از کش. اگر نبود یا منقضی شده بود، None برمی‌گرداند."""
        if not settings.ENABLE_CACHE:
            return None
        key = self._key(*args)
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            mtime = path.stat().st_mtime
            if time.time() - mtime > self.ttl:
                return None  # منقضی شده
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache read error: %s", exc)
            return None

    def set(self, value: Any, *args) -> None:
        """ذخیره داده در کش."""
        if not settings.ENABLE_CACHE:
            return
        key = self._key(*args)
        path = self.cache_dir / f"{key}.json"
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache write error: %s", exc)

    def clear(self) -> int:
        """پاک کردن تمام فایل‌های کش. برمی‌گرداند تعداد فایل‌های حذف شده."""
        deleted = 0
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass
        return deleted


# --------------------------------------------------------------------------- #
# CoinGeckoClient
# --------------------------------------------------------------------------- #
class CoinGeckoClient:
    """کلاینت برای API عمومی CoinGecko با کش و پشتیبانی از کلید API."""

    def __init__(self) -> None:
        self.base_url = settings.COINGECKO_BASE_URL
        self.headers = settings.request_headers
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.cache = FileCache(settings.CACHE_DIR, settings.CACHE_TTL_SECONDS)

    # ------------------------------------------------------------------ #
    # low-level HTTP
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: Optional[dict] = None,
             use_cache: bool = True) -> Any:
        url = f"{self.base_url}{path}"

        # تلاش برای دریافت از کش
        cache_key = (path, json.dumps(params, sort_keys=True) if params else "")
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT for %s", path)
                return cached

        last_error: Optional[Exception] = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                # دریافت token از rate limiter پیش از ارسال درخواست
                if not get_rate_limiter().acquire(timeout=30.0):
                    logger.warning("Rate limiter timeout, retrying...")
                    continue

                resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    wait = settings.REQUEST_DELAY * attempt * 2
                    logger.warning("Rate limited by CoinGecko, sleeping %.1fs", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                # ذخیره در کش
                if use_cache:
                    self.cache.set(data, cache_key)
                return data
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Attempt %d/%d failed for %s: %s",
                               attempt, settings.MAX_RETRIES, path, exc)
                time.sleep(settings.REQUEST_DELAY)
        raise RuntimeError(f"CoinGecko request failed after {settings.MAX_RETRIES} retries: {last_error}")

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def get_top_markets(self, per_page: int = 100, page: int = 1) -> List[Dict[str, Any]]:
        """دریافت لیست بازارهای برتر."""
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        }
        data = self._get("/coins/markets", params=params)
        return data or []

    def get_coins_by_category(self, category: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        دریافت کوین‌های یک دسته‌بندی خاص - جدید در V1.1.0.
        مثال: meme-token, dog-themed-coins
        """
        params = {
            "vs_currency": "usd",
            "category": category,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        }
        data = self._get("/coins/markets", params=params)
        return data or []

    def get_coin_history(self, coin_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """دریافت داده تاریخی روزانه OHLC."""
        params = {"vs_currency": "usd", "days": days, "interval": "daily"}
        data = self._get(f"/coins/{coin_id}/ohlc", params=params)
        return data or []

    def get_coin_market_chart(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """دریافت داده بازار شامل قیمت‌ها و حجم‌ها."""
        params = {"vs_currency": "usd", "days": days, "interval": "daily"}
        data = self._get(f"/coins/{coin_id}/market_chart", params=params)
        return data or {}

    def get_coin_market_chart_by_timeframe(self, coin_id: str,
                                           timeframe: str = "1d") -> Dict[str, Any]:
        """
        دریافت داده بازار در بازه زمانی مشخص - V1.2.0.

        timeframe: '1d' (روزانه)، '4h' (4 ساعته)، '1h' (ساعتی)
        """
        days_map = {"1d": 30, "4h": 7, "1h": 3}
        interval_map = {"1d": "daily", "4h": "hourly", "1h": "hourly"}

        days = days_map.get(timeframe, 30)
        interval = interval_map.get(timeframe, "daily")

        params = {"vs_currency": "usd", "days": days, "interval": interval}
        data = self._get(f"/coins/{coin_id}/market_chart", params=params)
        return data or {}

    def get_coin_ohlc(self, coin_id: str, days: int = 30) -> List[List[float]]:
        """
        دریافت OHLC برای محاسبه ATR - جدید در V1.1.0.
        فرمت: [timestamp, open, high, low, close]
        """
        params = {"vs_currency": "usd", "days": days}
        data = self._get(f"/coins/{coin_id}/ohlc", params=params)
        return data or []

    # ------------------------------------------------------------------ #
    # filter helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_likely_meme(coin: Dict[str, Any]) -> bool:
        """
        فیلتر پیشرفته برای تشخیص میم‌کوین با دو روش:
        1. کلمات کلیدی (موجود در نام یا نماد)
        2. مارکت‌کپ متوسط + نوسان بالا
        """
        symbol = (coin.get("symbol") or "").lower()
        name = (coin.get("name") or "").lower()
        # فیلتر استیبل‌کوین‌ها
        if symbol.upper() in settings.STABLECOIN_SYMBOLS:
            return False
        # تشخیص با کلمات کلیدی
        for kw in settings.MEME_KEYWORDS:
            if kw in name or kw in symbol:
                return True
        # مارکت‌کپ متوسط + نوسان بالا → احتمال میم‌کوین
        mcap = coin.get("market_cap") or 0
        change_24h = abs(coin.get("price_change_percentage_24h") or 0)
        if mcap < 2_000_000_000 and change_24h > 15:
            return True
        return False


def fetch_meme_candidates(client: CoinGeckoClient, limit: int = 50) -> List[Dict[str, Any]]:
    """
    دریافت کوین‌های برتر و فیلتر آن‌ها برای یافتن میم‌کوین‌های بالقوه.
    V1.1.0 - اکنون از دسته‌بندی CoinGecko هم استفاده می‌کند.
    """
    all_candidates: List[Dict[str, Any]] = []
    seen_ids = set()

    # روش 1: استفاده از دسته‌بندی CoinGecko (ترجیحی)
    if settings.USE_COINGECKO_CATEGORIES:
        for category in settings.MEME_CATEGORIES:
            try:
                logger.info("دریافت کوین‌های دسته: %s", category)
                coins = client.get_coins_by_category(category, per_page=50)
                for coin in coins:
                    cid = coin.get("id")
                    if cid and cid not in seen_ids:
                        seen_ids.add(cid)
                        all_candidates.append(coin)
            except Exception as exc:  # noqa: BLE001
                logger.warning("خطا در دریافت دسته %s: %s", category, exc)

    # روش 2: فیلتر کلمات کلیدی از 100 کوین برتر (پشتیبان)
    if len(all_candidates) < limit:
        try:
            top_coins = client.get_top_markets(per_page=settings.TOP_N_COINS, page=1)
            for coin in top_coins:
                cid = coin.get("id")
                if cid and cid not in seen_ids and CoinGeckoClient.is_likely_meme(coin):
                    seen_ids.add(cid)
                    all_candidates.append(coin)
        except Exception as exc:  # noqa: BLE001
            logger.warning("خطا در دریافت کوین‌های برتر: %s", exc)

    # فیلتر مالی نهایی
    candidates: List[Dict[str, Any]] = []
    for coin in all_candidates:
        mcap = coin.get("market_cap") or 0
        vol = coin.get("total_volume") or 0
        if mcap > settings.MAX_MARKET_CAP_USD:
            continue
        if vol < settings.MIN_24H_VOLUME_USD:
            continue
        candidates.append(coin)
        if len(candidates) >= limit:
            break

    logger.info("Found %d meme-coin candidates after filtering "
                "(from %d total)", len(candidates), len(all_candidates))
    return candidates


def enrich_with_history(client: CoinGeckoClient, coin_id: str,
                         days: int = 30) -> Dict[str, Any]:
    """
    دریافت سری تاریخی قیمت، حجم و OHLC برای یک کوین.
    V1.1.0 - اکنون OHLC را هم برای ATR برمی‌گرداند.
    """
    chart = client.get_coin_market_chart(coin_id, days=days)
    prices = chart.get("prices", [])
    volumes = chart.get("total_volumes", [])

    # تلاش برای دریافت OHLC برای ATR
    highs: List[float] = []
    lows: List[float] = []
    closes: List[float] = []
    try:
        ohlc_data = client.get_coin_ohlc(coin_id, days=days)
        for candle in ohlc_data:
            # فرمت: [timestamp, open, high, low, close]
            if len(candle) >= 5:
                highs.append(float(candle[2]))
                lows.append(float(candle[3]))
                closes.append(float(candle[4]))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to get OHLC for %s: %s", coin_id, exc)

    return {
        "prices": [p[1] for p in prices],
        "volumes": [v[1] for v in volumes],
        "timestamps": [p[0] for p in prices],
        "highs": highs,
        "lows": lows,
        "closes": closes,
    }
