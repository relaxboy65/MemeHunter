"""
notifier.py
ارسال نوتیفیکیشن تلگرام - MemeHunter V1.4.1

- خلاصه واضح BUY / SELL / HOLD
- تفکیک نتایج + هشتگ
- لینک CoinGecko / TradingView / KuCoin
- بازگرداندن message_id برای ریپلای بعدی
"""
from __future__ import annotations

import csv
import logging
import os
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

DISCLAIMER = (
    "⚠️ هشدار ریسک:\n"
    "سیگنال‌ها صرفاً آموزشی‌اند و توصیه مالی نیستند.\n"
    "میم‌کوین‌ها پرنوسان‌اند — فقط با پول قابل‌از‌دست‌دادن وارد شوید. DYOR."
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TG_MSG_FILE = DATA_DIR / "telegram_messages.csv"
TG_MSG_COLUMNS = [
    "sent_at", "message_id", "chat_id", "scan_timestamp",
    "buy_count", "sell_count", "hold_count", "total", "version",
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
    # TradingView pair فرضی USDT
    return f"https://www.tradingview.com/symbols/{symbol.upper()}USDT/"


def _kucoin_link(symbol: str) -> str:
    return f"https://www.kucoin.com/trade/{symbol.upper()}-USDT"


def _hashtags(symbol: str, signal: Signal) -> str:
    sig = signal.value if hasattr(signal, "value") else str(signal)
    # فارسی سیگنال → انگلیسی هشتگ
    map_sig = {"خرید": "BUY", "فروش": "SELL", "نگه‌داری": "HOLD"}
    sig_en = map_sig.get(sig, sig.upper().replace(" ", ""))
    clean = "".join(c for c in symbol.upper() if c.isalnum())
    return f"#{clean} #{sig_en} #MemeHunter #Crypto"


def format_telegram_message(
    results: List[AnalysisResult],
    paper_trading_stats: Optional[dict] = None,
    run_meta: Optional[dict] = None,
) -> str:
    """
    پیام فاخر و خوانا — V1.4.1

    ساختار:
    1) هدر + نتیجه کلی (چند خرید/فروش/نگهداری)
    2) بخش 🟢 BUY / 🔴 SELL / 🟡 HOLD (تا ۵ مورد هر کدام)
    3) لینک + هشتگ هر کوین
    4) آمار منابع داده
    5) سلب مسئولیت
    """
    if not results:
        return "❌ هیچ میم‌کوینی در این اسکن تحلیل نشد."

    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    buys = [r for r in sorted_results if r.signal == Signal.BUY]
    sells = [r for r in sorted_results if r.signal == Signal.SELL]
    holds = [r for r in sorted_results if r.signal == Signal.HOLD]

    real_count = sum(1 for r in results if r.data_sources and "واقعی" in (r.data_sources or ""))
    proxy_only = len(results) - real_count

    lines: List[str] = []
    ver = settings.PROJECT_VERSION
    lines.append(f"🎯 MemeHunter {ver} — گزارش اسکن")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("📋 نتیجه این اجرا:")
    lines.append(
        f"  🟢 خرید: {len(buys)}   🔴 فروش: {len(sells)}   🟡 نگه‌داری: {len(holds)}"
    )
    lines.append(f"  📊 کل تحلیل‌شده: {len(results)}")
    lines.append(f"  ✅ داده واقعی: {real_count}  |  🔮 فقط پروکسی: {proxy_only}")
    if run_meta:
        if run_meta.get("history_kucoin") is not None:
            lines.append(
                f"  📡 تاریخچه: KuCoin={run_meta.get('history_kucoin', 0)} "
                f"| CG={run_meta.get('history_coingecko', 0)}"
            )
        if run_meta.get("duration_seconds"):
            lines.append(f"  ⏱ مدت اسکن: {run_meta['duration_seconds']:.0f}s")
    lines.append("")

    def _section(title: str, items: List[AnalysisResult], limit: int = 5) -> None:
        if not items:
            return
        lines.append(title)
        lines.append("───────────────")
        for r in items[:limit]:
            badge = SIGNAL_BADGE.get(r.signal, "🟡 HOLD")
            lines.append(f"{badge}  {r.name} ({r.symbol})")
            lines.append(
                f"  💵 {_price_str(r.current_price)}  |  "
                f"24h: {r.change_24h_pct:+.1f}%  |  7d: {r.change_7d_pct:+.1f}%"
            )
            lines.append(
                f"  🎚 امتیاز: {r.score:.3f}  |  اطمینان: {r.confidence * 100:.0f}%"
            )
            mcap = _format_money(r.market_cap)
            vol = _format_money(r.volume_24h)
            lines.append(f"  💰 مارکت‌کپ: {mcap}  |  حجم: {vol}")
            if r.data_sources:
                lines.append(f"  📡 {r.data_sources}")
            # دلایل کوتاه
            if r.reasons:
                for reason in r.reasons[:2]:
                    short = reason if len(reason) < 90 else reason[:87] + "…"
                    lines.append(f"  • {short}")
            # لینک‌ها
            links = [
                f"CG: {_cg_link(r.coin_id)}",
                f"TV: {_tv_link(r.symbol)}",
            ]
            if r.data_sources and ("KuCoin" in r.data_sources or "واقعی" in r.data_sources):
                links.append(f"KC: {_kucoin_link(r.symbol)}")
            lines.append("  🔗 " + " | ".join(links))
            lines.append(f"  {_hashtags(r.symbol, r.signal)}")
            lines.append("")
        if len(items) > limit:
            lines.append(f"  … و {len(items) - limit} مورد دیگر")
            lines.append("")

    if buys:
        _section(f"🟢 سیگنال‌های خرید ({len(buys)})", buys, limit=8)
    if sells:
        _section(f"🔴 سیگنال‌های فروش ({len(sells)})", sells, limit=8)
    # HOLD: فقط برترین‌ها اگر BUY/SELL نبود یا همیشه ۳ تای برتر
    if holds:
        title = f"🟡 نگه‌داری — برترین امتیازها ({len(holds)} کل)"
        _section(title, holds, limit=5 if (buys or sells) else 8)

    if not buys and not sells:
        lines.append("ℹ️ در این اسکن سیگنال خرید/فروش صادر نشد.")
        lines.append("همه در محدوده نگه‌داری بودند.")
        lines.append("")

    if paper_trading_stats and paper_trading_stats.get("total_positions", 0) > 0:
        lines.append("───────────────")
        lines.append("📈 Paper Trading:")
        lines.append(f"  باز: {paper_trading_stats.get('open_positions', 0)}  |  "
                     f"بسته: {paper_trading_stats.get('closed_positions', 0)}")
        if paper_trading_stats.get("closed_positions", 0) > 0:
            lines.append(
                f"  WinRate: {paper_trading_stats.get('win_rate', 0):.0f}%  |  "
                f"PnL: ${paper_trading_stats.get('total_pnl_usd', 0):+.2f}"
            )
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(DISCLAIMER)
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} | {ver}")
    lines.append("#MemeHunter #ScanReport")

    return "\n".join(lines)


def save_telegram_message_id(
    message_id: int,
    chat_id: str,
    buy_count: int,
    sell_count: int,
    hold_count: int,
    total: int,
) -> None:
    """ذخیره message_id برای ریپلای بعدی در چک نتایج."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not TG_MSG_FILE.exists()
    with TG_MSG_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(TG_MSG_COLUMNS)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message_id,
            chat_id,
            int(datetime.now().timestamp()),
            buy_count,
            sell_count,
            hold_count,
            total,
            settings.PROJECT_VERSION,
        ])
    logger.info("Telegram message_id=%s ذخیره شد → %s", message_id, TG_MSG_FILE)


def get_last_telegram_message_id() -> Optional[int]:
    """آخرین message_id ذخیره‌شده برای reply."""
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


class TelegramNotifier:
    """ارسال پیام به کانال/چت تلگرام."""

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
        """
        ارسال پیام. برمی‌گرداند (موفقیت, لیست message_idها).
        """
        if not self.is_configured:
            logger.warning(
                "Telegram notifier is not configured "
                "(TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing)."
            )
            return False, []

        chunks = self._split_message(text, max_length=4000)
        ids: List[int] = []
        all_ok = True
        first_reply = reply_to_message_id
        for i, chunk in enumerate(chunks):
            mid = self._send_single(
                chunk,
                parse_mode=parse_mode,
                reply_to_message_id=first_reply if i == 0 else None,
            )
            if mid is None:
                all_ok = False
            else:
                ids.append(mid)
        self.last_message_ids = ids
        return all_ok, ids

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
                logger.error(
                    "Telegram API error %d: %s",
                    resp.status_code,
                    resp.text[:300],
                )
                return None
            data = resp.json()
            mid = data.get("result", {}).get("message_id")
            logger.info(
                "Telegram message sent to %s (message_id=%s)",
                self.chat_id,
                mid,
            )
            return int(mid) if mid is not None else None
        except (requests.exceptions.RequestException, ValueError, TypeError) as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return None

    @staticmethod
    def _split_message(text: str, max_length: int = 4000) -> List[str]:
        if len(text) <= max_length:
            return [text]
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0
        for line in text.split("\n"):
            line_len = len(line) + 1
            if current_len + line_len > max_length and current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += line_len
        if current:
            chunks.append("\n".join(current))
        return chunks


def notify_results(
    results: List[AnalysisResult],
    paper_trading_stats: Optional[dict] = None,
    run_meta: Optional[dict] = None,
) -> Tuple[bool, List[int]]:
    """ساخت پیام، ارسال، ذخیره message_id."""
    notifier = TelegramNotifier()
    if not notifier.is_configured:
        return False, []
    message = format_telegram_message(
        results,
        paper_trading_stats=paper_trading_stats,
        run_meta=run_meta,
    )
    ok, ids = notifier.send_message(message)
    if ok and ids:
        buy_c = sum(1 for r in results if r.signal == Signal.BUY)
        sell_c = sum(1 for r in results if r.signal == Signal.SELL)
        hold_c = sum(1 for r in results if r.signal == Signal.HOLD)
        save_telegram_message_id(
            ids[0],
            notifier.chat_id,
            buy_c,
            sell_c,
            hold_c,
            len(results),
        )
    return ok, ids
