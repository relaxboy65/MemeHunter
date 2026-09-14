"""
notifier.py
ارسال نوتیفیکیشن تلگرام - MemeHunter V1.4.3

قوانین این نسخه:
- برای هر ارز یک پیام جداگانه ارسال می‌شود
- message_id هر پیام در data/telegram_messages.csv ذخیره می‌شود
- بدون هشدار ریسک و بدون هشتگ پروژه
"""
from __future__ import annotations

import csv
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import requests

from .analyzer import AnalysisResult, Signal
from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)

SIGNAL_BADGE = {
    Signal.BUY: "🟢 BUY",
    Signal.SELL: "🔴 SELL",
    Signal.HOLD: "🟡 HOLD",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TG_MSG_FILE = DATA_DIR / "telegram_messages.csv"
TG_RETENTION_DAYS = 90

# جدول CSV مشخصات پیام تلگرام (یک ردیف به ازای هر ارز)
TG_MSG_COLUMNS = [
    "sent_at",          # تاریخ و ساعت ارسال
    "message_id",       # آی‌دی پیام تلگرام
    "chat_id",
    "scan_timestamp",   # epoch اسکن
    "coin_id",
    "symbol",
    "name",
    "signal",
    "score",
    "version",
]


def _format_money(amount: float) -> str:
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:.2f}"


def _price_str(price: float) -> str:
    if price <= 0:
        return "—"
    if price < 0.0001:
        return f"${price:.8f}"
    if price < 1:
        return f"${price:.6f}"
    return f"${price:.4f}"


def _cg_link(coin_id: str) -> str:
    return f"https://www.coingecko.com/en/coins/{coin_id}"


def _tv_link(symbol: str) -> str:
    return f"https://www.tradingview.com/symbols/{symbol.upper()}USDT/"


def _kucoin_link(symbol: str) -> str:
    return f"https://www.kucoin.com/trade/{symbol.upper()}-USDT"


def _coin_tag(symbol: str) -> str:
    clean = "".join(c for c in symbol.upper() if c.isalnum())
    return f"#{clean}" if clean else ""


def format_coin_message(r: AnalysisResult, run_meta: Optional[dict] = None) -> str:
    """ساخت متن پیام جداگانه برای یک ارز."""
    badge = SIGNAL_BADGE.get(r.signal, "🟡 HOLD")
    lines: List[str] = []
    lines.append(f"{badge}  {r.name} ({r.symbol})")
    lines.append("───────────────")
    lines.append(
        f"💵 {_price_str(r.current_price)}  |  "
        f"24h: {r.change_24h_pct:+.1f}%  |  7d: {r.change_7d_pct:+.1f}%"
    )
    lines.append(
        f"🎚 امتیاز: {r.score:.3f}  |  اطمینان: {r.confidence * 100:.0f}%"
    )
    lines.append(
        f"💰 مارکت‌کپ: {_format_money(r.market_cap)}  |  "
        f"حجم: {_format_money(r.volume_24h)}"
    )
    if r.data_sources:
        lines.append(f"📡 {r.data_sources}")
    if r.reasons:
        for reason in r.reasons[:3]:
            short = reason if len(reason) < 100 else reason[:97] + "…"
            lines.append(f"• {short}")
    links = [
        f"CG: {_cg_link(r.coin_id)}",
        f"TV: {_tv_link(r.symbol)}",
    ]
    if r.data_sources and ("KuCoin" in (r.data_sources or "") or "واقعی" in (r.data_sources or "")):
        links.append(f"KC: {_kucoin_link(r.symbol)}")
    lines.append("🔗 " + " | ".join(links))
    tag = _coin_tag(r.symbol)
    if tag:
        lines.append(tag)
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} | {settings.PROJECT_VERSION}")
    return "\n".join(lines)


def format_summary_message(
    results: List[AnalysisResult],
    run_meta: Optional[dict] = None,
) -> str:
    """پیام خلاصه کوتاه (اختیاری، قبل از پیام‌های تک‌ارز)."""
    buys = sum(1 for r in results if r.signal == Signal.BUY)
    sells = sum(1 for r in results if r.signal == Signal.SELL)
    holds = sum(1 for r in results if r.signal == Signal.HOLD)
    real_count = sum(1 for r in results if r.data_sources and "واقعی" in (r.data_sources or ""))
    lines = [
        f"🎯 MemeHunter {settings.PROJECT_VERSION} — خلاصه اسکن",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🟢 خرید: {buys}   🔴 فروش: {sells}   🟡 نگه‌داری: {holds}",
        f"📊 کل: {len(results)}  |  ✅ داده واقعی: {real_count}",
    ]
    if run_meta and run_meta.get("duration_seconds"):
        lines.append(f"⏱ مدت: {run_meta['duration_seconds']:.0f}s")
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def format_telegram_message(
    results: List[AnalysisResult],
    paper_trading_stats: Optional[dict] = None,
    run_meta: Optional[dict] = None,
) -> str:
    """پیش‌نمایش: خلاصه + پیام هر ارز (برای --telegram-preview)."""
    if not results:
        return "❌ هیچ میم‌کوینی در این اسکن تحلیل نشد."
    parts = [format_summary_message(results, run_meta)]
    for r in sorted(results, key=lambda x: x.score, reverse=True):
        parts.append(format_coin_message(r, run_meta))
    return "\n\n==========\n\n".join(parts)


