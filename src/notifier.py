"""
notifier.py
ارسال نوتیفیکیشن تلگرام برای سیگنال‌های خرید/فروش - پروژه MemeHunter.

V1.3.1 - یکدست‌سازی کامل ایموجی (🟢/🔴/🟡) + خلاصه واقعی/پروکسی + سلب مسئولیت ثابت.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

import requests

from .analyzer import AnalysisResult, Signal
from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


# --------------------------------------------------------------------------- #
# ایموجی‌های یکدست و فاخر - V1.3.1
# --------------------------------------------------------------------------- #
# سیگنال‌ها
SIGNAL_BADGE = {
    Signal.BUY:   "🟢 BUY",
    Signal.SELL:  "🔴 SELL",
    Signal.HOLD:  "🟡 HOLD",
}

# ایموجی‌های پایه
EMOJI = {
    "header":        "🎯",
    "summary":       "📋",
    "top_opportunity": "🚀",
    "details":       "📊",
    "real_data":     "✅",
    "proxy_data":    "🔮",
    "warning":       "⚠️",
    "money":         "💵",
    "clock":         "⏰",
    "info":          "ℹ️",
    "alert":         "🚨",
    "success":       "✅",
    "error":         "❌",
    "separator":     "━━━━━━━━━━━━━━━━━━",
    "sub_separator": "───────────────",
}

# سلب مسئولیت ثابت - در انتهای هر پیام
DISCLAIMER = (
    f"{EMOJI['warning']} هشدار ریسک:\n"
    "  این سیگنال‌ها صرفاً آموزشی هستند و توصیه مالی نیستند.\n"
    "  میم‌کوین‌ها بسیار پرنوسان و پرریسک هستند.\n"
    "  فقط با پولی سرمایه‌گذاری کنید که حاضر به از دست دادنش هستید.\n"
    "  همیشه قبل از تصمیم‌گیری، تحقیق شخصی (DYOR) انجام دهید."
)


def _count_data_sources(results: List[AnalysisResult]) -> Tuple[int, int]:
    """شمارش کوین‌هایی که داده واقعی vs پروکسی دارند."""
    real_count = 0
    proxy_only_count = 0
    for r in results:
        ds = r.data_sources or ""
        if "واقعی" in ds:
            real_count += 1
        else:
            proxy_only_count += 1
    return real_count, proxy_only_count


def format_telegram_message(results: List[AnalysisResult],
                            paper_trading_stats: Optional[dict] = None) -> str:
    """
    ساخت پیام تلگرام با فرمت فاخر و یکدست - V1.3.1.

    ساختار:
    1. هدر
    2. خلاصه (شمارش واقعی/پروکسی + BUY/SELL/HOLD)
    3. برترین فرصت
    4. جزئیات سیگنال‌ها
    5. Paper Trading (اگر موجود)
    6. سلب مسئولیت ثابت
    """
    if not results:
        return f"{EMOJI['error']} هیچ میم‌کوینی پیدا نشد."

    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    important_signals = [r for r in sorted_results if r.signal in (Signal.BUY, Signal.SELL)]
    if not important_signals:
        important_signals = sorted_results[:3]

    buy_count = sum(1 for r in results if r.signal == Signal.BUY)
    sell_count = sum(1 for r in results if r.signal == Signal.SELL)
    hold_count = sum(1 for r in results if r.signal == Signal.HOLD)
    real_count, proxy_only_count = _count_data_sources(results)

    lines: List[str] = []

    # هدر
    lines.append(f"{EMOJI['header']} MemeHunter Signal Report")
    lines.append(EMOJI["separator"])
    lines.append("")

    # خلاصه - V1.3.1 اکنون شامل شمارش واقعی/پروکسی
    lines.append(f"{EMOJI['summary']} خلاصه:")
    lines.append(f"  🟢 خرید: {buy_count}  |  🔴 فروش: {sell_count}  |  🟡 نگه‌داری: {hold_count}")
    lines.append(f"  {EMOJI['info']} کل کوین‌ها: {len(results)}")
    lines.append(f"  {EMOJI['real_data']} داده واقعی: {real_count}  |  "
                 f"{EMOJI['proxy_data']} فقط پروکسی: {proxy_only_count}")
    lines.append("")

    # برترین فرصت
    buy_signals = [r for r in sorted_results if r.signal == Signal.BUY]
    if buy_signals:
        top = buy_signals[0]
        lines.append(f"{EMOJI['top_opportunity']} برترین فرصت:")
        lines.append(f"  🟢 {top.name} ({top.symbol})")
        lines.append(f"     امتیاز: {top.score:.2f}  |  اطمینان: {top.confidence*100:.0f}%")
        if top.data_sources:
            lines.append(f"     {EMOJI['info']} داده‌ها: {top.data_sources}")
        lines.append("")

    # جزئیات سیگنال‌ها
    lines.append(f"{EMOJI['details']} جزئیات سیگنال‌ها:")
    lines.append(EMOJI["separator"])
    lines.append("")

    for r in important_signals:
        badge = SIGNAL_BADGE.get(r.signal, "🟡 HOLD")
        lines.append(f"{badge}  {r.name} ({r.symbol})")

        # قیمت
        price_str = f"${r.current_price:.6f}" if r.current_price < 1 else f"${r.current_price:.2f}"
        lines.append(f"  {EMOJI['money']} قیمت: {price_str}")

        # تغییرات با ایموجی رنگی
        emoji_24 = "🟢" if r.change_24h_pct >= 0 else "🔴"
        emoji_7d = "🟢" if r.change_7d_pct >= 0 else "🔴"
        lines.append(f"  24h: {emoji_24} {r.change_24h_pct:+.2f}%  |  "
                     f"7d: {emoji_7d} {r.change_7d_pct:+.2f}%")

        # امتیاز با رنگ
        score_emoji = "🟢" if r.score >= 0.65 else ("🔴" if r.score <= 0.35 else "🟡")
        lines.append(f"  {EMOJI['info']} امتیاز: {score_emoji} {r.score:.3f}  |  "
                     f"اطمینان: {r.confidence*100:.1f}%")

        # مارکت‌کپ و حجم
        mcap_str = _format_money(r.market_cap)
        vol_str = _format_money(r.volume_24h)
        lines.append(f"  {EMOJI['money']} مارکت‌کپ: {mcap_str}  |  حجم: {vol_str}")

        # اندیکاتورهای کلیدی فشرده با ایموجی رنگی
        ind = r.indicators
        indicator_parts = []
        if ind.get("rsi") is not None:
            rsi_val = ind["rsi"]
            rsi_emoji = "🔴" if rsi_val > 70 else ("🟢" if rsi_val < 30 else "🟡")
            indicator_parts.append(f"RSI={rsi_val:.0f}{rsi_emoji}")
        if ind.get("volume_surge_ratio") is not None:
            vsr = ind["volume_surge_ratio"]
            vol_emoji = "🔥" if vsr >= 2 else ""
            indicator_parts.append(f"Vol={vsr:.1f}x{vol_emoji}")
        if ind.get("ma_bullish") is not None:
            ma_emoji = "🟢" if ind["ma_bullish"] else "🔴"
            indicator_parts.append(f"MA={ma_emoji}")
        if ind.get("atr_percent") is not None:
            atr_pct = ind["atr_percent"]
            atr_emoji = "🔥" if atr_pct > 10 else ""
            indicator_parts.append(f"ATR={atr_pct:.0f}%{atr_emoji}")
        if ind.get("bollinger_squeeze"):
            indicator_parts.append("BB=Squeeze🔍")

        if indicator_parts:
            lines.append(f"  {EMOJI['details']} " + "  |  ".join(indicator_parts))

        # V1.3.1 - تحلیل‌های پیشرفته با برچسب روشن ✅/🔮
        adv = getattr(r, "advanced", {}) or {}
        adv_parts = []
        if adv.get("liquidity_score") is not None:
            is_real = adv.get("liquidity_is_real", False)
            tag = f"{EMOJI['real_data']}" if is_real else f"{EMOJI['proxy_data']}"
            adv_parts.append(f"Liq={adv['liquidity_score']:.2f} {tag}")
        if adv.get("buy_pressure") is not None:
            is_real = adv.get("orderflow_is_real", False)
            tag = f"{EMOJI['real_data']}" if is_real else f"{EMOJI['proxy_data']}"
            bp = adv['buy_pressure']
            bp_emoji = "🟢" if bp > 0.6 else ("🔴" if bp < 0.4 else "🟡")
            adv_parts.append(f"BuyPress={bp:.2f}{bp_emoji} {tag}")
        if adv.get("sweep_detected"):
            # V1.3.1 - برچسب همیشه‌واضح Sweep به‌عنوان پروکسی
            adv_parts.append(f"{EMOJI['alert']}Sweep {EMOJI['proxy_data']}(پروکسی)")
        if adv.get("large_trades_count") and adv.get("large_trades_count", 0) > 0:
            adv_parts.append(f"LargeTrades={adv['large_trades_count']} {EMOJI['proxy_data']}")
        if adv.get("mtf_aligned_count") and adv.get("mtf_total_count"):
            adv_parts.append(f"MTF={adv['mtf_aligned_count']}/{adv['mtf_total_count']}")

        if adv_parts:
            lines.append(f"  {EMOJI['info']} " + "  |  ".join(adv_parts))

        # 2 دلیل اول
        if r.reasons:
            for reason in r.reasons[:2]:
                lines.append(f"     • {reason}")
        lines.append("")

    # V1.3.1 - Paper Trading خلاصه
    if paper_trading_stats and paper_trading_stats.get("total_positions", 0) > 0:
        lines.append(EMOJI["sub_separator"])
        lines.append(f"{EMOJI['success']} Paper Trading:")
        lines.append(f"  پوزیشن‌های باز: {paper_trading_stats['open_positions']}")
        lines.append(f"  پوزیشن‌های بسته: {paper_trading_stats['closed_positions']}")
        if paper_trading_stats.get('closed_positions', 0) > 0:
            wr = paper_trading_stats['win_rate']
            wr_emoji = "🟢" if wr >= 60 else ("🔴" if wr < 40 else "🟡")
            lines.append(f"  نرخ موفقیت: {wr_emoji} {wr:.1f}%")
            pnl = paper_trading_stats['total_pnl_usd']
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            lines.append(f"  کل PnL: {pnl_emoji} ${pnl:+.2f}")
        lines.append("")

    # سلب مسئولیت ثابت
    lines.append(EMOJI["separator"])
    lines.append(DISCLAIMER)
    lines.append("")
    version_num = settings.PROJECT_VERSION.replace("V", "")
    lines.append(f"{EMOJI['clock']} MemeHunter v{version_num}")

    return "\n".join(lines)


def _format_money(amount: float) -> str:
    """قالب‌بندی مبالغ بزرگ به‌صورت خوانا (K, M, B)."""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.2f}K"
    return f"${amount:.2f}"


class TelegramNotifier:
    """ارسال پیام به کانال یا چت تلگرام از طریق Bot API."""

    def __init__(self,
                 bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None) -> None:
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_base = "https://api.telegram.org/bot{token}/{method}"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        if not self.is_configured:
            logger.warning("Telegram notifier is not configured "
                           "(TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing).")
            return False

        chunks = self._split_message(text, max_length=4000)
        all_sent = True
        for chunk in chunks:
            ok = self._send_single(chunk, parse_mode=parse_mode)
            if not ok:
                all_sent = False
        return all_sent

    def _send_single(self, text: str, parse_mode: Optional[str] = None) -> bool:
        url = self.api_base.format(token=self.bot_token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                logger.error("Telegram API error %d: %s",
                             resp.status_code, resp.text[:300])
                return False
            logger.info("Telegram message sent successfully to %s", self.chat_id)
            return True
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return False

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


def notify_results(results: List[AnalysisResult],
                   paper_trading_stats: Optional[dict] = None) -> bool:
    """تابع کمکی: ساخت پیام و ارسال به تلگرام."""
    notifier = TelegramNotifier()
    if not notifier.is_configured:
        return False
    message = format_telegram_message(results, paper_trading_stats=paper_trading_stats)
    return notifier.send_message(message)
