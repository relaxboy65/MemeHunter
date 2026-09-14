"""
kucoin_provider.py
لایه داده واقعی KuCoin Public API - V1.4.0.

اولویت اصلی برای:
- OHLCV (کندل روزانه/ساعتی) → اندیکاتورها
- Order book depth → Liquidity واقعی
- Recent trades → Order Flow / CVD واقعی

بدون نیاز به کلید API.
محدودیت Public حدود 2000 وزن / 30ثانیه (بسیار راحت‌تر از CoinGecko).

نمادها به صورت BASE-QUOTE هستند (مثلاً PEPE-USDT).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import requests

from .config import settings
from .rate_limiter import get_rate_limiter
from .binance_provider import OrderFlowReal, LiquidityReal


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class KuCoinAvailability:
    """نتیجه بررسی لیست بودن یک کوین در KuCoin Spot."""
    available: bool
    symbol: str = ""  # e.g. PEPE-USDT


class KuCoinClient:
    """کلاینت KuCoin Public REST - رایگان، بدون کلید."""

    # نگاشت نمادهای رایج
    SYMBOL_OVERRIDES = {
        "SHIB": "SHIB-USDT",
        "PEPE": "PEPE-USDT",
        "FLOKI": "FLOKI-USDT",
        "BONK": "BONK-USDT",
        "WIF": "WIF-USDT",
        "DOGE": "DOGE-USDT",
        "MEME": "MEME-USDT",
        "BOME": "BOME-USDT",
        "MYRO": "MYRO-USDT",
        "POPCAT": "POPCAT-USDT",
        "MEW": "MEW-USDT",
        "NEIRO": "NEIRO-USDT",
        "PNUT": "PNUT-USDT",
        "GOAT": "GOAT-USDT",
        "ACT": "ACT-USDT",
        "TRUMP": "TRUMP-USDT",
        "FARTCOIN": "FARTCOIN-USDT",
        "MOG": "MOG-USDT",
        "SPX": "SPX-USDT",
        "AI16Z": "AI16Z-USDT",
    }

    # نگاشت interval داخلی به type کوکوین
    INTERVAL_MAP = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1hour",
        "2h": "2hour",
        "4h": "4hour",
        "6h": "6hour",
        "8h": "8hour",
        "12h": "12hour",
        "1d": "1day",
        "1w": "1week",
    }

    def __init__(self) -> None:
        self.base_url = settings.KUCOIN_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": f"{settings.PROJECT_NAME}/{settings.PROJECT_VERSION}",
        })
        self._available_symbols: Optional[Set[str]] = None  # set of "PEPE-USDT"

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """GET با retry محدود. 429 → backoff کوتاه."""
        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                if not get_rate_limiter().acquire(timeout=20.0):
                    logger.warning("KuCoin rate limiter timeout, retrying...")
                    continue
                resp = self.session.get(
                    url, params=params, timeout=settings.REQUEST_TIMEOUT
                )
                if resp.status_code == 429:
                    wait = min(2 ** attempt, 10)
                    logger.warning("KuCoin rate limited, sleeping %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code in (400, 404):
                    return None
                resp.raise_for_status()
                body = resp.json()
                # KuCoin: code "200000" = success
                if isinstance(body, dict):
                    code = str(body.get("code", ""))
                    if code and code != "200000":
                        logger.debug("KuCoin code=%s msg=%s", code, body.get("msg"))
                        return None
                    return body.get("data", body)
                return body
            except requests.exceptions.RequestException as exc:
                last_error = exc
                time.sleep(min(0.5 * attempt, 3))
        logger.debug("KuCoin request failed after retries: %s %s", path, last_error)
        return None

    # ------------------------------------------------------------------ #
    # Symbols
    # ------------------------------------------------------------------ #
    def _load_symbols(self) -> Set[str]:
        if self._available_symbols is not None:
            return self._available_symbols
        data = self._get("/api/v2/symbols")
        symbols: Set[str] = set()
        if isinstance(data, list):
            for item in data:
                try:
                    sym = item.get("symbol") or ""
                    quote = (item.get("quoteCurrency") or "").upper()
                    enabled = item.get("enableTrading", True)
                    if sym and quote == "USDT" and enabled:
                        symbols.add(sym.upper())
                except (AttributeError, TypeError):
                    continue
        self._available_symbols = symbols
        logger.info("KuCoin: %d نماد USDT فعال بارگذاری شد", len(symbols))
        return symbols

    def _make_symbol(self, coin_symbol: str) -> Optional[str]:
        """تبدیل نماد ساده (PEPE) به PEPE-USDT."""
        if not coin_symbol:
            return None
        raw = coin_symbol.upper().replace("USDT", "").replace("-", "").strip()
        if not raw:
            return None
        if raw in self.SYMBOL_OVERRIDES:
            return self.SYMBOL_OVERRIDES[raw]
        candidate = f"{raw}-USDT"
        known = self._load_symbols()
        if candidate in known:
            return candidate
        # تلاش بدون بارگذاری کامل (برای سرعت)
        return candidate

    def is_available(self, coin_symbol: str) -> KuCoinAvailability:
        """بررسی لیست بودن نماد در Spot KuCoin."""
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return KuCoinAvailability(available=False)
        known = self._load_symbols()
        if symbol in known:
            return KuCoinAvailability(available=True, symbol=symbol)
        # اگر لیست خالی بود (خطای شبکه)، یک بار candles تست کن
        if not known:
            test = self.get_klines(coin_symbol, interval="1d", limit=1)
            if test:
                return KuCoinAvailability(available=True, symbol=symbol)
        return KuCoinAvailability(available=False, symbol=symbol)

    # ------------------------------------------------------------------ #
    # Klines / OHLCV
    # ------------------------------------------------------------------ #
    def get_klines(self, coin_symbol: str, interval: str = "1d",
                   limit: int = 100) -> Optional[List[List]]:
        """
        دریافت کندل از KuCoin.

        type: 1min, 1hour, 1day, ...
        پاسخ KuCoin: [time, open, close, high, low, volume, turnover]
        برای سازگاری با بقیه کد، به فرمت [ts, open, high, low, close, volume] تبدیل می‌شود.
        """
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        ktype = self.INTERVAL_MAP.get(interval, interval)
        params = {"symbol": symbol, "type": ktype}
        data = self._get("/api/v1/market/candles", params=params)
        if not isinstance(data, list) or not data:
            return None

        # KuCoin معمولاً از جدید به قدیم برمی‌گرداند → برعکس می‌کنیم
        rows: List[List] = []
        for candle in reversed(data):
            try:
                if len(candle) < 6:
                    continue
                ts = int(float(candle[0]))
                # اگر ثانیه است به میلی‌ثانیه نزدیک نکنیم؛ indicators با ترتیب کار می‌کند
                o = float(candle[1])
                c = float(candle[2])
                h = float(candle[3])
                l = float(candle[4])
                v = float(candle[5])
                rows.append([ts, o, h, l, c, v])
            except (ValueError, TypeError, IndexError):
                continue

        if limit and len(rows) > limit:
            rows = rows[-limit:]
        return rows if rows else None

    def get_history_ohlcv(self, coin_symbol: str,
                          days: int = 30) -> Optional[Dict[str, List]]:
        """
        خروجی سازگار با enrich_with_history:
        prices, volumes, highs, lows, closes, timestamps
        """
        klines = self.get_klines(coin_symbol, interval="1d", limit=max(days + 5, 40))
        if not klines or len(klines) < 14:
            return None
        # فقط N روز آخر
        klines = klines[-days:] if len(klines) > days else klines
        return {
            "prices": [float(k[4]) for k in klines],   # close
            "volumes": [float(k[5]) for k in klines],
            "highs": [float(k[2]) for k in klines],
            "lows": [float(k[3]) for k in klines],
            "closes": [float(k[4]) for k in klines],
            "timestamps": [int(k[0]) * 1000 if k[0] < 1e12 else int(k[0]) for k in klines],
            "source": "KuCoin candles",
        }

    def get_multi_timeframe_data(self, coin_symbol: str,
                                 timeframes: tuple = ("1d", "4h")) -> Dict[str, List]:
        result: Dict[str, List] = {}
        for tf in timeframes:
            klines = self.get_klines(coin_symbol, interval=tf, limit=100)
            if klines:
                result[tf] = klines
            time.sleep(0.15)
        return result

    # ------------------------------------------------------------------ #
    # Order book → Liquidity
    # ------------------------------------------------------------------ #
    def get_depth(self, coin_symbol: str, size: int = 20) -> Optional[Dict]:
        """
        depth جزئی: level2_20 یا level2_100
        پاسخ: {"bids": [[price, size], ...], "asks": [...]}
        """
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        size = 20 if size <= 20 else 100
        path = f"/api/v1/market/orderbook/level2_{size}"
        data = self._get(path, params={"symbol": symbol})
        if not isinstance(data, dict):
            return None
        return data

    def compute_liquidity(self, coin_symbol: str) -> Optional[LiquidityReal]:
        depth = self.get_depth(coin_symbol, size=settings.KUCOIN_DEPTH_LIMIT)
        if not depth:
            return None
        bids = depth.get("bids") or []
        asks = depth.get("asks") or []
        if not bids or not asks:
            return None
        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
        except (ValueError, IndexError, TypeError):
            return None

        bid_depth_usd = 0.0
        for bid in bids:
            try:
                bid_depth_usd += float(bid[0]) * float(bid[1])
            except (ValueError, IndexError, TypeError):
                continue
        ask_depth_usd = 0.0
        for ask in asks:
            try:
                ask_depth_usd += float(ask[0]) * float(ask[1])
            except (ValueError, IndexError, TypeError):
                continue

        total = bid_depth_usd + ask_depth_usd
        if total <= 0 or best_bid <= 0:
            return None
        spread_pct = (best_ask - best_bid) / best_bid * 100
        imbalance = (bid_depth_usd - ask_depth_usd) / total

        notes: List[str] = []
        if imbalance > 0.2:
            notes.append(f"عدم تعادل خریداران {imbalance*100:.1f}%")
        elif imbalance < -0.2:
            notes.append(f"عدم تعادل فروشندگان {imbalance*100:.1f}%")
        if spread_pct < 0.15:
            notes.append(f"اسپرد کم {spread_pct:.3f}%")
        elif spread_pct > 1.0:
            notes.append(f"اسپرد بالا {spread_pct:.2f}%")

        return LiquidityReal(
            bid_depth_usd=bid_depth_usd,
            ask_depth_usd=ask_depth_usd,
            total_depth_usd=total,
            spread_pct=spread_pct,
            imbalance=imbalance,
            best_bid=best_bid,
            best_ask=best_ask,
            is_real=True,
            source="KuCoin depth",
            notes=notes,
        )

    # ------------------------------------------------------------------ #
    # Trades → Order Flow
    # ------------------------------------------------------------------ #
    def get_recent_trades(self, coin_symbol: str) -> Optional[List[Dict]]:
        """
        تاریخچه معاملات اخیر.
        هر آیتم: {sequence, price, size, side, time, ...}
        side: "buy" | "sell"
        """
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        data = self._get("/api/v1/market/histories", params={"symbol": symbol})
        return data if isinstance(data, list) else None

    def compute_orderflow(self, coin_symbol: str,
                          current_price: Optional[float] = None,
                          market_cap: Optional[float] = None) -> Optional[OrderFlowReal]:
        trades = self.get_recent_trades(coin_symbol)
        if not trades:
            return None

        large_threshold = self._large_trade_threshold(market_cap)
        buy_vol = 0.0
        sell_vol = 0.0
        large_buys = 0
        large_sells = 0
        large_trade_volume = 0.0

        ref_price = current_price or 0.0
        if ref_price <= 0 and trades:
            try:
                ref_price = float(trades[0].get("price", 0))
            except (ValueError, TypeError):
                ref_price = 0.0

        for t in trades:
            try:
                price = float(t.get("price", 0))
                size = float(t.get("size", 0))
                side = (t.get("side") or "").lower()
                trade_value = price * size
                if side == "buy":
                    buy_vol += size
                    if trade_value >= large_threshold:
                        large_buys += 1
                        large_trade_volume += trade_value
                elif side == "sell":
                    sell_vol += size
                    if trade_value >= large_threshold:
                        large_sells += 1
                        large_trade_volume += trade_value
            except (ValueError, TypeError):
                continue

        total = buy_vol + sell_vol
        if total <= 0:
            return None

        buy_pressure = buy_vol / total
        sell_pressure = sell_vol / total
        cvd = buy_vol - sell_vol

        notes: List[str] = []
        if buy_pressure > 0.6:
            notes.append(f"فشار خرید واقعی {buy_pressure*100:.0f}% (KuCoin)")
        elif sell_pressure > 0.6:
            notes.append(f"فشار فروش واقعی {sell_pressure*100:.0f}% (KuCoin)")
        if large_buys > large_sells and large_buys > 0:
            notes.append(f"تریدهای بزرگ خرید بیشتر ({large_buys} vs {large_sells})")
        elif large_sells > large_buys and large_sells > 0:
            notes.append(f"تریدهای بزرگ فروش بیشتر ({large_sells} vs {large_buys})")

        return OrderFlowReal(
            cvd=cvd,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            total_volume=total,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            large_trades_count=large_buys + large_sells,
            large_buys=large_buys,
            large_sells=large_sells,
            large_trade_volume=large_trade_volume,
            is_real=True,
            source="KuCoin trades",
            notes=notes,
        )

    def _large_trade_threshold(self, market_cap: Optional[float]) -> float:
        base = settings.KUCOIN_LARGE_TRADE_USD
        if market_cap is None or market_cap <= 0:
            return base
        if market_cap < 100_000_000:
            return 10_000.0
        if market_cap < 1_000_000_000:
            return 25_000.0
        return base
