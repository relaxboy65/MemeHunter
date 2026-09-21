"""
logging_setup.py — MemeHunter V1.5.0
لاگ چرخشی ۹۰ روزه + لاگ ساختاریافته مخصوص GitHub Actions.

علامت‌های قابل‌جستجو در Actions:
  MH_RUN_START / MH_RUN_END
  PHASE_START / PHASE_END / PHASE_JSON
  API_CALL_JSON
  COIN_ANALYSIS_JSON
  ERROR_RECORDED
  DATA_SAVE_OK
  RUN_SUMMARY_JSON
  RUN_REPORT   (بلوک متنی خوانا)
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA_DIR / "activity.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_RETENTION_DAYS = 90


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(level)
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

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

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    return logger


def cleanup_old_logs() -> int:
    import time
    deleted = 0
    cutoff = time.time() - (LOG_RETENTION_DAYS * 86400)
    for f in DATA_DIR.glob("activity.log*"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


def get_log_path() -> Path:
    return LOG_FILE


# --------------------------------------------------------------------------- #
# آمار اجرا
# --------------------------------------------------------------------------- #
_run_stats: Dict[str, Any] = {
    "phases": [],
    "api_stats": defaultdict(lambda: defaultdict(int)),
    "errors": [],
    "coins_real_data": 0,
    "coins_proxy_only": 0,
    "current_phase": None,
    "phase_start_time": None,
    "run_started_at": None,
    "coins": [],  # خلاصه هر کوین برای گزارش نهایی
}


def reset_run_stats() -> None:
    global _run_stats
    _run_stats = {
        "phases": [],
        "api_stats": defaultdict(lambda: defaultdict(int)),
        "errors": [],
        "coins_real_data": 0,
        "coins_proxy_only": 0,
        "current_phase": None,
        "phase_start_time": None,
        "run_started_at": None,
        "coins": [],
    }


def log_run_start(version: str, limit: int = 0, flags: Optional[Dict[str, Any]] = None) -> None:
    """شروع اجرا — علامت واضح برای Actions."""
    logger = logging.getLogger("memehunter")
    _run_stats["run_started_at"] = datetime.now().isoformat()
    flags = flags or {}
    banner = {
        "type": "run_start",
        "version": version,
        "limit": limit,
        "flags": flags,
        "timestamp": _run_stats["run_started_at"],
    }
    logger.info("=" * 72)
    logger.info("MH_RUN_START version=%s limit=%s", version, limit)
    logger.info("MH_RUN_START_JSON: %s", json.dumps(banner, ensure_ascii=False, separators=(",", ":")))
    logger.info("=" * 72)


def start_phase(phase_name: str) -> None:
    logger = logging.getLogger("memehunter")
    _run_stats["current_phase"] = phase_name
    _run_stats["phase_start_time"] = datetime.now().isoformat()
    logger.info("PHASE_START: %s", phase_name)
    entry = {
        "type": "phase_start",
        "phase": phase_name,
        "timestamp": _run_stats["phase_start_time"],
    }
    try:
        logger.info("PHASE_JSON: %s", json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        pass


def end_phase(phase_name: str, summary: Optional[Dict[str, Any]] = None) -> None:
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
    logger.info("PHASE_END: %s", phase_name)
    entry = {
        "type": "phase_end",
        "phase": phase_name,
        "end_timestamp": end_time,
        "summary": summary or {},
    }
    try:
        logger.info("PHASE_JSON: %s", json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        pass


def record_api_call(source: str, status: str, detail: str = "", quiet: bool = False) -> None:
    """
    ثبت API.
    quiet=True: فقط در آمار جمع می‌شود، خط JSON جدا چاپ نمی‌شود (کاهش نویز Actions).
    """
    logger = logging.getLogger("memehunter")
    _run_stats["api_stats"][source][status] += 1
    _run_stats["api_stats"][source]["calls"] += 1
    if quiet and status == "success":
        return
    entry = {
        "type": "api_call",
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "status": status,
        "detail": detail,
    }
    try:
        logger.info("API_CALL_JSON: %s", json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        logger.info("API %s: %s - %s", source, status, detail)


def record_error(source: str, error: str, context: str = "") -> None:
    error_entry = {
        "source": source,
        "error": str(error)[:300],
        "context": context,
        "timestamp": datetime.now().isoformat(),
    }
    _run_stats["errors"].append(error_entry)
    logger = logging.getLogger("memehunter")
    logger.error("ERROR_RECORDED: [%s] %s (%s)", source, error, context)


def record_data_source(is_real: bool) -> None:
    if is_real:
        _run_stats["coins_real_data"] += 1
    else:
        _run_stats["coins_proxy_only"] += 1


def get_run_summary() -> Dict[str, Any]:
    api_stats_dict = {k: dict(v) for k, v in _run_stats["api_stats"].items()}
    return {
        "phases": _run_stats["phases"],
        "api_stats": api_stats_dict,
        "errors": _run_stats["errors"],
        "coins_real_data": _run_stats["coins_real_data"],
        "coins_proxy_only": _run_stats["coins_proxy_only"],
        "total_errors": len(_run_stats["errors"]),
        "coins": _run_stats["coins"],
        "run_started_at": _run_stats["run_started_at"],
    }


def log_coin_analysis(
    coin_symbol: str,
    coin_id: str,
    signal: str,
    score: float,
    data_sources: str = "",
    is_real_data: bool = False,
    telegram_message_id: Any = None,
) -> None:
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
        "telegram_message_id": telegram_message_id,
    }
    _run_stats["coins"].append(entry)
    try:
        logger.info("COIN_ANALYSIS_JSON: %s", json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        logger.info("Analyzed %s: signal=%s score=%.3f", coin_symbol, signal, score)


def log_run_summary(extra_stats: Optional[Dict[str, Any]] = None) -> None:
    logger = logging.getLogger("memehunter")
    summary = get_run_summary()
    summary["timestamp"] = datetime.now().isoformat()
    try:
        from .config import PROJECT_VERSION
        summary["version"] = PROJECT_VERSION
    except Exception:
        summary["version"] = "unknown"
    if extra_stats:
        summary.update(extra_stats)

    # JSON فشرده برای grep
    try:
        json_line = json.dumps(summary, ensure_ascii=False, separators=(",", ":"), default=str)
        logger.info("RUN_SUMMARY_JSON: %s", json_line)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to serialize run summary: %s", exc)

    # بلوک خوانا برای چشم انسان در Actions
    buy = extra_stats.get("buy_count", 0) if extra_stats else 0
    sell = extra_stats.get("sell_count", 0) if extra_stats else 0
    hold = extra_stats.get("hold_count", 0) if extra_stats else 0
    total = extra_stats.get("total_coins", len(_run_stats["coins"])) if extra_stats else len(_run_stats["coins"])
    duration = extra_stats.get("duration_seconds") if extra_stats else None
    lines = [
        "========== RUN_REPORT ==========",
        f"version={summary.get('version')}  total={total}  BUY={buy} SELL={sell} HOLD={hold}",
        f"real_data={_run_stats['coins_real_data']}  proxy_only={_run_stats['coins_proxy_only']}  errors={len(_run_stats['errors'])}",
    ]
    if duration is not None:
        lines.append(f"duration_seconds={duration:.1f}")
    # API یک‌خطی
    api_parts = []
    for src, st in summary.get("api_stats", {}).items():
        ok = st.get("success", 0)
        fail = st.get("failed", 0)
        rl = st.get("rate_limited", 0)
        api_parts.append(f"{src}:ok={ok}/fail={fail}/rl={rl}")
    if api_parts:
        lines.append("api | " + " | ".join(api_parts))
    # کوین‌ها
    for c in _run_stats["coins"]:
        mid = c.get("telegram_message_id") or "-"
        lines.append(
            f"  {c.get('symbol')}: {c.get('signal')} score={c.get('score')} "
            f"real={c.get('is_real_data')} tg_id={mid}"
        )
    if _run_stats["errors"]:
        lines.append("--- errors ---")
        for e in _run_stats["errors"][:10]:
            lines.append(f"  [{e.get('source')}] {e.get('error')}")
    lines.append("======== END RUN_REPORT ========")
    for line in lines:
        logger.info("%s", line)

    logger.info("=" * 72)
    logger.info("MH_RUN_END version=%s total=%s buy=%s sell=%s hold=%s",
                summary.get("version"), total, buy, sell, hold)
    logger.info("=" * 72)

    # GitHub Step Summary (در Actions در UI بالای job دیده می‌شود)
    write_github_step_summary(summary, extra_stats or {})


def write_github_step_summary(summary: Dict[str, Any], extra: Dict[str, Any]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        buy = extra.get("buy_count", 0)
        sell = extra.get("sell_count", 0)
        hold = extra.get("hold_count", 0)
        total = extra.get("total_coins", len(_run_stats["coins"]))
        duration = extra.get("duration_seconds")
        md: List[str] = []
        md.append(f"## 🐸 MemeHunter {summary.get('version', '')}")
        md.append("")
        md.append("| شاخص | مقدار |")
        md.append("|------|-------|")
        md.append(f"| کل کوین | **{total}** |")
        md.append(f"| 🟢 BUY | {buy} |")
        md.append(f"| 🔴 SELL | {sell} |")
        md.append(f"| 🟡 HOLD | {hold} |")
        md.append(f"| داده واقعی | {_run_stats['coins_real_data']} |")
        md.append(f"| فقط پروکسی | {_run_stats['coins_proxy_only']} |")
        md.append(f"| خطاها | {len(_run_stats['errors'])} |")
        if duration is not None:
            md.append(f"| مدت (ثانیه) | {duration:.1f} |")
        md.append("")
        if _run_stats["coins"]:
            md.append("### نتایج")
            md.append("| نماد | سیگنال | امتیاز | واقعی | tg_id |")
            md.append("|------|--------|--------|-------|-------|")
            for c in _run_stats["coins"]:
                md.append(
                    f"| {c.get('symbol')} | {c.get('signal')} | {c.get('score')} | "
                    f"{'✅' if c.get('is_real_data') else '❌'} | {c.get('telegram_message_id') or '-'} |"
                )
            md.append("")
        if summary.get("api_stats"):
            md.append("### API")
            md.append("| منبع | موفق | ناموفق | rate_limit |")
            md.append("|------|------|--------|------------|")
            for src, st in summary["api_stats"].items():
                md.append(
                    f"| {src} | {st.get('success', 0)} | {st.get('failed', 0)} | {st.get('rate_limited', 0)} |"
                )
            md.append("")
        if _run_stats["errors"]:
            md.append("### خطاها")
            for e in _run_stats["errors"][:15]:
                md.append(f"- `{e.get('source')}`: {e.get('error')}")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
    except OSError as exc:
        logging.getLogger("memehunter").debug("GITHUB_STEP_SUMMARY write failed: %s", exc)


def log_data_source(source: str, status: str, detail: str = "") -> None:
    record_api_call(source, status, detail)
