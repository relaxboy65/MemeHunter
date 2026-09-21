"""
wyckoff.py
Wyckoff Method و Volume Spread Analysis (VSA) - V2.0

تشخیص فاز accumulation/distribution و spring/upthrust.

VSA مکانیزم:
- حجم بالا + spread پایین = فشار خرید/فروش جذب شده (exhaustion)
- Spring: تست آخرین پایین با حجم کم و برگشت = accumulation
- Upthrust: تست آخرین بالا با حجم کم و برگشت = distribution
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class WyckoffResult:
    """نتیجه تحلیل Wyckoff."""
    phase: str = "unknown"  # accumulation/distribution/markup/markdown/unknown
    spring_detected: bool = False
    upthrust_detected: bool = False
    vsa_signal: str = "neutral"  # bullish/bearish/neutral
    effort_vs_result: float = 0.5  # 0..1 (high = effort resulted in result)
    volume_anomaly: bool = False
    signal_score: float = 0.5
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "spring_detected": self.spring_detected,
            "upthrust_detected": self.upthrust_detected,
            "vsa_signal": self.vsa_signal,
            "effort_vs_result": round(self.effort_vs_result, 3),
            "volume_anomaly": self.volume_anomaly,
            "signal_score": round(self.signal_score, 3),
            "notes": self.notes,
        }


def analyze_wyckoff(opens: List[float], highs: List[float], lows: List[float],
                    closes: List[float], volumes: List[float]) -> WyckoffResult:
    """
    تحلیل Wyckoff/VSA.
    """
    result = WyckoffResult()
    if len(closes) < 10 or len(volumes) < 10:
        return result

    # محاسبه spread برای هر کندل
    spreads = [highs[i] - lows[i] for i in range(len(closes))]

    # میانگین حجم
    avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
    avg_spread = statistics.mean(spreads[-20:]) if len(spreads) >= 20 else statistics.mean(spreads)

    # VSA: کندل آخر
    last_spread = spreads[-1]
    last_vol = volumes[-1]
    last_close = closes[-1]
    last_open = opens[-1]

    # Effort vs Result
    # effort = volume, result = price change
    price_change = abs(last_close - last_open)
    if avg_vol > 0 and last_vol > 0:
        vol_ratio = last_vol / avg_vol
        if price_change > 0 and avg_spread > 0:
            spread_ratio = last_spread / avg_spread
            # اگر حجم بالا ولی spread پایین = exhaustion
            if vol_ratio > 1.5 and spread_ratio < 0.7:
                result.effort_vs_result = 0.3
                result.vsa_signal = "exhaustion"
                result.notes.append("VSA: حجم بالا + spread پایین = exhaustion")
                # اگر در روند نزولی = احتمال برگشت صعودی
                if last_close < last_open:
                    result.signal_score = 0.65
                    result.notes.append("احتمال accumulation phase")
                    result.phase = "accumulation"
            # اگر حجم بالا و spread بالا = trend قوی
            elif vol_ratio > 1.3 and spread_ratio > 1.2:
                result.effort_vs_result = 0.85
                if last_close > last_open:
                    result.vsa_signal = "bullish"
                    result.signal_score = 0.70
                    result.phase = "markup"
                    result.notes.append("VSA: حجم + spread بالا + صعودی = trend صعودی قوی")
                else:
                    result.vsa_signal = "bearish"
                    result.signal_score = 0.30
                    result.phase = "markdown"
                    result.notes.append("VSA: حجم + spread بالا + نزولی = trend نزولی قوی")

    # Spring detection
    # تست آخرین کف با حجم کم و برگشت سریع
    if len(lows) >= 5:
        recent_lows = lows[-5:-1]
        if recent_lows:
            min_low_idx = recent_lows.index(min(recent_lows))
            min_low = recent_lows[min_low_idx]
            last_low = lows[-1]

            # اگر آخرین low زیر min_low رفت ولی قیمت بسته بالاتر است
            if last_low < min_low and last_close > min_low:
                # حجم کم در spring
                if volumes[-1] < avg_vol * 0.7:
                    result.spring_detected = True
                    result.signal_score = 0.75
                    result.phase = "accumulation"
                    result.notes.append(f"Spring: تست کف {min_low:.6f} با حجم کم و برگشت")

    # Upthrust detection
    if len(highs) >= 5:
        recent_highs = highs[-5:-1]
        if recent_highs:
            max_high = max(recent_highs)
            last_high = highs[-1]

            if last_high > max_high and last_close < max_high:
                if volumes[-1] < avg_vol * 0.7:
                    result.upthrust_detected = True
                    result.signal_score = 0.25
                    result.phase = "distribution"
                    result.notes.append(f"Upthrust: تست سقف {max_high:.6f} با حجم کم و برگشت")

    # Volume anomaly
    if last_vol > avg_vol * 2.5:
        result.volume_anomaly = True
        result.notes.append("Volume anomaly: حجم 2.5x میانگین")

    # اگر هیچ سیگنالی نیست، خنثی
    if not result.notes:
        result.phase = "ranging"
        result.notes.append("بدون سیگنال واضح - بازار در حالت رنج")

    return result
