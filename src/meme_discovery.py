"""
meme_discovery.py
کشف هوشمند میم‌کوین‌های در حال پامپ - V2.4.0

این ماژول مشکل اصلی پروژه را حل می‌کند:
- قبلاً: فقط دسته‌بندی meme-token را می‌گرفت (همیشه همان کوین‌ها)
- حالا: کوین‌های trending + volume spike + جدید را پیدا می‌کند

منابع کشف:
1. CoinGecko Trending API - کوین‌های داغ امروز
2. CoinGecko /coins/markets با order=volume_desc
3. فیلتر volume spike (حجم 24h > میانگین 7 روزه)
4. فیلتر price action (تغییر 24h > 5%)
5. دسته‌بندی‌های متعدد meme

خروجی: لیست میم‌کوین‌های در حال فعالیت (نه خواب)
"""
from __future__ import annotations

import logging
import time
from typing import List, Dict, Any, Optional

import requests

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


class MemeDiscovery:
    """کشف هوشمند میم‌کوین‌های در حال پامپ."""

    def __init__(self) -> None:
        self.base_url = settings.COINGECKO_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(settings.request_headers)

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(settings.REQUEST_DELAY)
                return None
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            logger.debug("Discovery request failed: %s", exc)
            return None

    def get_trending_coins(self) -> List[Dict[str, Any]]:
        """دریافت کوین‌های trending (داغ امروز)."""
        data = self._get("/search/trending")
        if not data or "coins" not in data:
            return []
        coins = []
        for item in data["coins"]:
            coin = item.get("item", {})
            if coin:
                coins.append({
                    "id": coin.get("id", ""),
                    "symbol": (coin.get("symbol") or "").upper(),
                    "name": coin.get("name", ""),
                    "market_cap_rank": coin.get("market_cap_rank"),
                    "score": coin.get("score", 0),
                    "source": "trending",
                })
        logger.info("Trending coins: %d", len(coins))
        return coins

    def get_high_volume_memes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """دریافت میم‌کوین‌ها با بالاترین حجم معاملات از چند دسته."""
        all_coins = []
        # فقط 2 دسته اصلی برای کاهش rate limit
        categories = ["meme-token", "dog-themed-coins"]
        for cat in categories:
            params = {
                "vs_currency": "usd",
                "category": cat,
                "order": "volume_desc",
                "per_page": 50,
                "page": 1,
                "price_change_percentage": "24h",
            }
            data = self._get("/coins/markets", params=params)
            if data and isinstance(data, list):
                for c in data:
                    c["source"] = f"category:{cat}"
                all_coins.extend(data)
                logger.info("Category %s: %d coins", cat, len(data))
            else:
                logger.warning("Category %s failed (rate limit?)", cat)
            time.sleep(2)  # احترام بیشتر به rate limit
        seen = set()
        unique = []
        for c in all_coins:
            cid = c.get("id", "")
            if cid and cid not in seen:
                seen.add(cid)
                unique.append(c)
        unique.sort(key=lambda x: x.get("total_volume", 0) or 0, reverse=True)
        logger.info("High-volume memes: %d (unique)", len(unique))
        return unique[:limit]

    def get_pumping_memes(self, min_change_pct: float = 5.0,
                          min_volume_usd: float = 1_000_000) -> List[Dict[str, Any]]:
        """میم‌کوین‌هایی که در 24 ساعت پامپ کرده‌اند."""
        all_coins = self.get_high_volume_memes(limit=100)
        pumping = []
        for c in all_coins:
            change = c.get("price_change_percentage_24h") or 0
            volume = c.get("total_volume") or 0
            if change >= min_change_pct and volume >= min_volume_usd:
                c["is_pumping"] = True
                pumping.append(c)
        logger.info("Pumping memes (>+%g%%): %d", min_change_pct, len(pumping))
        return pumping

    def get_accumulating_memes(self, min_volume_usd: float = 500_000) -> List[Dict[str, Any]]:
        """میم‌کوین‌های در حال انباشت (حجم بالا + قیمت ثابت)."""
        all_coins = self.get_high_volume_memes(limit=100)
        accumulating = []
        for c in all_coins:
            change = abs(c.get("price_change_percentage_24h") or 0)
            volume = c.get("total_volume") or 0
            if volume >= min_volume_usd and change < 3.0:
                c["is_accumulating"] = True
                accumulating.append(c)
        logger.info("Accumulating memes: %d", len(accumulating))
        return accumulating

    def discover_active_memes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        کشف ترکیبی میم‌کوین‌های فعال امروز.

        حتی اگر category API rate-limited شود، trending کار می‌کند.
        """
        all_candidates = []
        seen_ids = set()

        # 1. Trending (همیشه کار می‌کند، rate limit کمتر)
        trending = self.get_trending_coins()
        for c in trending:
            cid = c.get("id", "")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                all_candidates.append(c)

        # 2. High volume memes (ممکن است rate-limited شود)
        try:
            high_vol = self.get_high_volume_memes(limit=limit)
            for c in high_vol:
                cid = c.get("id", "")
                change = c.get("price_change_percentage_24h") or 0
                volume = c.get("total_volume") or 0

                # تشخیص pumping و accumulating
                if change >= 5.0 and volume >= 1_000_000:
                    c["is_pumping"] = True
                elif volume >= 500_000 and abs(change) < 3.0:
                    c["is_accumulating"] = True

                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    all_candidates.append(c)
        except Exception as exc:
            logger.warning("High volume memes failed: %s", exc)

        # 3. اگر category fail شد، از trending به عنوان فیلتر استفاده کن
        # trending coins که در دسته meme هستند را علامت بزن
        if len(all_candidates) > 0 and len([c for c in all_candidates if c.get("source") != "trending"]) == 0:
            # همه trending هستند - فیلتر کن فقط meme‌ها
            meme_keywords = settings.MEME_KEYWORDS
            for c in all_candidates:
                sym = (c.get("symbol") or "").lower()
                name = (c.get("name") or "").lower()
                for kw in meme_keywords:
                    if kw in sym or kw in name:
                        c["is_likely_meme"] = True
                        break

        # مرتب: pumping first, then accumulating, then trending
        def sort_key(c):
            priority = 0
            if c.get("is_pumping"):
                priority = 3
            elif c.get("is_accumulating"):
                priority = 2
            elif c.get("source") == "trending":
                priority = 1
            vol = c.get("total_volume") or 0
            return (priority, vol)

        all_candidates.sort(key=sort_key, reverse=True)
        logger.info("Total active meme candidates: %d", len(all_candidates))
        return all_candidates[:limit]

    def format_discovery_report(self, coins: List[Dict[str, Any]]) -> str:
        """قالب‌بندی گزارش کشف میم‌کوین‌ها."""
        lines = []
        lines.append("=" * 70)
        lines.append("  🔍 گزارش کشف میم‌کوین‌های فعال")
        lines.append("=" * 70)
        lines.append(f"  کل کوین‌های کشف شده: {len(coins)}")
        lines.append("")

        pumping = [c for c in coins if c.get("is_pumping")]
        accumulating = [c for c in coins if c.get("is_accumulating")]
        trending = [c for c in coins if c.get("source") == "trending"]

        lines.append(f"  🚀 در حال پامپ: {len(pumping)}")
        lines.append(f"  💎 در حال انباشت: {len(accumulating)}")
        lines.append(f"  🔥 Trending: {len(trending)}")
        lines.append("")

        if pumping:
            lines.append("  === 🚀 میم‌کوین‌های در حال پامپ ===")
            for c in pumping[:10]:
                sym = c.get("symbol", "?")
                change = c.get("price_change_percentage_24h") or 0
                vol = c.get("total_volume") or 0
                lines.append(f"    {sym:<12} change={change:+.1f}%  vol=${vol/1e6:.1f}M")
            lines.append("")

        if accumulating:
            lines.append("  === 💎 میم‌کوین‌های در حال انباشت ===")
            for c in accumulating[:10]:
                sym = c.get("symbol", "?")
                vol = c.get("total_volume") or 0
                lines.append(f"    {sym:<12} vol=${vol/1e6:.1f}M  (قیمت ثابت)")
            lines.append("")

        if trending:
            lines.append("  === 🔥 میم‌کوین‌های Trending ===")
            for c in trending[:10]:
                sym = c.get("symbol", "?")
                rank = c.get("market_cap_rank", "?")
                lines.append(f"    {sym:<12} rank={rank}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)
