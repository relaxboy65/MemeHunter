"""
logging_setup.py
راه‌اندازی لاگ‌نویسی با فایل چرخشی 90 روزه + لاگ ساختاریافته - V1.3.1.

V1.3.1 - اضافه شدن:
  - لاگ PHASE برای هر مرحله از اجرا
  - آمار جداگانه هر API (CoinGecko، Binance، ...)
  - لیست خطاها در خلاصه نهایی
  - شمارش داده واقعی vs پروکسی
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional


# مسیر پوشه data
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA_DIR / "activity.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_RETENTION_DAYS = 90


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """راه‌اندازی لاگر اصلی پروژه."""
    logger = logging.getLogger()
    logger.setLevel(level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # handler فایل: چرخشی روزانه با نگهداری 90 روز
    file_handler = TimedRotatingFileHandler(
        filename=str(LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
        utc=False,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # handler کنسول
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # کاهش پر‌حرفی کتابخانه‌های خارجی
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    return logger


def cleanup_old_logs() -> int:
    """پاکسازی فایل‌های لاگ قدیمی‌تر از 90 روز."""
    import time
    deleted = 0
    cutoff = time.time() - (LOG_RETENTION_DAYS * 86400)
    for f in DATA_DIR.glob("activity.log*"):
        try:
            mtime = f.stat().st_mtime
            if mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


def get_log_path() -> Path:
    """بازگرداندن مسیر فایل لاگ فعلی."""
    return LOG_FILE


# --------------------------------------------------------------------------- #
# V1.3.1 - لاگ ساختاریافته (PHASE + آمار + خطاها)
# --------------------------------------------------------------------------- #
# آمار اجرای فعلی (سراسری)
_run_stats: Dict[str, Any] = {
    "phases": [],                # لیست فازها با زمان شروع/پایان
    "api_stats": defaultdict(lambda: {"calls": 0, "success": 0, "failed": 0, "cached": 0}),
    "errors": [],                # لیست خطاها
    "coins_real_data": 0,        # تعداد کوین‌های با داده واقعی
    "coins_proxy_only": 0,       # تعداد کوین‌های فقط پروکسی
    "current_phase": None,
    "phase_start_time": None,
}


def start_phase(phase_name: str) -> None:
    """
    شروع یک فاز از اجرا.
    phase_name: نام فاز مثل "fetch_candidates", "analyze_coins", "binance_data"
    """
    logger = logging.getLogger("memehunter")
    _run_stats["current_phase"] = phase_name
    _run_stats["phase_start_time"] = datetime.now().isoformat()

    logger.info(f"PHASE_START: {phase_name}")
    entry = {
        "type": "phase_start",
        "phase": phase_name,
        "timestamp": _run_stats["phase_start_time"],
    }
    try:
        json_line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"PHASE_JSON: {json_line}")
    except (TypeError, ValueError):
        pass


def end_phase(phase_name: str, summary: Optional[Dict[str, Any]] = None) -> None:
    """
    پایان یک فاز.
    """
    logger = logging.getLogger("memehunter")
    end_time = datetime.now().isoformat()

    phase_info = {
        "phase": phase_name,
        "start": _run_stats["phase_start_time"],
        "end": end_time,
        "summary": summary or {},
    }
    _run_stats["phases"].append(phase_info)
    _run_stats["current_phase"] = None
    _run_stats["phase_start_time"] = None

    logger.info(f"PHASE_END: {phase_name}")
    entry = {
        "type": "phase_end",
        "phase": phase_name,
        "end_timestamp": end_time,
        "summary": summary or {},
    }
    try:
        json_line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"PHASE_JSON: {json_line}")
    except (TypeError, ValueError):
        pass


def record_api_call(source: str, status: str, detail: str = "") -> None:
    """
    ثبت یک درخواست API.
    source: 'coingecko', 'binance', 'dexscreener', 'geckoterminal'
    status: 'success', 'failed', 'cached', 'rate_limited', 'skipped'
    """
    logger = logging.getLogger("memehunter")
    _run_stats["api_stats"][source][status] += 1
    _run_stats["api_stats"][source]["calls"] += 1

    entry = {
        "type": "api_call",
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "status": status,
        "detail": detail,
    }
    try:
        json_line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"API_CALL_JSON: {json_line}")
    except (TypeError, ValueError):
        logger.info(f"API {source}: {status} - {detail}")


def record_error(source: str, error: str, context: str = "") -> None:
    """
    ثبت یک خطا برای خلاصه نهایی.
    """
    error_entry = {
        "source": source,
        "error": error,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }
    _run_stats["errors"].append(error_entry)

    logger = logging.getLogger("memehunter")
    logger.error(f"ERROR_RECORDED: [{source}] {error} ({context})")


def record_data_source(is_real: bool) -> None:
    """
    ثبت منبع داده یک کوین (واقعی یا پروکسی).
    """
    if is_real:
        _run_stats["coins_real_data"] += 1
    else:
        _run_stats["coins_proxy_only"] += 1


def get_run_summary() -> Dict[str, Any]:
    """دریافت خلاصه کامل اجرا."""
    # تبدیل defaultdict به dict معمولی
    api_stats_dict = {k: dict(v) for k, v in _run_stats["api_stats"].items()}
    return {
        "phases": _run_stats["phases"],
        "api_stats": api_stats_dict,
        "errors": _run_stats["errors"],
        "coins_real_data": _run_stats["coins_real_data"],
        "coins_proxy_only": _run_stats["coins_proxy_only"],
        "total_errors": len(_run_stats["errors"]),
    }


def log_run_summary(extra_stats: Optional[Dict[str, Any]] = None) -> None:
    """
    ثبت خلاصه اجرا به‌صورت JSON در انتهای هر run - V1.3.1 کامل‌تر.
    """
    logger = logging.getLogger("memehunter")

    summary = get_run_summary()
    if "timestamp" not in summary:
        summary["timestamp"] = datetime.now().isoformat()
    if "version" not in summary:
        from .config import PROJECT_VERSION
        summary["version"] = PROJECT_VERSION

    # اضافه کردن آمار اضافی
    if extra_stats:
        summary.update(extra_stats)

    # ساخت رشته JSON فشرده
    try:
        json_line = json.dumps(summary, ensure_ascii=False, separators=(",", ":"), default=str)
        logger.info(f"RUN_SUMMARY_JSON: {json_line}")
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to serialize run summary: %s", exc)


def log_coin_analysis(coin_symbol: str, coin_id: str, signal: str,
                      score: float, data_sources: str = "",
                      is_real_data: bool = False) -> None:
    """
    ثبت تحلیل یک کوین به‌صورت JSON.
    """
    # ثبت منبع داده
    record_data_source(is_real_data)

    logger = logging.getLogger("memehunter")
    entry = {
        "type": "coin_analysis",
        "timestamp": datetime.now().isoformat(),
        "symbol": coin_symbol,
        "coin_id": coin_id,
        "signal": signal,
        "score": round(score, 4),
        "data_sources": data_sources,
        "is_real_data": is_real_data,
    }
    try:
        json_line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        logger.info(f"COIN_ANALYSIS_JSON: {json_line}")
    except (TypeError, ValueError):
        logger.info(f"Analyzed {coin_symbol}: signal={signal}, score={score:.3f}")


def reset_run_stats() -> None:
    """ریست آمار اجرا (برای تست‌ها)."""
    global _run_stats
    _run_stats = {
        "phases": [],
        "api_stats": defaultdict(lambda: {"calls": 0, "success": 0, "failed": 0, "cached": 0}),
        "errors": [],
        "coins_real_data": 0,
        "coins_proxy_only": 0,
        "current_phase": None,
        "phase_start_time": None,
    }


# نگه‌داری توابع قدیمی برای سازگاری
def log_data_source(source: str, status: str, detail: str = "") -> None:
    """ثبت وضعیت منبع داده (alias برای record_api_call)."""
    record_api_call(source, status, detail)
