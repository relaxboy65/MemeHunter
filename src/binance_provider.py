"""
binance_provider.py
لایه داده واقعی Binance Public API - V1.3.0.

این ماژول داده‌های واقعی برای تحلیل‌های پیشرفته فراهم می‌کند:
- aggTrades → محاسبه CVD (Cumulative Volume Delta) واقعی
- depth → اسپرد و عمق واقعی order book
- klines → OHLCV با بازه‌های مختلف

کاملاً رایگان، بدون نیاز به کلید API.

توجه: فقط کوین‌های لیست‌شده در Binance (مثل PEPE، WIF، FLOKI) قابل استفاده هستند.
کوین‌های فقط DEX از این لایه پشتیبانی نمی‌شوند.
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
# Data classes برای نتایج
# --------------------------------------------------------------------------- #
@dataclass
class OrderFlowReal:
    """نتایج تحلیل اردرفلو واقعی از Binance aggTrades."""
    cvd: float                    # Cumulative Volume Delta (مثبت = خریداران تهاجمی‌تر)
    buy_volume: float             # حجم خریداران تهاجمی
    sell_volume: float            # حجم فروشندگان تهاجمی
    total_volume: float
    buy_pressure: float           # buy_volume / total_volume (0..1)
    sell_pressure: float          # sell_volume / total_volume (0..1)
    large_trades_count: int       # تعداد تریدهای بزرگ (smart money proxy)
    large_buys: int               # تریدهای بزرگ خرید
    large_sells: int              # تریدهای بزرگ فروش
    large_trade_volume: float     # حجم دلاری تریدهای بزرگ
    is_real: bool = True          # برچسب منبع داده
    source: str = "Binance aggTrades"
    notes: List[str] = field(default_factory=list)


@dataclass
class LiquidityReal:
    """نتایج تحلیل لیکوییدیتی واقعی از Binance depth."""
    bid_depth_usd: float          # ارزش کل bids
    ask_depth_usd: float          # ارزش کل asks
    total_depth_usd: float        # مجموع عمق
    spread_pct: float             # اسپرد به درصد
    imbalance: float              # عدم تعادل (bid-ask) / total (-1..1)
    best_bid: float
    best_ask: float
    is_real: bool = True
    source: str = "Binance depth"
    notes: List[str] = field(default_factory=list)


@dataclass
class BinanceAvailability:
    """نتیجه بررسی لیست بودن یک کوین در Binance."""
    available: bool
    symbol: str = ""
    spot: bool = False
    futures: bool = False


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class BinanceClient:
    """کلاینت Binance Public API - رایگان، بدون کلید."""

    # نگاشت نمادهای معمول به نماد Binance
    # این نگاشت باید به‌مرور کامل شود
    SYMBOL_OVERRIDES = {
        "SHIB": "SHIBUSDT",
        "PEPE": "PEPEUSDT",
        "FLOKI": "FLOKIUSDT",
        "BONK": "BONKUSDT",
        "WIF": "WIFUSDT",
        "DOGE": "DOGEUSDT",
        "ELON": "ELONUSDT",
        "MEME": "MEMEUSDT",
        "BOME": "BOMEUSDT",
        "MYRO": "MYROUSDT",
    }

    def __init__(self) -> None:
        self.spot_url = settings.BINANCE_SPOT_URL
        self.futures_url = settings.BINANCE_FUTURES_URL
        self.session = requests.Session()
        self.session.headers.update(settings.binance_headers)
        self._available_symbols: Optional[set] = None

    def _get(self, base_url: str, path: str, params: Optional[dict] = None) -> Any:
        """درخواست GET با rate limiter و retry."""
        url = f"{base_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                if not get_rate_limiter().acquire(timeout=30.0):
                    logger.warning("Rate limiter timeout, retrying...")
                    continue
                resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    wait = settings.REQUEST_DELAY * attempt
                    logger.warning("Binance rate limited, sleeping %.1fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 400:
                    # نماد نامعتبر یا لیست نشده
                    return None
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as exc:
                if resp.status_code == 400:
                    return None
                last_error = exc
                logger.warning("Binance HTTP error attempt %d/%d: %s",
                               attempt, settings.MAX_RETRIES, exc)
                time.sleep(settings.REQUEST_DELAY)
            except requests.exceptions.RequestException as exc:
                last_error = exc
                logger.warning("Binance request error attempt %d/%d: %s",
                               attempt, settings.MAX_RETRIES, exc)
                time.sleep(settings.REQUEST_DELAY)
        logger.error("Binance request failed after %d retries: %s",
                     settings.MAX_RETRIES, last_error)
        return None

    def _make_symbol(self, coin_symbol: str) -> str:
        """تبدیل نماد معمول به نماد Binance (SYMBOL + USDT)."""
        if not coin_symbol:
            return ""
        upper = coin_symbol.upper()
        # اگر از قبل کامل است
        if upper.endswith("USDT"):
            return upper
        # استفاده از override اگر موجود
        if upper in self.SYMBOL_OVERRIDES:
            return self.SYMBOL_OVERRIDES[upper]
        # پیش‌فرض: SYMBOL+USDT
        return f"{upper}USDT"

    def is_available(self, coin_symbol: str) -> BinanceAvailability:
        """بررسی اینکه آیا کوین در Binance لیست شده است."""
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return BinanceAvailability(available=False)

        # تست با klines (سبک‌ترین endpoint)
        data = self._get(self.spot_url, "/api/v3/klines",
                         {"symbol": symbol, "interval": "1d", "limit": 1})
        if data is None or (isinstance(data, list) and len(data) == 0):
            return BinanceAvailability(available=False, symbol=symbol)
        return BinanceAvailability(available=True, symbol=symbol, spot=True)

    # ------------------------------------------------------------------ #
    # aggTrades → Order Flow واقعی
    # ------------------------------------------------------------------ #
    def get_agg_trades(self, coin_symbol: str,
                       limit: int = 1000) -> Optional[List[Dict]]:
        """
        دریافت aggregated trades از Binance.

        فرمت هر ترید:
        {
            "a": aggregateTradeId,
            "p": "price",
            "q": "quantity",
            "T": timestamp,
            "m": isBuyerMaker  # مهم! True = فروشنده maker → خریدار تهاجمی → BUY
                              #                    False = خریدار maker → فروشنده تهاجمی → SELL
        }
        """
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        params = {"symbol": symbol, "limit": limit}
        data = self._get(self.spot_url, "/api/v3/aggTrades", params=params)
        return data if isinstance(data, list) else None

    def compute_orderflow(self, coin_symbol: str,
                          current_price: Optional[float] = None,
                          market_cap: Optional[float] = None) -> Optional[OrderFlowReal]:
        """
        محاسبه Order Flow واقعی از aggTrades.

        مکانیزم:
        - فیلد m=True یعنی خریدار taker است → فشار خرید (buy_volume)
        - فیلد m=False یعنی فروشنده taker است → فشار فروش (sell_volume)
        - CVD = buy_volume - sell_volume
        - تریدهای بزرگ (حجم دلاری > threshold) → proxy برای smart money

        V1.3.1 - آستانه large trade پویا بر اساس مارکت‌کپ:
        - میم‌کوین کوچک (مارکت‌کپ < 100M): آستانه پایین‌تر (10K)
        - میم‌کوین متوسط (100M-1B): آستانه میانی (25K)
        - میم‌کوین بزرگ (>1B): آستانه استاندارد (50K)
        """
        trades = self.get_agg_trades(coin_symbol, settings.BINANCE_AGGTRADES_LIMIT)
        if not trades:
            return None

        # V1.3.1 - آستانه پویای large trade
        large_trade_threshold = self._compute_large_trade_threshold(market_cap)

        buy_vol = 0.0
        sell_vol = 0.0
        large_buys = 0
        large_sells = 0
        large_trade_volume = 0.0

        # استفاده از قیمت فعلی برای تشخیص «ترید بزرگ»
        ref_price = current_price
        if ref_price is None or ref_price <= 0:
            try:
                ref_price = float(trades[0].get("p", 0))
            except (ValueError, IndexError, TypeError):
                ref_price = 0

        for trade in trades:
            try:
                price = float(trade.get("p", 0))
                qty = float(trade.get("q", 0))
                is_buyer_maker = trade.get("m", False)
                trade_value = price * qty

                if is_buyer_maker:
                    # m=True یعنی خریدار maker است → فروشنده تهاجمی → SELL
                    sell_vol += qty
                    if trade_value >= large_trade_threshold:
                        large_sells += 1
                        large_trade_volume += trade_value
                else:
                    # m=False یعنی فروشنده maker است → خریدار تهاجمی → BUY
                    buy_vol += qty
                    if trade_value >= large_trade_threshold:
                        large_buys += 1
                        large_trade_volume += trade_value
            except (ValueError, TypeError) as exc:
                logger.debug("Skip malformed trade: %s", exc)
                continue

        total_vol = buy_vol + sell_vol
        if total_vol == 0:
            return None

        buy_pressure = buy_vol / total_vol
        sell_pressure = sell_vol / total_vol
        cvd = buy_vol - sell_vol

        notes: List[str] = []
        if buy_pressure > 0.6:
            notes.append(f"فشار خرید واقعی {buy_pressure*100:.0f}% (CVD مثبت)")
        elif sell_pressure > 0.6:
            notes.append(f"فشار فروش واقعی {sell_pressure*100:.0f}% (CVD منفی)")
        if large_buys > large_sells and large_buys > 0:
            notes.append(f"تریدهای بزرگ خرید بیشتر ({large_buys} vs {large_sells}) - smart money proxy")
        elif large_sells > large_buys and large_sells > 0:
            notes.append(f"تریدهای بزرگ فروش بیشتر ({large_sells} vs {large_buys}) - smart money proxy")
        if large_trade_threshold != settings.BINANCE_LARGE_TRADE_USD:
            notes.append(f"آستانه large trade پویا: ${large_trade_threshold:,.0f} (بر اساس مارکت‌کپ)")

        return OrderFlowReal(
            cvd=cvd,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            total_volume=total_vol,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            large_trades_count=large_buys + large_sells,
            large_buys=large_buys,
            large_sells=large_sells,
            large_trade_volume=large_trade_volume,
            is_real=True,
            source="Binance aggTrades",
            notes=notes,
        )

    def _compute_large_trade_threshold(self, market_cap: Optional[float]) -> float:
        """
        محاسبه آستانه پویای large trade بر اساس مارکت‌کپ - V1.3.1.

        میم‌کوین‌های کوچک‌تر، تریدهای کوچک‌ترشان هم مهم است.
        """
        if market_cap is None or market_cap <= 0:
            return settings.BINANCE_LARGE_TRADE_USD
        if market_cap < 100_000_000:  # < 100M
            return 10_000.0  # 10K
        if market_cap < 1_000_000_000:  # < 1B
            return 25_000.0  # 25K
        return settings.BINANCE_LARGE_TRADE_USD  # 50K

    # ------------------------------------------------------------------ #
    # depth → Liquidity واقعی
    # ------------------------------------------------------------------ #
    def get_depth(self, coin_symbol: str,
                  limit: int = 100) -> Optional[Dict]:
        """دریافت order book snapshot."""
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        params = {"symbol": symbol, "limit": limit}
        data = self._get(self.spot_url, "/api/v3/depth", params=params)
        return data if isinstance(data, dict) else None

    def compute_liquidity(self, coin_symbol: str) -> Optional[LiquidityReal]:
        """
        محاسبه لیکوییدیتی واقعی از order book depth.

        مکانیزم:
        - مجموع ارزش bids = قدرت خریداران
        - مجموع ارزش asks = قدرت فروشندگان
        - اسپرد = (best_ask - best_bid) / best_bid * 100
        - imbalance = (bid_depth - ask_depth) / total
        """
        depth = self.get_depth(coin_symbol, settings.BINANCE_DEPTH_LIMIT)
        if not depth or "bids" not in depth or "asks" not in depth:
            return None

        bids = depth.get("bids", [])
        asks = depth.get("asks", [])
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
                price = float(bid[0])
                qty = float(bid[1])
                bid_depth_usd += price * qty
            except (ValueError, IndexError, TypeError):
                continue

        ask_depth_usd = 0.0
        for ask in asks:
            try:
                price = float(ask[0])
                qty = ask[1] if isinstance(ask[1], (int, float)) else float(ask[1])
                ask_depth_usd += price * qty
            except (ValueError, IndexError, TypeError):
                continue

        total_depth = bid_depth_usd + ask_depth_usd
        if total_depth == 0 or best_bid == 0:
            return None

        spread_pct = (best_ask - best_bid) / best_bid * 100
        imbalance = (bid_depth_usd - ask_depth_usd) / total_depth

        notes: List[str] = []
        if imbalance > 0.2:
            notes.append(f"عدم تعادل خریداران {imbalance*100:.1f}% - تقاضای بیشتر")
        elif imbalance < -0.2:
            notes.append(f"عدم تعادل فروشندگان {imbalance*100:.1f}% - فشار فروش")
        if spread_pct < 0.1:
            notes.append(f"اسپرد بسیار کم {spread_pct:.3f}% - لیکوییدیتی عالی")
        elif spread_pct > 1.0:
            notes.append(f"اسپرد بالا {spread_pct:.2f}% - لیکوییدیتی ضعیف")
        if total_depth > 1_000_000:
            notes.append(f"عمق کل ${total_depth/1_000_000:.2f}M - لیکوییدیتی خوب")

        return LiquidityReal(
            bid_depth_usd=bid_depth_usd,
            ask_depth_usd=ask_depth_usd,
            total_depth_usd=total_depth,
            spread_pct=spread_pct,
            imbalance=imbalance,
            best_bid=best_bid,
            best_ask=best_ask,
            is_real=True,
            source="Binance depth",
            notes=notes,
        )

    # ------------------------------------------------------------------ #
    # klines → OHLCV چندبازه‌ای
    # ------------------------------------------------------------------ #
    def get_klines(self, coin_symbol: str, interval: str = "1d",
                   limit: int = 100) -> Optional[List[List]]:
        """
        دریافت کندل‌های OHLCV از Binance.

        interval: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
        فرمت: [openTime, open, high, low, close, volume, closeTime, ...]
        """
        symbol = self._make_symbol(coin_symbol)
        if not symbol:
            return None
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        data = self._get(self.spot_url, "/api/v3/klines", params=params)
        return data if isinstance(data, list) else None

    def get_multi_timeframe_data(self, coin_symbol: str,
                                 timeframes: tuple = ("1d", "4h")) -> Dict[str, List]:
        """
        دریافت داده چند بازه زمانی برای تحلیل confluence.

        برمی‌گرداند: {timeframe: [[openTime, O, H, L, C, V, ...], ...]}
        """
        result: Dict[str, List] = {}
        for tf in timeframes:
            klines = self.get_klines(coin_symbol, interval=tf, limit=100)
            if klines:
                result[tf] = klines
            time.sleep(0.5)  # احترام به rate limit
        return result
