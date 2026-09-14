"""
volume_alert.py
هشدار حجم غیرعادی - جدا از اسکن دوره‌ای.
Unusual volume alert - separate from periodic scan.

V1.2.0 - تشخیص حجم غیرعادی بر اساس انحراف معیار.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class VolumeAlert:
    """اطلاعات هشدار حجم غیرعادی."""
    coin_id: str
    symbol: str
    name: str
    current_volume: float
    avg_volume: float
    volume_ratio: float          # نسبت حجم فعلی به میانگین
    z_score: float               # z-score آماری
    is_anomaly: bool             # آیا واقعاً غیرعادی است؟
    severity: str                # 'low', 'medium', 'high', 'extreme'
    notes: List[str] = field(default_factory=list)


def detect_volume_anomaly(volumes: List[float],
                         coin_id: str,
                         symbol: str,
                         name: str,
                         lookback: int = 30) -> Optional[VolumeAlert]:
    """
    تشخیص حجم غیرعادی با روش‌های آماری.

    روش‌ها:
    1. نسبت ساده: حجم فعلی / میانگین (با آستانه 3x)
    2. z-score: انحراف معیار حجم فعلی از میانگین (با آستانه 2)
    """
    if len(volumes) < lookback + 1:
        return None

    historical = volumes[-lookback - 1:-1]
    current = volumes[-1]

    if current <= 0:
        return None

    avg_vol = statistics.mean(historical)
    if avg_vol <= 0:
        return None

    # روش 1: نسبت ساده
    ratio = current / avg_vol

    # روش 2: z-score (اگر انحراف معیار قابل محاسبه باشد)
    try:
        std_vol = statistics.stdev(historical)
        z_score = (current - avg_vol) / std_vol if std_vol > 0 else 0
    except statistics.StatisticsError:
        z_score = 0

    # تشخیص غیرعادی بودن
    is_anomaly = (ratio >= settings.VOLUME_ANOMALY_THRESHOLD or
                  (z_score >= 2 and ratio >= 1.5))

    # شدت غیرعادی
    severity = "none"
    if ratio >= 10 or z_score >= 5:
        severity = "extreme"
    elif ratio >= 5 or z_score >= 3:
        severity = "high"
    elif ratio >= 3 or z_score >= 2:
        severity = "medium"
    elif ratio >= 2 or z_score >= 1.5:
        severity = "low"

    notes: List[str] = []
    if is_anomaly:
        notes.append(f"حجم {ratio:.1f}x میانگین 30 روز")
        if z_score >= 2:
            notes.append(f"z-score = {z_score:.2f} (آماری معنادار)")
        if severity == "extreme":
            notes.append("شدت: بسیار شدید - احتمال رویداد مهم")
        elif severity == "high":
            notes.append("شدت: بالا - احتمال حرکت بزرگ")
        elif severity == "medium":
            notes.append("شدت: متوسط - ارزش بررسی دارد")

    return VolumeAlert(
        coin_id=coin_id,
        symbol=symbol,
        name=name,
        current_volume=current,
        avg_volume=avg_vol,
        volume_ratio=ratio,
        z_score=z_score,
        is_anomaly=is_anomaly,
        severity=severity,
        notes=notes,
    )


def format_volume_alerts(alerts: List[VolumeAlert]) -> str:
    """قالب‌بندی هشدارهای حجم غیرعادی."""
    if not alerts:
        return "هیچ حجم غیرعادی پیدا نشد."

    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  هشدار حجم غیرعادی (Volume Anomaly Alert)")
    lines.append("=" * 60)
    lines.append("")

    # فیلتر فقط هشدارهای واقعی
    real_alerts = [a for a in alerts if a.is_anomaly]
    real_alerts.sort(key=lambda a: a.volume_ratio, reverse=True)

    if not real_alerts:
        lines.append("هیچ حجم غیرعادی پیدا نشد.")
        return "\n".join(lines)

    lines.append(f"  تعداد هشدارها: {len(real_alerts)}")
    lines.append("")

    for a in real_alerts:
        lines.append(f"  [{a.severity.upper()}] {a.name} ({a.symbol})")
        lines.append(f"    حجم فعلی: ${a.current_volume:,.0f}")
        lines.append(f"    میانگین 30 روز: ${a.avg_volume:,.0f}")
        lines.append(f"    نسبت: {a.volume_ratio:.1f}x")
        lines.append(f"    z-score: {a.z_score:.2f}")
        for note in a.notes:
            lines.append(f"    • {note}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
