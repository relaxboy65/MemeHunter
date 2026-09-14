"""
backtest.py
ماژول بک‌تست ساده برای بررسی عملکرد سیگنال‌های گذشته.
Simple backtest module to evaluate past signal performance.

V1.2.0 - بررسی چند درصد سیگنال‌های خرید بعد از N روز سودده بوده‌اند.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import settings
from .storage import get_db_path


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class BacktestStats:
    """آمار بک‌تست."""
    total_signals: int = 0
    total_buy: int = 0
    total_sell: int = 0
    total_hold: int = 0
    # برای سیگنال‌های BUY
    buy_win_rate_7d: float = 0.0       # درصد سودده بعد از 7 روز
    buy_win_rate_14d: float = 0.0      # درصد سودده بعد از 14 روز
    buy_avg_return_7d: float = 0.0     # میانگین بازده 7 روز
    buy_avg_return_14d: float = 0.0    # میانگین بازده 14 روز
    # V1.3.0 - تعداد نمونه و فاصله اطمینان
    buy_sample_count_7d: int = 0      # تعداد نمونه‌های قابل ارزیابی
    buy_sample_count_14d: int = 0
    buy_ci_lower_7d: float = 0.0       # بازده در فاصله اطمینان 95%
    buy_ci_upper_7d: float = 0.0
    buy_ci_lower_14d: float = 0.0
    buy_ci_upper_14d: float = 0.0
    # برای سیگنال‌های SELL
    sell_win_rate_7d: float = 0.0      # درصد درست (قیمت پایین‌تر) بعد از 7 روز
    sell_avg_return_7d: float = 0.0
    sell_sample_count_7d: int = 0      # V1.3.0
    # بهترین و بدترین سیگنال‌ها
    best_signal: Optional[Dict[str, Any]] = None
    worst_signal: Optional[Dict[str, Any]] = None


def _parse_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
    """تبدیل رکورد CSV به dict با مقادیر عددی."""
    result = {}
    for key, value in row.items():
        if value is None or value == "":
            result[key] = None
            continue
        # اعداد
        try:
            if key in ("scan_timestamp",):
                result[key] = int(value)
            elif key in ("ma_bullish", "bollinger_squeeze"):
                result[key] = value.lower() in ("true", "1", "yes")
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = float(value)
        except (ValueError, TypeError):
            result[key] = value
    return result


def _find_price_after(db_path: Path, symbol: str,
                      after_timestamp: int, days: int) -> Optional[float]:
    """
    پیدا کردن قیمت نماد N روز پس از یک تاریخ خاص.
    """
    target_ts = after_timestamp + (days * 86400)
    # بازه ±1 روز برای انعطاف
    min_ts = target_ts - 86400
    max_ts = target_ts + 86400

    if not db_path.exists():
        return None

    with db_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        candidates = []
        for row in reader:
            if row.get("symbol") != symbol:
                continue
            try:
                ts = int(row.get("scan_timestamp", 0))
                if min_ts <= ts <= max_ts:
                    price = float(row.get("current_price_usd", 0))
                    candidates.append((abs(ts - target_ts), price))
            except (ValueError, TypeError):
                continue

    if not candidates:
        return None
    # نزدیک‌ترین timestamp
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def run_backtest(days_back: int = 30, hold_days: int = 7) -> BacktestStats:
    """
    اجرای بک‌تست روی داده‌های ذخیره شده.

    days_back: بررسی سیگنال‌های N روز اخیر
    hold_days: ارزیابی عملکرد N روز پس از سیگنال
    """
    db_path = get_db_path()
    if not db_path.exists():
        logger.warning("دیتابیس CSV موجود نیست. بک‌تست اجرا نمی‌شود.")
        return BacktestStats()

    now_ts = int(datetime.now().timestamp())
    cutoff_ts = now_ts - (days_back * 86400)
    # سیگنال باید بین cutoff_ts و (now - hold_days) باشد
    # تا بتوانیم عملکرد N روز پس از آن را ارزیابی کنیم
    latest_evaluable_ts = now_ts - (hold_days * 86400)

    stats = BacktestStats()
    buy_returns_7d: List[float] = []
    buy_returns_14d: List[float] = []
    sell_returns_7d: List[float] = []
    all_records: List[Dict[str, Any]] = []

    with db_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row.get("scan_timestamp", 0))
                # سیگنال باید در محدوده قابل ارزیابی باشد
                if ts < cutoff_ts or ts > latest_evaluable_ts:
                    continue
                parsed = _parse_csv_row(row)
                parsed["_original_row"] = row
                all_records.append(parsed)
            except (ValueError, TypeError):
                continue

    stats.total_signals = len(all_records)
    stats.total_buy = sum(1 for r in all_records if r.get("signal") == "خرید")
    stats.total_sell = sum(1 for r in all_records if r.get("signal") == "فروش")
    stats.total_hold = sum(1 for r in all_records if r.get("signal") == "نگه‌داری")

    # ارزیابی سیگنال‌های BUY
    for record in all_records:
        if record.get("signal") != "خرید":
            continue
        symbol = record.get("symbol", "")
        entry_price = record.get("current_price_usd")
        entry_ts = record.get("scan_timestamp")
        if not (entry_price and entry_ts):
            continue

        # قیمت 7 روز بعد
        price_7d = _find_price_after(db_path, symbol, entry_ts, 7)
        if price_7d and entry_price > 0:
            ret = (price_7d - entry_price) / entry_price * 100
            buy_returns_7d.append(ret)
            if ret > 0:
                if not stats.best_signal or ret > stats.best_signal.get("return", -1e9):
                    stats.best_signal = {
                        "symbol": symbol,
                        "date": record.get("scan_date"),
                        "entry_price": entry_price,
                        "exit_price": price_7d,
                        "return": ret,
                        "days": 7,
                    }

        # قیمت 14 روز بعد
        price_14d = _find_price_after(db_path, symbol, entry_ts, 14)
        if price_14d and entry_price > 0:
            ret = (price_14d - entry_price) / entry_price * 100
            buy_returns_14d.append(ret)
            if ret < 0:
                if not stats.worst_signal or ret < stats.worst_signal.get("return", 1e9):
                    stats.worst_signal = {
                        "symbol": symbol,
                        "date": record.get("scan_date"),
                        "entry_price": entry_price,
                        "exit_price": price_14d,
                        "return": ret,
                        "days": 14,
                    }

    # ارزیابی سیگنال‌های SELL
    for record in all_records:
        if record.get("signal") != "فروش":
            continue
        symbol = record.get("symbol", "")
        entry_price = record.get("current_price_usd")
        entry_ts = record.get("scan_timestamp")
        if not (entry_price and entry_ts):
            continue
        price_7d = _find_price_after(db_path, symbol, entry_ts, 7)
        if price_7d and entry_price > 0:
            # برای SELL، بازده منفی یعنی قیمت پایین آمده = سیگنال درست
            ret = (price_7d - entry_price) / entry_price * 100
            sell_returns_7d.append(ret)

    # محاسبه میانگین‌ها
    if buy_returns_7d:
        stats.buy_sample_count_7d = len(buy_returns_7d)
        stats.buy_win_rate_7d = sum(1 for r in buy_returns_7d if r > 0) / len(buy_returns_7d) * 100
        stats.buy_avg_return_7d = sum(buy_returns_7d) / len(buy_returns_7d)
        # محاسبه فاصله اطمینان 95% (z=1.96)
        ci = _compute_confidence_interval(buy_returns_7d, settings.BACKTEST_CONFIDENCE_LEVEL)
        stats.buy_ci_lower_7d, stats.buy_ci_upper_7d = ci
    if buy_returns_14d:
        stats.buy_sample_count_14d = len(buy_returns_14d)
        stats.buy_win_rate_14d = sum(1 for r in buy_returns_14d if r > 0) / len(buy_returns_14d) * 100
        stats.buy_avg_return_14d = sum(buy_returns_14d) / len(buy_returns_14d)
        ci = _compute_confidence_interval(buy_returns_14d, settings.BACKTEST_CONFIDENCE_LEVEL)
        stats.buy_ci_lower_14d, stats.buy_ci_upper_14d = ci
    if sell_returns_7d:
        stats.sell_sample_count_7d = len(sell_returns_7d)
        # برای SELL، win یعنی بازده منفی
        stats.sell_win_rate_7d = sum(1 for r in sell_returns_7d if r < 0) / len(sell_returns_7d) * 100
        stats.sell_avg_return_7d = sum(sell_returns_7d) / len(sell_returns_7d)

    return stats


def _compute_confidence_interval(returns: List[float], confidence: float = 0.95) -> tuple:
    """
    محاسبه فاصله اطمینان با استفاده از توزیع نرمال.
    برمی‌گرداند: (lower, upper)
    """
    import math
    import statistics

    if len(returns) < 2:
        return (0.0, 0.0)
    try:
        mean = statistics.mean(returns)
        std = statistics.stdev(returns)
        n = len(returns)
        # z-score برای فاصله اطمینان 95% = 1.96
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence, 1.96)
        # خطای معیار = std / sqrt(n)
        sem = std / math.sqrt(n)
        margin = z * sem
        return (mean - margin, mean + margin)
    except statistics.StatisticsError:
        return (0.0, 0.0)


def format_backtest_report(stats: BacktestStats) -> str:
    """قالب‌بندی گزارش بک‌تست به متن قابل نمایش."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  گزارش عملکرد سیگنال‌های گذشته (Backtest)")
    lines.append("=" * 60)
    lines.append("")

    if stats.total_signals == 0:
        lines.append("هیچ سیگنالی برای بک‌تست موجود نیست.")
        lines.append("داده کافی در دیتابیس CSV جمع نشده است.")
        lines.append("برای داشتن داده بک‌تست، چند هفته ربات را اجرا کنید.")
        return "\n".join(lines)

    lines.append(f"  کل سیگنال‌ها: {stats.total_signals}")
    lines.append(f"  سیگنال خرید: {stats.total_buy}")
    lines.append(f"  سیگنال فروش: {stats.total_sell}")
    lines.append(f"  سیگنال نگه‌داری: {stats.total_hold}")
    lines.append("")

    if stats.total_buy > 0:
        lines.append("  --- عملکرد سیگنال‌های خرید ---")
        if stats.buy_win_rate_7d > 0 or stats.buy_sample_count_7d > 0:
            lines.append(f"  7 روز:  نرخ موفقیت {stats.buy_win_rate_7d:.1f}% "
                        f"({stats.buy_sample_count_7d} نمونه) | "
                        f"میانگین بازده {stats.buy_avg_return_7d:+.2f}%")
            if stats.buy_sample_count_7d > 1:
                lines.append(f"         فاصله اطمینان 95%: "
                            f"[{stats.buy_ci_lower_7d:+.2f}%, {stats.buy_ci_upper_7d:+.2f}%]")
        if stats.buy_win_rate_14d > 0 or stats.buy_sample_count_14d > 0:
            lines.append(f"  14 روز: نرخ موفقیت {stats.buy_win_rate_14d:.1f}% "
                        f"({stats.buy_sample_count_14d} نمونه) | "
                        f"میانگین بازده {stats.buy_avg_return_14d:+.2f}%")
            if stats.buy_sample_count_14d > 1:
                lines.append(f"         فاصله اطمینان 95%: "
                            f"[{stats.buy_ci_lower_14d:+.2f}%, {stats.buy_ci_upper_14d:+.2f}%]")
        lines.append("")

    if stats.total_sell > 0:
        lines.append("  --- عملکرد سیگنال‌های فروش ---")
        if stats.sell_win_rate_7d > 0 or stats.sell_sample_count_7d > 0:
            lines.append(f"  7 روز:  نرخ موفقیت {stats.sell_win_rate_7d:.1f}% "
                        f"({stats.sell_sample_count_7d} نمونه) | "
                        f"میانگین بازده {stats.sell_avg_return_7d:+.2f}%")
        lines.append("")

    if stats.best_signal:
        lines.append("  --- بهترین سیگنال ---")
        lines.append(f"  {stats.best_signal['symbol']} در {stats.best_signal['date']}")
        lines.append(f"  ورود: ${stats.best_signal['entry_price']:.6f}")
        lines.append(f"  خروج: ${stats.best_signal['exit_price']:.6f}")
        lines.append(f"  بازده: {stats.best_signal['return']:+.2f}% در {stats.best_signal['days']} روز")
        lines.append("")

    if stats.worst_signal:
        lines.append("  --- بدترین سیگنال ---")
        lines.append(f"  {stats.worst_signal['symbol']} در {stats.worst_signal['date']}")
        lines.append(f"  ورود: ${stats.worst_signal['entry_price']:.6f}")
        lines.append(f"  خروج: ${stats.worst_signal['exit_price']:.6f}")
        lines.append(f"  بازده: {stats.worst_signal['return']:+.2f}% در {stats.worst_signal['days']} روز")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
