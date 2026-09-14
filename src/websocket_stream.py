"""
websocket_stream.py
پشتیبانی اختیاری از WebSocket برای داده real-time - V1.3.1.

این ماژول به‌صورت اختیاری فعال می‌شود و برای کوین‌های منتخب (مثل PEPE، WIF)
داده‌های real-time دریافت می‌کند:
- aggTrade: تریدهای لحظه‌ای برای CVD real-time
- depth20: آپدیت order book هر 100ms

توجه: این ماژول به کتابخانه websocket-client نیاز دارد.
نصب: pip install websocket-client

اگر نصب نباشد، ماژول به‌صورت خودکار غیرفعال می‌شود.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


# تلاش برای import کتابخانه websocket
try:
    import websocket  # type: ignore
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.info("websocket-client نصب نیست. WebSocket غیرفعال است. "
                "نصب: pip install websocket-client")


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass
class RealtimeStats:
    """آمار real-time یک کوین."""
    symbol: str
    cvd_realtime: float = 0.0           # CVD لحظه‌ای
    buy_volume_realtime: float = 0.0
    sell_volume_realtime: float = 0.0
    trade_count: int = 0
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread_pct: Optional[float] = None
    last_price: Optional[float] = None
    last_update: Optional[float] = None  # timestamp


# --------------------------------------------------------------------------- #
# WebSocket Manager
# --------------------------------------------------------------------------- #
class BinanceWebSocketManager:
    """
    مدیریت WebSocketهای real-time Binance - V1.3.1.

    برای کوین‌های منتخب، اتصال WebSocket برقرار می‌کند و
    داده‌های real-time دریافت می‌کند.
    """

    BASE_URL = "wss://stream.binance.com:9443/ws"

    def __init__(self) -> None:
        if not WEBSOCKET_AVAILABLE:
            raise ImportError(
                "websocket-client نصب نیست. نصب: pip install websocket-client"
            )
        self._streams: Dict[str, websocket.WebSocketApp] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stats: Dict[str, RealtimeStats] = {}
        self._running = False

    def _make_symbol_lower(self, symbol: str) -> str:
        """تبدیل SYMBOL به symbol (حروف کوچک)."""
        s = symbol.upper()
        if s.endswith("USDT"):
            return s[:-4].lower() + "usdt"
        return s.lower() + "usdt"

    def start_coin_stream(self, coin_symbol: str) -> bool:
        """
        شروع اتصال WebSocket برای یک کوین.
        شامل: aggTrade + depth20@100ms
        """
        if not WEBSOCKET_AVAILABLE:
            return False

        sym_lower = self._make_symbol_lower(coin_symbol)
        if sym_lower in self._streams:
            logger.info("Stream already running for %s", coin_symbol)
            return True

        # ساخت URL ترکیبی
        stream_url = (
            f"{self.BASE_URL}/{sym_lower}@aggTrade/{sym_lower}@depth20@100ms"
        )

        # آمار اولیه
        self._stats[sym_lower] = RealtimeStats(symbol=coin_symbol)

        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._process_message(sym_lower, data)
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.debug("WebSocket message error: %s", exc)

        def on_error(ws, error):
            logger.warning("WebSocket error for %s: %s", coin_symbol, error)

        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket closed for %s", coin_symbol)

        def on_open(ws):
            logger.info("WebSocket opened for %s", coin_symbol)

        ws = websocket.WebSocketApp(
            stream_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )

        # اجرا در thread جداگانه
        thread = threading.Thread(target=ws.run_forever, daemon=True)
        thread.start()

        self._streams[sym_lower] = ws
        self._threads[sym_lower] = thread
        self._running = True

        logger.info("Started WebSocket stream for %s", coin_symbol)
        return True

    def stop_coin_stream(self, coin_symbol: str) -> None:
        """توقف اتصال WebSocket یک کوین."""
        sym_lower = self._make_symbol_lower(coin_symbol)
        ws = self._streams.pop(sym_lower, None)
        if ws:
            ws.close()
        self._threads.pop(sym_lower, None)
        self._stats.pop(sym_lower, None)
        logger.info("Stopped WebSocket stream for %s", coin_symbol)

    def stop_all(self) -> None:
        """توقف تمام اتصال‌ها."""
        for symbol in list(self._streams.keys()):
            try:
                self._streams[symbol].close()
            except Exception:
                pass
        self._streams.clear()
        self._threads.clear()
        self._stats.clear()
        self._running = False

    def _process_message(self, sym_lower: str, data: dict) -> None:
        """پردازش پیام دریافتی از WebSocket."""
        stats = self._stats.get(sym_lower)
        if not stats:
            return

        # تشخیص نوع stream
        event_type = data.get("e") or data.get("stream", "")
        current_time = time.time()

        if "aggTrade" in str(event_type):
            # aggTrade event
            try:
                price = float(data.get("p", 0))
                qty = float(data.get("q", 0))
                is_buyer_maker = data.get("m", False)

                if is_buyer_maker:
                    # m=True یعنی خریدار maker → فروشنده تهاجمی → SELL
                    stats.sell_volume_realtime += qty
                    stats.cvd_realtime -= qty
                else:
                    # m=False یعنی خریدار تهاجمی → BUY
                    stats.buy_volume_realtime += qty
                    stats.cvd_realtime += qty

                stats.trade_count += 1
                stats.last_price = price
                stats.last_update = current_time
            except (ValueError, TypeError):
                pass

        elif "depth" in str(event_type) or "bids" in data or "asks" in data:
            # depth event
            try:
                bids = data.get("bids") or data.get("b", [])
                asks = data.get("asks") or data.get("a", [])
                if bids and asks:
                    stats.best_bid = float(bids[0][0])
                    stats.best_ask = float(asks[0][0])
                    if stats.best_bid > 0:
                        stats.spread_pct = (
                            (stats.best_ask - stats.best_bid) / stats.best_bid * 100
                        )
                    stats.last_update = current_time
            except (ValueError, IndexError, TypeError):
                pass

    def get_realtime_stats(self, coin_symbol: str) -> Optional[RealtimeStats]:
        """دریافت آمار real-time یک کوین."""
        sym_lower = self._make_symbol_lower(coin_symbol)
        return self._stats.get(sym_lower)

    def is_stream_active(self, coin_symbol: str) -> bool:
        """بررسی فعال بودن stream یک کوین."""
        sym_lower = self._make_symbol_lower(coin_symbol)
        return sym_lower in self._streams

    def get_active_streams(self) -> List[str]:
        """دریافت لیست کوین‌های دارای stream فعال."""
        return [stats.symbol for stats in self._stats.values()]


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def is_websocket_available() -> bool:
    """بررسی نصب بودن کتابخانه websocket-client."""
    return WEBSOCKET_AVAILABLE


def get_realtime_summary(coin_symbol: str,
                         ws_manager: Optional[BinanceWebSocketManager]) -> Optional[dict]:
    """
    دریافت خلاصه real-time برای نمایش در خروجی.
    """
    if not ws_manager:
        return None
    stats = ws_manager.get_realtime_stats(coin_symbol)
    if not stats or not stats.last_update:
        return None

    # بررسی freshness (آخرین آپدیت کمتر از 30 ثانیه پیش باشد)
    if time.time() - stats.last_update > 30:
        return None

    return {
        "symbol": stats.symbol,
        "last_price": stats.last_price,
        "cvd_realtime": round(stats.cvd_realtime, 4),
        "buy_volume": round(stats.buy_volume_realtime, 4),
        "sell_volume": round(stats.sell_volume_realtime, 4),
        "trade_count": stats.trade_count,
        "spread_pct": round(stats.spread_pct, 3) if stats.spread_pct else None,
        "is_realtime": True,
    }
