"""
reporter.py
قالب‌بندی خروجی تحلیل به صورت جدول، JSON یا CSV.
Formats analysis results into table / JSON / CSV.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime
from typing import List

from .analyzer import AnalysisResult, Signal
from .config import settings


SIGNAL_EMOJI = {
    Signal.BUY: "BUY",
    Signal.SELL: "SELL",
    Signal.HOLD: "HOLD",
}


def format_table(results: List[AnalysisResult]) -> str:
    """قالب جدولی قابل خواندن در ترمینال."""
    if not results:
        return "هیچ میم‌کوینی پیدا نشد."

    header = (
        f"{'#':<3} {'Symbol':<10} {'Price $':<12} {'24h %':<8} "
        f"{'7d %':<8} {'Score':<7} {'Signal':<7} {'Reasons'}"
    )
    lines = [header, "-" * 100]

    # مرتب‌سازی بر اساس امتیاز نزولی
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

    for i, r in enumerate(sorted_results, 1):
        signal_tag = SIGNAL_EMOJI.get(r.signal, "?")
        top_reason = r.reasons[0] if r.reasons else ""
        lines.append(
            f"{i:<3} {r.symbol:<10} {r.current_price:<12.6f} "
            f"{r.change_24h_pct:>+7.2f}% {r.change_7d_pct:>+7.2f}% "
            f"{r.score:<7.3f} {signal_tag:<7} {top_reason}"
        )

    # جمع‌بندی
    buy_count = sum(1 for r in results if r.signal == Signal.BUY)
    sell_count = sum(1 for r in results if r.signal == Signal.SELL)
    hold_count = sum(1 for r in results if r.signal == Signal.HOLD)

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"  خلاصه: {buy_count} خرید | {sell_count} فروش | {hold_count} نگه‌داری")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_detailed(results: List[AnalysisResult]) -> str:
    """گزارش مفصل با دلایل هر سیگنال."""
    if not results:
        return "هیچ میم‌کوینی پیدا نشد."

    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("  گزارش کامل تحلیل میم‌کوین‌ها")
    lines.append(f"  تاریخ تولید: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    for r in sorted_results:
        signal_tag = SIGNAL_EMOJI.get(r.signal, "?")
        lines.append("")
        lines.append(f"[{signal_tag}] {r.name} ({r.symbol})")
        lines.append("-" * 70)
        lines.append(f"  قیمت فعلی:        ${r.current_price:.6f}")
        lines.append(f"  مارکت‌کپ:          ${r.market_cap:,.0f}")
        lines.append(f"  حجم 24 ساعت:      ${r.volume_24h:,.0f}")
        lines.append(f"  تغییر 24 ساعت:    {r.change_24h_pct:+.2f}%")
        lines.append(f"  تغییر 7 روز:      {r.change_7d_pct:+.2f}%")
        lines.append(f"  امتیاز نهایی:      {r.score:.3f}/1.000")
        lines.append(f"  اطمینان:           {r.confidence*100:.1f}%")
        lines.append("  دلایل:")
        for reason in r.reasons:
            lines.append(f"    - {reason}")
    return "\n".join(lines)


def format_json(results: List[AnalysisResult]) -> str:
    """خروجی JSON برای استفاده در ابزارهای دیگر."""
    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_coins": len(results),
        "results": [r.to_dict() for r in sorted(results, key=lambda r: r.score, reverse=True)],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def format_csv(results: List[AnalysisResult]) -> str:
    """خروجی CSV برای اکسل و تحلیل داده."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "symbol", "name", "price_usd", "market_cap_usd",
        "volume_24h_usd", "change_24h_pct", "change_7d_pct",
        "score", "signal", "confidence",
    ])
    for r in sorted(results, key=lambda r: r.score, reverse=True):
        writer.writerow([
            r.symbol, r.name, r.current_price, r.market_cap,
            r.volume_24h, r.change_24h_pct, r.change_7d_pct,
            round(r.score, 3), r.signal.value, round(r.confidence, 3),
        ])
    return out.getvalue()


def save_report(content: str, fmt: str = "txt") -> str:
    """ذخیره گزارش در پوشه reports/ و بازگرداندن مسیر فایل."""
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meme_report_{timestamp}.{fmt}"
    path = os.path.join(settings.OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
