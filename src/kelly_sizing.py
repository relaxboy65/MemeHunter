"""
kelly_sizing.py
Kelly Criterion و Volatility Targeting برای position sizing بهینه - V2.0

فرمول Kelly:
    f* = (b·p - q) / b
که p = win rate, q = 1-p, b = win/loss ratio

برای کریپتو با توزیع fat-tailed، از Quarter Kelly استفاده می‌کنیم.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import List, Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class KellyResult:
    """نتیجه محاسبه Kelly."""
    kelly_fraction: float = 0.0       # درصد کامل (0..1)
    fractional_kelly: float = 0.0     # بعد از کاهش (Quarter Kelly)
    recommended_size: float = 0.0    # حجم پیشنهادی (0..1)
    win_rate: float = 0.0
    win_loss_ratio: float = 0.0
    confidence: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "kelly_fraction": round(self.kelly_fraction, 4),
            "fractional_kelly": round(self.fractional_kelly, 4),
            "recommended_size": round(self.recommended_size, 4),
            "win_rate": round(self.win_rate, 4),
            "win_loss_ratio": round(self.win_loss_ratio, 4),
        }


def compute_kelly(win_rate: float,
                  avg_win_pct: float,
                  avg_loss_pct: float,
                  fraction: float = 0.25) -> KellyResult:
    """
    محاسبه Kelly Criterion.

    win_rate: 0..1 (احتمال برد)
    avg_win_pct: میانگین سود هر ترید برنده (درصد، مثلاً 5.0)
    avg_loss_pct: میانگین زیان هر ترید بازنده (درصد، مثلاً 3.0 - بدون علامت)
    fraction: کسر Kelly (پیش‌فرض 0.25 = Quarter Kelly)
    """
    result = KellyResult()
    result.win_rate = win_rate

    if avg_loss_pct <= 0 or win_rate <= 0 or win_rate >= 1:
        result.notes = "داده ناکافی برای Kelly"
        return result

    # Win/Loss ratio
    b = avg_win_pct / avg_loss_pct
    result.win_loss_ratio = b
    p = win_rate
    q = 1 - p

    # Kelly formula: f* = (b*p - q) / b
    kelly = (b * p - q) / b
    result.kelly_fraction = kelly

    # اعمال کسر (Quarter Kelly)
    fractional = kelly * fraction
    result.fractional_kelly = fractional

    # Clamp to [0, 0.50] (هرگز بیشتر از 50% سرمایه)
    result.recommended_size = max(0.0, min(0.50, fractional))

    # توضیح
    if kelly < 0:
        result.notes = "Kelly منفی - استراتژی سودآور نیست"
        result.recommended_size = 0.0
    elif kelly < 0.05:
        result.notes = f"Kelly پایین ({kelly*100:.1f}%) - edge ضعیف"
    elif kelly > 0.50:
        result.notes = f"Kelly بسیار بالا ({kelly*100:.1f}%) - احتمالاً overfit"
    else:
        result.notes = f"Kelly سالم ({kelly*100:.1f}%) - Quarter Kelly = {fractional*100:.1f}%"

    return result


def volatility_targeting(asset_volatility_pct: float,
                          target_volatility_pct: float = 5.0,
                          max_position: float = 0.40) -> float:
    """
    محاسبه position size بر اساس volatility targeting.

    asset_volatility_pct: نوسان روزانه دارایی (مثلاً ATR% = 10)
    target_volatility_pct: نوسان هدف پورتفوی (مثلاً 5%)
    max_position: حداکثر position size (مثلاً 0.40 = 40%)

    خروجی: position size (0..1)
    """
    if asset_volatility_pct <= 0:
        return 0.0

    # Position size = target_vol / asset_vol
    size = target_volatility_pct / asset_volatility_pct

    # محدودسازی
    return max(0.0, min(max_position, size))


def combined_sizing(kelly_result: KellyResult,
                     asset_volatility_pct: float,
                     target_volatility_pct: float = 5.0,
                     max_position: float = 0.40) -> float:
    """
    ترکیب Kelly و Volatility Targeting.
    کمترین مقدار را می‌گیریم برای محافظه‌کاری بیشتر.
    """
    kelly_size = kelly_result.recommended_size
    vol_size = volatility_targeting(asset_volatility_pct, target_volatility_pct, max_position)

    # کمترین را بگیر
    final = min(kelly_size, vol_size)

    # محدودسازی نهایی
    return max(0.0, min(max_position, final))
