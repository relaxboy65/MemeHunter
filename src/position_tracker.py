"""
position_tracker.py
ردیابی پوزیشن‌های BUY و محاسبه سود/زیان واقعی - V2.5.0

این ماژال:
1. وقتی سیگنال BUY صادر می‌شود، پوزیشن ثبت می‌کند
2. در اسکن‌های بعدی، قیمت را چک می‌کند
3. وقتی سیگنال SELL صادر می‌شود یا SL/TP خورد، پوزیشن را می‌بندد
4. سود/زیان را محاسبه می‌کند
5. پیام ریپلای تلگرام را آماده می‌کند

استراتژی:
- BUY → ثبت پوزیشن (با entry_price، SL، TP)
- هر اسکن → بررسی SL/TP
- SELL یا SL/TP → بستن پوزیشن + محاسبه سود
- ارسال ریپلای به پیام BUY اصلی تلگرام
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


# فایل ذخیره پوزیشن‌های باز
POSITIONS_FILE = Path(settings.CACHE_DIR).parent / "tracked_positions.csv"

POSITION_COLUMNS = [
    "open_date", "open_timestamp", "symbol", "name",
    "entry_price", "position_size_usd", "quantity",
    "stop_loss", "take_profit", "pump_score",
    "telegram_message_id",  # برای ریپلای
    "status",  # open, closed_tp, closed_sl, closed_signal
    "close_date", "close_timestamp",
    "exit_price", "pnl_usd", "pnl_pct",
    "hold_days", "close_reason",
]


@dataclass
class TrackedPosition:
    """پوزیشن ردیابی شده."""
    open_date: str
    open_timestamp: int
    symbol: str
    name: str
    entry_price: float
    position_size_usd: float
    quantity: float
    stop_loss: float
    take_profit: float
    pump_score: float
    telegram_message_id: str = ""  # برای ریپلای
    status: str = "open"  # open, closed_tp, closed_sl, closed_signal
    close_date: str = ""
    close_timestamp: int = 0
    exit_price: float = 0.0
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    hold_days: float = 0.0
    close_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def open_tracked_position(symbol: str, name: str, entry_price: float,
                          pump_score: float, telegram_message_id: str = "",
                          position_size_usd: float = 0,
                          stop_loss_pct: float = 0.08,
                          take_profit_pct: float = 0.30) -> Optional[TrackedPosition]:
    """
    ثبت یک پوزیشن BUY جدید.
    """
    if entry_price <= 0:
        return None

    # بررسی اینکه آیا پوزیشن باز برای این نماد وجود دارد
    open_positions = get_open_tracked_positions()
    for pos in open_positions:
        if pos.symbol == symbol:
            logger.info("Position already open for %s, skipping", symbol)
            return None

    if position_size_usd <= 0:
        position_size_usd = settings.PAPER_TRADING_INITIAL_CAPITAL * settings.PAPER_TRADING_POSITION_SIZE

    quantity = position_size_usd / entry_price
    stop_loss = entry_price * (1 - stop_loss_pct)
    take_profit = entry_price * (1 + take_profit_pct)

    now = datetime.now()
    position = TrackedPosition(
        open_date=now.strftime("%Y-%m-%d %H:%M:%S"),
        open_timestamp=int(now.timestamp()),
        symbol=symbol,
        name=name,
        entry_price=entry_price,
        position_size_usd=position_size_usd,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        pump_score=pump_score,
        telegram_message_id=telegram_message_id,
    )

    _append_tracked_position(position)
    logger.info("Tracked position opened: %s @ $%.6f (SL=%.6f, TP=%.6f, msg_id=%s)",
                symbol, entry_price, stop_loss, take_profit, telegram_message_id)
    return position


def check_tracked_positions(current_prices: Dict[str, float],
                             sell_signals: Dict[str, Any] = None) -> List[TrackedPosition]:
    """
    بررسی پوزیشن‌های باز برای SL/TP یا سیگنال SELL.

    current_prices: {symbol: price}
    sell_signals: {symbol: signal_data} - نمادهایی که سیگنال SELL گرفته‌اند

    برمی‌گرداند: لیست پوزیشن‌های بسته شده
    """
    positions = _read_all_tracked_positions()
    closed: List[TrackedPosition] = []
    updated = False

    for pos in positions:
        if pos.status != "open":
            continue

        price = current_prices.get(pos.symbol)
        if price is None or price <= 0:
            continue

        exit_reason = None
        # اولویت 1: Stop Loss
        if price <= pos.stop_loss:
            exit_reason = "stop_loss"
        # اولویت 2: Take Profit
        elif price >= pos.take_profit:
            exit_reason = "take_profit"
        # اولویت 3: سیگنال SELL
        elif sell_signals and pos.symbol in sell_signals:
            exit_reason = "signal_sell"

        if exit_reason:
            now = datetime.now()
            pos.status = "closed_sl" if exit_reason == "stop_loss" else \
                         "closed_tp" if exit_reason == "take_profit" else "closed_signal"
            pos.close_date = now.strftime("%Y-%m-%d %H:%M:%S")
            pos.close_timestamp = int(now.timestamp())
            pos.exit_price = price
            pos.pnl_usd = (price - pos.entry_price) * pos.quantity
            pos.pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
            pos.hold_days = (pos.close_timestamp - pos.open_timestamp) / 86400
            pos.close_reason = exit_reason
            closed.append(pos)
            updated = True
            logger.info("Position closed: %s | PnL: %+.2f%% (%+.2f USD) | reason: %s | hold: %.1f days",
                        pos.symbol, pos.pnl_pct, pos.pnl_usd, exit_reason, pos.hold_days)

    if updated:
        _rewrite_all_tracked_positions(positions)

    return closed


def get_open_tracked_positions() -> List[TrackedPosition]:
    """دریافت پوزیشن‌های باز."""
    positions = _read_all_tracked_positions()
    return [p for p in positions if p.status == "open"]


def get_closed_tracked_positions() -> List[TrackedPosition]:
    """دریافت پوزیشن‌های بسته شده."""
    positions = _read_all_tracked_positions()
    return [p for p in positions if p.status != "open"]


def get_position_stats() -> Dict[str, Any]:
    """آمار پوزیشن‌های ردیابی شده."""
    positions = _read_all_tracked_positions()
    closed = [p for p in positions if p.status != "open"]
    open_pos = [p for p in positions if p.status == "open"]

    if not closed:
        return {
            "total_positions": len(positions),
            "open_positions": len(open_pos),
            "closed_positions": 0,
            "win_rate": 0.0,
            "total_pnl_usd": 0.0,
            "avg_pnl_pct": 0.0,
            "avg_hold_days": 0.0,
            "best_trade": None,
            "worst_trade": None,
        }

    wins = [p for p in closed if p.pnl_usd > 0]
    losses = [p for p in closed if p.pnl_usd <= 0]
    total_pnl = sum(p.pnl_usd for p in closed)
    avg_pnl = sum(p.pnl_pct for p in closed) / len(closed)
    avg_hold = sum(p.hold_days for p in closed) / len(closed)

    best = max(closed, key=lambda p: p.pnl_pct) if closed else None
    worst = min(closed, key=lambda p: p.pnl_pct) if closed else None

    return {
        "total_positions": len(positions),
        "open_positions": len(open_pos),
        "closed_positions": len(closed),
        "win_rate": len(wins) / len(closed) * 100 if closed else 0,
        "total_pnl_usd": total_pnl,
        "avg_pnl_pct": avg_pnl,
        "avg_hold_days": avg_hold,
        "best_trade": {
            "symbol": best.symbol,
            "pnl_pct": best.pnl_pct,
            "pnl_usd": best.pnl_usd,
            "hold_days": best.hold_days,
        } if best else None,
        "worst_trade": {
            "symbol": worst.symbol,
            "pnl_pct": worst.pnl_pct,
            "pnl_usd": worst.pnl_usd,
            "hold_days": worst.hold_days,
        } if worst else None,
    }


def format_close_reply(position: TrackedPosition) -> str:
    """
    قالب پیام ریپلای برای پوزیشن بسته شده.

    این پیام باید به پیام BUY اصلی ریپلای شود.
    """
    emoji = "🟢" if position.pnl_usd > 0 else "🔴"

    lines = [
        f"{emoji} نتیجه سیگنال خرید",
        f"",
        f"💰 ارز: {position.name} ({position.symbol})",
        f"📥 ورود: ${position.entry_price:.6f} ({position.open_date[:10]})",
        f"📤 خروج: ${position.exit_price:.6f} ({position.close_date[:10]})",
        f"⏱ مدت نگهداری: {position.hold_days:.1f} روز",
        f"📊 سود/زیان: {position.pnl_pct:+.2f}% (${position.pnl_usd:+.2f})",
        f"🔒 دلیل خروج: {position.close_reason}",
    ]

    if position.pnl_usd > 0:
        lines.append(f"✅ ترید موفق!")
    else:
        lines.append(f"❌ ترید ناموفق")

    return "\n".join(lines)


def format_stats_report() -> str:
    """گزارش آماری پوزیشن‌ها."""
    stats = get_position_stats()
    lines = [
        "=" * 50,
        "  📊 آمار پوزیشن‌های ردیابی شده",
        "=" * 50,
        f"  کل پوزیشن‌ها: {stats['total_positions']}",
        f"  باز: {stats['open_positions']}",
        f"  بسته شده: {stats['closed_positions']}",
        "",
    ]

    if stats['closed_positions'] > 0:
        lines.extend([
            f"  نرخ موفقیت: {stats['win_rate']:.1f}%",
            f"  کل سود/زیان: ${stats['total_pnl_usd']:+.2f}",
            f"  میانگین بازده: {stats['avg_pnl_pct']:+.2f}%",
            f"  میانگین نگهداری: {stats['avg_hold_days']:.1f} روز",
            "",
        ])

        if stats['best_trade']:
            bt = stats['best_trade']
            lines.append(f"  🟢 بهترین: {bt['symbol']} {bt['pnl_pct']:+.2f}% در {bt['hold_days']:.1f} روز")

        if stats['worst_trade']:
            wt = stats['worst_trade']
            lines.append(f"  🔴 بدترین: {wt['symbol']} {wt['pnl_pct']:+.2f}% در {wt['hold_days']:.1f} روز")

    lines.append("=" * 50)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# توابع داخلی فایل CSV
# --------------------------------------------------------------------------- #
def _read_all_tracked_positions() -> List[TrackedPosition]:
    """خواندن تمام پوزیشن‌ها از فایل."""
    if not POSITIONS_FILE.exists():
        return []
    positions: List[TrackedPosition] = []
    try:
        with POSITIONS_FILE.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pos = TrackedPosition(
                        open_date=row.get("open_date", ""),
                        open_timestamp=int(row.get("open_timestamp", 0) or 0),
                        symbol=row.get("symbol", ""),
                        name=row.get("name", ""),
                        entry_price=float(row.get("entry_price", 0) or 0),
                        position_size_usd=float(row.get("position_size_usd", 0) or 0),
                        quantity=float(row.get("quantity", 0) or 0),
                        stop_loss=float(row.get("stop_loss", 0) or 0),
                        take_profit=float(row.get("take_profit", 0) or 0),
                        pump_score=float(row.get("pump_score", 0) or 0),
                        telegram_message_id=row.get("telegram_message_id", ""),
                        status=row.get("status", "open"),
                        close_date=row.get("close_date", ""),
                        close_timestamp=int(row.get("close_timestamp", 0) or 0),
                        exit_price=float(row.get("exit_price", 0) or 0),
                        pnl_usd=float(row.get("pnl_usd", 0) or 0),
                        pnl_pct=float(row.get("pnl_pct", 0) or 0),
                        hold_days=float(row.get("hold_days", 0) or 0),
                        close_reason=row.get("close_reason", ""),
                    )
                    positions.append(pos)
                except (ValueError, TypeError) as exc:
                    logger.debug("Skip malformed position: %s", exc)
                    continue
    except OSError as exc:
        logger.warning("Error reading positions: %s", exc)
    return positions


def _append_tracked_position(pos: TrackedPosition) -> None:
    """افزودن یک پوزیشن به فایل."""
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = POSITIONS_FILE.exists()
    with POSITIONS_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POSITION_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(pos.to_dict())


def _rewrite_all_tracked_positions(positions: List[TrackedPosition]) -> None:
    """بازنویسی تمام پوزیشن‌ها."""
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with POSITIONS_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POSITION_COLUMNS)
        writer.writeheader()
        for pos in positions:
            writer.writerow(pos.to_dict())
