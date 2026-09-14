"""
paper_trading.py
ماژول Paper Trading ساده - V1.3.0.

ثبت سیگنال‌های خرید به‌صورت فرضی و ارزیابی نتیجه.
این ماژول برای تست استراتژی بدون ریسک واقعی استفاده می‌شود.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


# فایل ذخیره پوزیشن‌های paper trading
PAPER_TRADE_FILE = Path(settings.CACHE_DIR).parent / "paper_trades.csv"


@dataclass
class PaperPosition:
    """یک پوزیشن paper trading."""
    open_date: str               # YYYY-MM-DD HH:MM:SS
    open_timestamp: int
    symbol: str
    name: str
    entry_price: float
    position_size_usd: float
    quantity: float
    signal_score: float
    stop_loss: float
    take_profit: float
    status: str = "open"          # open, closed_win, closed_loss, closed_sl, closed_tp
    close_date: Optional[str] = None
    close_timestamp: Optional[int] = None
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    close_reason: Optional[str] = None   # "stop_loss", "take_profit", "manual", "time_exit"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


PAPER_TRADE_COLUMNS = [
    "open_date", "open_timestamp", "symbol", "name",
    "entry_price", "position_size_usd", "quantity",
    "signal_score", "stop_loss", "take_profit",
    "status", "close_date", "close_timestamp",
    "exit_price", "pnl_usd", "pnl_pct", "close_reason",
]


def open_position(symbol: str, name: str, entry_price: float,
                  signal_score: float,
                  position_size_usd: Optional[float] = None) -> Optional[PaperPosition]:
    """
    باز کردن یک پوزیشن فرضی.
    """
    if entry_price <= 0:
        logger.warning("Invalid entry price for %s: %s", symbol, entry_price)
        return None

    # بررسی تعداد پوزیشن‌های باز
    open_positions = get_open_positions()
    if len(open_positions) >= settings.PAPER_TRADING_MAX_POSITIONS:
        logger.info("Max positions reached (%d), skipping %s",
                    settings.PAPER_TRADING_MAX_POSITIONS, symbol)
        return None

    # بررسی اینکه آیا پوزیشن باز برای این نماد وجود دارد
    for pos in open_positions:
        if pos.symbol == symbol:
            logger.info("Position already open for %s, skipping", symbol)
            return None

    # محاسبه اندازه پوزیشن
    if position_size_usd is None:
        position_size_usd = settings.PAPER_TRADING_INITIAL_CAPITAL * settings.PAPER_TRADING_POSITION_SIZE

    quantity = position_size_usd / entry_price
    stop_loss = entry_price * (1 - settings.PAPER_TRADING_STOP_LOSS)
    take_profit = entry_price * (1 + settings.PAPER_TRADING_TAKE_PROFIT)

    now = datetime.now()
    position = PaperPosition(
        open_date=now.strftime("%Y-%m-%d %H:%M:%S"),
        open_timestamp=int(now.timestamp()),
        symbol=symbol,
        name=name,
        entry_price=entry_price,
        position_size_usd=position_size_usd,
        quantity=quantity,
        signal_score=signal_score,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    # ذخیره در فایل
    _append_position(position)
    logger.info("Paper position opened: %s @ $%.6f (size $%.2f, SL=%.4f, TP=%.4f)",
                symbol, entry_price, position_size_usd, stop_loss, take_profit)
    return position


def close_position(symbol: str, current_price: float,
                   reason: str = "manual") -> Optional[PaperPosition]:
    """
    بستن یک پوزیشن فرضی.
    """
    if current_price <= 0:
        return None

    positions = _read_all_positions()
    for pos in positions:
        if pos.symbol == symbol and pos.status == "open":
            now = datetime.now()
            pos.status = _determine_status(reason, current_price, pos)
            pos.close_date = now.strftime("%Y-%m-%d %H:%M:%S")
            pos.close_timestamp = int(now.timestamp())
            pos.exit_price = current_price
            pos.pnl_usd = (current_price - pos.entry_price) * pos.quantity
            pos.pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            pos.close_reason = reason
            _rewrite_all_positions(positions)
            logger.info("Paper position closed: %s @ $%.6f (PnL: %+.2f%%, reason: %s)",
                        symbol, current_price, pos.pnl_pct, reason)
            return pos
    return None


def check_open_positions(current_prices: Dict[str, float]) -> List[PaperPosition]:
    """
    بررسی پوزیشن‌های باز برای hit کردن SL/TP.
    current_prices: {symbol: price}
    """
    closed: List[PaperPosition] = []
    positions = _read_all_positions()
    updated = False

    for pos in positions:
        if pos.status != "open":
            continue
        price = current_prices.get(pos.symbol)
        if price is None:
            continue

        # بررسی stop loss
        if price <= pos.stop_loss:
            pos.status = "closed_sl"
            pos.close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pos.close_timestamp = int(datetime.now().timestamp())
            pos.exit_price = price
            pos.pnl_usd = (price - pos.entry_price) * pos.quantity
            pos.pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
            pos.close_reason = "stop_loss"
            closed.append(pos)
            updated = True
        # بررسی take profit
        elif price >= pos.take_profit:
            pos.status = "closed_tp"
            pos.close_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pos.close_timestamp = int(datetime.now().timestamp())
            pos.exit_price = price
            pos.pnl_usd = (price - pos.entry_price) * pos.quantity
            pos.pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
            pos.close_reason = "take_profit"
            closed.append(pos)
            updated = True

    if updated:
        _rewrite_all_positions(positions)

    return closed


def _determine_status(reason: str, current_price: float, pos: PaperPosition) -> str:
    """تعیین وضعیت بسته شدن."""
    if reason == "stop_loss":
        return "closed_sl"
    if reason == "take_profit":
        return "closed_tp"
    if current_price > pos.entry_price:
        return "closed_win"
    return "closed_loss"


def get_open_positions() -> List[PaperPosition]:
    """دریافت لیست پوزیشن‌های باز."""
    positions = _read_all_positions()
    return [p for p in positions if p.status == "open"]


def get_closed_positions() -> List[PaperPosition]:
    """دریافت لیست پوزیشن‌های بسته شده."""
    positions = _read_all_positions()
    return [p for p in positions if p.status != "open"]


def get_paper_trading_stats() -> Dict[str, Any]:
    """آمار paper trading."""
    positions = _read_all_positions()
    closed = [p for p in positions if p.status != "open"]
    open_pos = [p for p in positions if p.status == "open"]

    if not closed:
        return {
            "total_positions": 0,
            "open_positions": len(open_pos),
            "closed_positions": 0,
            "win_rate": 0.0,
            "total_pnl_usd": 0.0,
            "avg_pnl_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
        }

    wins = [p for p in closed if p.pnl_usd and p.pnl_usd > 0]
    losses = [p for p in closed if p.pnl_usd and p.pnl_usd <= 0]
    total_pnl = sum(p.pnl_usd or 0 for p in closed)
    avg_pnl = sum(p.pnl_pct or 0 for p in closed) / len(closed)
    best = max(p.pnl_pct or 0 for p in closed)
    worst = min(p.pnl_pct or 0 for p in closed)

    return {
        "total_positions": len(positions),
        "open_positions": len(open_pos),
        "closed_positions": len(closed),
        "win_rate": len(wins) / len(closed) * 100 if closed else 0.0,
        "total_pnl_usd": total_pnl,
        "avg_pnl_pct": avg_pnl,
        "best_trade_pct": best,
        "worst_trade_pct": worst,
    }


def _read_all_positions() -> List[PaperPosition]:
    """خواندن تمام پوزیشن‌ها از فایل."""
    if not PAPER_TRADE_FILE.exists():
        return []
    positions: List[PaperPosition] = []
    try:
        with PAPER_TRADE_FILE.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pos = PaperPosition(
                        open_date=row.get("open_date", ""),
                        open_timestamp=int(row.get("open_timestamp", 0)),
                        symbol=row.get("symbol", ""),
                        name=row.get("name", ""),
                        entry_price=float(row.get("entry_price", 0)),
                        position_size_usd=float(row.get("position_size_usd", 0)),
                        quantity=float(row.get("quantity", 0)),
                        signal_score=float(row.get("signal_score", 0)),
                        stop_loss=float(row.get("stop_loss", 0)),
                        take_profit=float(row.get("take_profit", 0)),
                        status=row.get("status", "open"),
                        close_date=row.get("close_date") or None,
                        close_timestamp=int(row["close_timestamp"]) if row.get("close_timestamp") else None,
                        exit_price=float(row["exit_price"]) if row.get("exit_price") else None,
                        pnl_usd=float(row["pnl_usd"]) if row.get("pnl_usd") else None,
                        pnl_pct=float(row["pnl_pct"]) if row.get("pnl_pct") else None,
                        close_reason=row.get("close_reason") or None,
                    )
                    positions.append(pos)
                except (ValueError, TypeError, KeyError) as exc:
                    logger.debug("Skip malformed paper trade row: %s", exc)
                    continue
    except OSError as exc:
        logger.warning("Error reading paper trades: %s", exc)
    return positions


def _append_position(pos: PaperPosition) -> None:
    """افزودن یک پوزیشن به فایل."""
    PAPER_TRADE_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = PAPER_TRADE_FILE.exists()
    with PAPER_TRADE_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PAPER_TRADE_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(pos.to_dict())


def _rewrite_all_positions(positions: List[PaperPosition]) -> None:
    """بازنویسی تمام پوزیشن‌ها در فایل."""
    PAPER_TRADE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PAPER_TRADE_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PAPER_TRADE_COLUMNS)
        writer.writeheader()
        for pos in positions:
            writer.writerow(pos.to_dict())


def format_paper_trading_report() -> str:
    """قالب‌بندی گزارش paper trading."""
    stats = get_paper_trading_stats()
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  گزارش Paper Trading")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  کل پوزیشن‌ها: {stats['total_positions']}")
    lines.append(f"  پوزیشن‌های باز: {stats['open_positions']}")
    lines.append(f"  پوزیشن‌های بسته: {stats['closed_positions']}")
    lines.append("")
    if stats['closed_positions'] > 0:
        lines.append(f"  نرخ موفقیت: {stats['win_rate']:.1f}%")
        lines.append(f"  کل سود/زیان: ${stats['total_pnl_usd']:+.2f}")
        lines.append(f"  میانگین بازده: {stats['avg_pnl_pct']:+.2f}%")
        lines.append(f"  بهترین ترید: {stats['best_trade_pct']:+.2f}%")
        lines.append(f"  بدترین ترید: {stats['worst_trade_pct']:+.2f}%")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
