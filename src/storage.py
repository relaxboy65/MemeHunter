"""
storage.py
مدیریت دیتابیس CSV برای ذخیره میم‌کوین‌های روزانه.
- فایل اصلی: data/coins_database.csv
- هر روز یک رکورد به ازای هر کوین اضافه می‌شود
- نگهداری: 90 روز (طبق قانون پروژه)
"""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import AnalysisResult, Signal


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# فایل دیتابیس CSV اصلی
DB_FILE = DATA_DIR / "coins_database.csv"

# نگهداری 90 روز (طبق قانون پروژه)
DB_RETENTION_DAYS = 90

# ستون‌های دیتابیس
DB_COLUMNS = [
    "scan_date",            # YYYY-MM-DD HH:MM:SS
    "scan_timestamp",       # epoch
    "coin_id",
    "symbol",
    "name",
    "current_price_usd",
    "market_cap_usd",
    "volume_24h_usd",
    "change_24h_pct",
    "change_7d_pct",
    "rsi",
    "macd_hist",
    "ma_short",
    "ma_long",
    "ma_bullish",
    "volume_surge_ratio",
    "price_momentum_pct",
    "score",
    "signal",
    "confidence",
    # V1.1.0 - اندیکاتورهای جدید
    "atr",
    "atr_percent",
    "bollinger_percent_b",
    "bollinger_squeeze",
    # V1.3.0 - فیلدهای کلیدی پیشرفته
    "liquidity_score",
    "liquidity_is_real",         # True = داده واقعی Binance, False = پروکسی
    "liquidity_spread",
    "liquidity_imbalance",
    "sweep_detected",
    "sweep_type",
    "orderflow_buy_pressure",
    "orderflow_sell_pressure",
    "orderflow_is_real",
    "large_swap_count",          # تعداد تریدهای بزرگ (smart money proxy)
    "large_buys",
    "large_sells",
    "mtf_confluence_score",
    "mtf_aligned_count",
    "data_sources",              # خلاصه منابع داده (مثل "2 واقعی + 2 پروکسی")
]


def ensure_db_file() -> None:
    """اگر فایل دیتابیس وجود نداشت، آن را با هدر ایجاد می‌کند."""
    if not DB_FILE.exists():
        with DB_FILE.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(DB_COLUMNS)


def save_results_to_db(results: List[AnalysisResult]) -> int:
    """
    ذخیره نتایج اسکن در دیتابیس CSV داخل data/coins_database.csv
    با تاریخ (scan_date / scan_timestamp). نگهداری ۹۰ روز.
    برمی‌گرداند: تعداد رکوردهای ذخیره‌شده.
    """
    import logging
    log = logging.getLogger("memehunter")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ensure_db_file()
    now = datetime.now()
    timestamp = int(now.timestamp())

    rows: List[List[Any]] = []
    for r in results:
        ind = r.indicators or {}
        adv = getattr(r, "advanced", None) or {}
        rows.append([
            now.strftime("%Y-%m-%d %H:%M:%S"),
            timestamp,
            r.coin_id,
            r.symbol,
            r.name,
            round(r.current_price, 8),
            round(r.market_cap, 0),
            round(r.volume_24h, 0),
            round(r.change_24h_pct, 4),
            round(r.change_7d_pct, 4),
            ind.get("rsi"),
            ind.get("macd_hist"),
            ind.get("ma_short"),
            ind.get("ma_long"),
            ind.get("ma_bullish"),
            ind.get("volume_surge_ratio"),
            ind.get("price_momentum_pct"),
            round(r.score, 4),
            r.signal.value if hasattr(r.signal, "value") else str(r.signal),
            round(r.confidence, 4),
            ind.get("atr"),
            ind.get("atr_percent"),
            ind.get("bollinger_percent_b"),
            ind.get("bollinger_squeeze"),
            adv.get("liquidity_score"),
            adv.get("liquidity_is_real"),
            adv.get("spread_estimate"),
            adv.get("liquidity_imbalance"),
            adv.get("sweep_detected"),
            adv.get("sweep_type"),
            adv.get("buy_pressure"),
            adv.get("sell_pressure"),
            adv.get("orderflow_is_real"),
            adv.get("large_trades_count"),
            adv.get("large_buys"),
            adv.get("large_sells"),
            adv.get("mtf_confluence_score"),
            adv.get("mtf_aligned_count"),
            getattr(r, "data_sources", "") or "",
        ])

    if not rows:
        log.warning("save_results_to_db: هیچ ردیفی برای ذخیره نبود")
        return 0

    abs_path = DB_FILE.resolve()
    with DB_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        f.flush()

    # تأیید ذخیره واقعی روی دیسک
    if not DB_FILE.exists():
        raise OSError(f"فایل دیتابیس پس از نوشتن وجود ندارد: {abs_path}")
    size = DB_FILE.stat().st_size
    log.info(
        "DATA_SAVE_OK: %d رکورد → %s (size=%d bytes)",
        len(rows), abs_path, size,
    )
    # نشانگر آخرین ذخیره
    marker = DATA_DIR / ".last_save"
    marker.write_text(
        f"{now.isoformat()}|coins_database.csv|{len(rows)}|{abs_path}\n",
        encoding="utf-8",
    )
    return len(rows)


def cleanup_old_db_records() -> int:
    """
    حذف رکوردهای قدیمی‌تر از 90 روز از دیتابیس CSV.
    برمی‌گرداند: تعداد رکوردهای حذف‌شده.
    """
    if not DB_FILE.exists():
        return 0

    cutoff = time.time() - (DB_RETENTION_DAYS * 86400)

    with DB_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        kept: List[Dict[str, Any]] = []
        deleted = 0
        for row in reader:
            try:
                ts = int(row.get("scan_timestamp", 0))
                if ts >= cutoff:
                    kept.append(row)
                else:
                    deleted += 1
            except (ValueError, TypeError):
                kept.append(row)  # در صورت خطا، رکورد را نگه دار

    # بازنویسی فایل فقط در صورتی که رکوردی حذف شده باشد
    if deleted > 0:
        with DB_FILE.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DB_COLUMNS)
            writer.writeheader()
            writer.writerows(kept)

    return deleted


def read_recent_records(days: int = 7) -> List[Dict[str, Any]]:
    """
    خواندن رکوردهای N روز اخیر از دیتابیس.
    """
    if not DB_FILE.exists():
        return []
    cutoff = time.time() - (days * 86400)
    rows: List[Dict[str, Any]] = []
    with DB_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row.get("scan_timestamp", 0))
                if ts >= cutoff:
                    rows.append(row)
            except (ValueError, TypeError):
                continue
    return rows


def get_db_path() -> Path:
    """بازگرداندن مسیر فایل دیتابیس."""
    return DB_FILE


def get_db_stats() -> Dict[str, Any]:
    """آمار دیتابیس: تعداد رکوردها، تاریخ اولین و آخرین اسکن."""
    if not DB_FILE.exists():
        return {
            "total_records": 0,
            "first_scan": None,
            "last_scan": None,
            "unique_coins": 0,
        }
    with DB_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return {
            "total_records": 0,
            "first_scan": None,
            "last_scan": None,
            "unique_coins": 0,
        }
    dates = [r.get("scan_date", "") for r in rows]
    coins = {r.get("symbol", "") for r in rows}
    return {
        "total_records": len(rows),
        "first_scan": min(dates),
        "last_scan": max(dates),
        "unique_coins": len(coins),
    }