def format_telegram_parts(
    results: List[AnalysisResult],
    paper_trading_stats: Optional[dict] = None,
    run_meta: Optional[dict] = None,
) -> List[str]:
    """سازگاری با کد قبلی: لیست متن پیام‌ها."""
    if not results:
        return ["❌ هیچ میم‌کوینی در این اسکن تحلیل نشد."]
    parts = [format_summary_message(results, run_meta)]
    for r in sorted(results, key=lambda x: x.score, reverse=True):
        parts.append(format_coin_message(r, run_meta))
    return parts


def ensure_tg_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TG_MSG_FILE.exists():
        with TG_MSG_FILE.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(TG_MSG_COLUMNS)


def save_coin_message_id(
    message_id: int,
    chat_id: str,
    coin: AnalysisResult,
) -> None:
    """ذخیره مشخصات پیام یک ارز در جدول CSV."""
    ensure_tg_csv()
    with TG_MSG_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message_id,
            chat_id,
            int(datetime.now().timestamp()),
            coin.coin_id,
            coin.symbol,
            coin.name,
            coin.signal.value if hasattr(coin.signal, "value") else str(coin.signal),
            round(coin.score, 4),
            settings.PROJECT_VERSION,
        ])
    logger.info(
        "Telegram message_id=%s برای %s ذخیره شد → %s",
        message_id, coin.symbol, TG_MSG_FILE,
    )


def cleanup_old_telegram_records() -> int:
    """حذف رکوردهای قدیمی‌تر از ۹۰ روز از telegram_messages.csv."""
    if not TG_MSG_FILE.exists():
        return 0
    cutoff = time.time() - (TG_RETENTION_DAYS * 86400)
    with TG_MSG_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or TG_MSG_COLUMNS
        kept: List[Dict[str, Any]] = []
        deleted = 0
        for row in reader:
            try:
                ts = int(row.get("scan_timestamp", 0) or 0)
                if ts >= cutoff:
                    kept.append(row)
                else:
                    deleted += 1
            except (ValueError, TypeError):
                kept.append(row)
    if deleted > 0:
        with TG_MSG_FILE.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept)
    return deleted


def get_last_telegram_message_id() -> Optional[int]:
    if not TG_MSG_FILE.exists():
        return None
    try:
        with TG_MSG_FILE.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        return int(rows[-1]["message_id"])
    except (ValueError, KeyError, OSError):
        return None


def get_last_telegram_message_ids() -> List[int]:
    if not TG_MSG_FILE.exists():
        return []
    try:
        with TG_MSG_FILE.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return [int(r["message_id"]) for r in rows if r.get("message_id")]
    except (ValueError, KeyError, OSError):
        return []


def get_message_id_for_symbol(symbol: str) -> Optional[int]:
    """آخرین message_id ذخیره‌شده برای یک نماد (برای ریپلای چک نتیجه)."""
    if not TG_MSG_FILE.exists():
        return None
    try:
        with TG_MSG_FILE.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in reversed(rows):
            if (row.get("symbol") or "").upper() == symbol.upper():
                return int(row["message_id"])
    except (ValueError, KeyError, OSError):
        return None
    return None


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_base = "https://api.telegram.org/bot{token}/{method}"
        self.last_message_ids: List[int] = []

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(
        self,
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> Tuple[bool, List[int]]:
        if not self.is_configured:
            logger.warning(
                "Telegram notifier is not configured "
                "(TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing)."
            )
            return False, []
        mid = self._send_single(text, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
        if mid is None:
            return False, []
        self.last_message_ids = [mid]
        return True, [mid]

    def _send_single(
        self,
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> Optional[int]:
        url = self.api_base.format(token=self.bot_token, method="sendMessage")
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                logger.error("Telegram API error %d: %s", resp.status_code, resp.text[:300])
                return None
            data = resp.json()
            mid = data.get("result", {}).get("message_id")
            logger.info("Telegram message sent to %s (message_id=%s)", self.chat_id, mid)
            return int(mid) if mid is not None else None
        except (requests.exceptions.RequestException, ValueError, TypeError) as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return None


def notify_results(
    results: List[AnalysisResult],
    paper_trading_stats: Optional[dict] = None,
    run_meta: Optional[dict] = None,
    reply_to_previous: bool = False,
) -> Tuple[bool, List[int]]:
    """
    ۱) یک پیام خلاصه
    ۲) یک پیام جدا برای هر ارز
    ۳) ذخیره message_id هر ارز در data/telegram_messages.csv
    """
    notifier = TelegramNotifier()
    if not notifier.is_configured:
        return False, []

    if not results:
        ok, ids = notifier.send_message("❌ هیچ میم‌کوینی در این اسکن تحلیل نشد.")
        return ok, ids

    all_ids: List[int] = []
    any_ok = False

    # خلاصه
    summary = format_summary_message(results, run_meta)
    ok, ids = notifier.send_message(summary)
    if ok and ids:
        any_ok = True
        all_ids.extend(ids)

    # یک پیام به ازای هر ارز + ذخیره در CSV
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    for r in sorted_results:
        text = format_coin_message(r, run_meta)
        ok, ids = notifier.send_message(text)
        if ok and ids:
            any_ok = True
            all_ids.extend(ids)
            save_coin_message_id(ids[0], notifier.chat_id, r)
        # فاصله کوتاه برای جلوگیری از flood limit تلگرام
        time.sleep(0.35)

    deleted = cleanup_old_telegram_records()
    if deleted:
        logger.info("%d رکورد قدیمی تلگرام (بیش از ۹۰ روز) حذف شد", deleted)

    notifier.last_message_ids = all_ids
    return any_ok, all_ids
