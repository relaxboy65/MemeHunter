"""
profitable_strategy.py
استراتژی سودده بر اساس تحلیل داده‌های تاریخی واقعی - V1.5.0

این ماژول بر اساس تحلیل 326 رکورد تاریخی واقعی ساخته شده و
فاکتورهایی که واقعاً سودآور بوده‌اند را شناسایی می‌کند.

یافته‌های کلیدی از تحلیل داده‌های 8 روزه:
  - RSI 30-50: +0.96% بازده، 60% win rate
  - MA صعودی: +1.19% بازده، 59% win rate
  - OrderFlow 0.50-0.60: +1.14% بازده، 62% win rate
  - ATR >20% یا <5%: +2.14% و +2.09% بازده
  - Bollinger 0.30-0.50: +0.78% بازده، 64% win rate
  - بدون سوییپ: +0.82% بازده، 59% win rate
  - حجم بالا (>1.2x) منفی است: -0.67% (خستگی بازار)
  - RSI >70 منفی است: -1.28% (اشباع خرید)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

from .config import settings
from .indicators import IndicatorPack


logger = logging.getLogger(settings.PROJECT_SLUG)


class Signal(str, Enum):
    BUY = "خرید"
    SELL = "فروش"
    HOLD = "نگه‌داری"


@dataclass
class ProfitableResult:
    """نتیجه تحلیل استراتژی سودده."""
    coin_id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    volume_24h: float
    change_24h_pct: float
    change_7d_pct: float
    score: float                       # امتیاز استراتژی سودده (0..1)
    signal: Signal
    confidence: float                  # 0..1
    expected_return_pct: float         # بازده مورد انتظار (بر اساس داده‌های تاریخی)
    reasons: list = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    advanced: dict = field(default_factory=dict)
    data_sources: str = ""

    def to_dict(self) -> dict:
        return {
            "coin_id": self.coin_id,
            "symbol": self.symbol,
            "name": self.name,
            "current_price_usd": round(self.current_price, 6),
            "market_cap_usd": round(self.market_cap, 0),
            "volume_24h_usd": round(self.volume_24h, 0),
            "change_24h_pct": round(self.change_24h_pct, 2),
            "change_7d_pct": round(self.change_7d_pct, 2),
            "score": round(self.score, 3),
            "signal": self.signal.value,
            "confidence": round(self.confidence, 3),
            "expected_return_pct": round(self.expected_return_pct, 2),
            "reasons": self.reasons,
            "indicators": self.indicators,
            "advanced": self.advanced,
            "data_sources": self.data_sources,
        }


def analyze_profitable(coin: dict, indicators: IndicatorPack,
                       advanced_pack: Optional[Any] = None) -> ProfitableResult:
    """
    تحلیل سودده بر اساس داده‌های تاریخی.

    این تابع به‌جای استفاده از امتیازدهی سنتی، مستقیماً بر اساس
    فاکتورهایی که در داده‌های تاریخی سودآور بوده‌اند تصمیم می‌گیرد.
    """
    reasons: list = []
    score = 0.5  # شروع از خنثی
    expected_return = 0.0
    evidence_count = 0
    positive_evidence = 0

    ind = indicators

    # ===== فاکتور 1: RSI (مهم) =====
    if ind.rsi is not None:
        if 30 <= ind.rsi < 50:
            # منطقه اشباع فروش ملایم - بهترین برای خرید
            score += 0.08
            expected_return += 0.96
            positive_evidence += 1
            reasons.append(f"RSI={ind.rsi:.1f} - اشباع فروش ملایم (سودده تاریخی: +0.96%)")
            evidence_count += 1
        elif 50 <= ind.rsi < 70:
            # منطقه خنثی به بالا
            score += 0.02
            expected_return += 0.43
            reasons.append(f"RSI={ind.rsi:.1f} - منطقه صعودی ملایم")
            evidence_count += 1
        elif ind.rsi >= 70:
            # اشباع خرید - منفی
            score -= 0.08
            expected_return -= 1.28
            reasons.append(f"RSI={ind.rsi:.1f} - اشباع خرید (زیان‌ده تاریخی: -1.28%)")
            evidence_count += 1
        elif ind.rsi < 30:
            # اشباع فروش شدید - ممکن است برگرد
            score += 0.04
            expected_return += 0.5
            reasons.append(f"RSI={ind.rsi:.1f} - اشباع فروش شدید")
            evidence_count += 1

    # ===== فاکتور 2: MA Trend (مهم) =====
    if ind.ma is not None:
        if ind.ma.bullish_cross:
            score += 0.07
            expected_return += 1.19
            positive_evidence += 1
            reasons.append("MA صعودی (سودده تاریخی: +1.19%)")
        else:
            score -= 0.02
            reasons.append("MA نزولی (احتیاط)")
        evidence_count += 1

    # ===== فاکتور 3: ATR (نوسان بازار) =====
    if ind.atr is not None:
        atr_pct = ind.atr.atr_percent
        if atr_pct > 20:
            # نوسان بسیار بالا - فرصت بزرگ
            score += 0.08
            expected_return += 2.14
            positive_evidence += 1
            reasons.append(f"ATR={atr_pct:.1f}% - نوسان بسیار بالا (سودده تاریخی: +2.14%)")
        elif atr_pct < 5:
            # نوسان بسیار کم - پایداری
            score += 0.06
            expected_return += 2.09
            positive_evidence += 1
            reasons.append(f"ATR={atr_pct:.1f}% - نوسان کم (سودده تاریخی: +2.09%)")
        elif 5 <= atr_pct < 10:
            # نوسان متوسط
            score += 0.01
            expected_return += 0.30
        elif 10 <= atr_pct <= 20:
            score += 0.02
            expected_return += 0.57
        evidence_count += 1

    # ===== فاکتور 4: Bollinger Bands =====
    if ind.bollinger is not None:
        pb = ind.bollinger.percent_b
        if 0.30 <= pb < 0.50:
            # بهترین منطقه - پایین‌وسط
            score += 0.06
            expected_return += 0.78
            positive_evidence += 1
            reasons.append(f"Bollinger %B={pb:.2f} - منطقه پایین‌وسط (سودده تاریخی: +0.78%, win 64%)")
        elif 0.50 <= pb < 0.70:
            score += 0.03
            expected_return += 0.60
        elif pb >= 0.70:
            score -= 0.02
            expected_return += 0.05
            reasons.append(f"Bollinger %B={pb:.2f} - نزدیک باند بالا (احتیاط)")
        elif pb < 0.30:
            score += 0.04
            expected_return += 0.73
            reasons.append(f"Bollinger %B={pb:.2f} - نزدیک باند پایین")
        evidence_count += 1

    # ===== فاکتور 5: OrderFlow (اگر داده واقعی داریم) =====
    adv_dict = {}
    data_sources = ""
    if advanced_pack is not None:
        if advanced_pack.orderflow is not None:
            bp = advanced_pack.orderflow.buy_pressure
            if 0.50 <= bp < 0.60:
                # بهترین منطقه - فشار خرید ملایم
                score += 0.07
                expected_return += 1.14
                positive_evidence += 1
                is_real = advanced_pack.orderflow.is_real
                tag = "واقعی" if is_real else "پروکسی"
                reasons.append(f"OrderFlow buy={bp:.2f} [{tag}] - فشار خرید ملایم (سودده: +1.14%)")
            elif 0.40 <= bp < 0.50:
                score += 0.04
                expected_return += 0.60
            elif bp >= 0.60:
                # فشار خرید زیاد - احتیاط (اشباع)
                score -= 0.01
                expected_return += 0.32
            elif bp < 0.40:
                # فشار فروش
                score -= 0.02
            evidence_count += 1

        # فاکتور 6: سوییپ (منفی در این داده‌ها!)
        if advanced_pack.sweep is not None and advanced_pack.sweep.sweep_detected:
            # سوییپ در داده‌های ما منفی بوده!
            score -= 0.05
            expected_return -= 0.56
            reasons.append(f"سوییپ شناسایی شد (زیان‌ده تاریخی: -0.56%)")
        elif advanced_pack.sweep is not None:
            # بدون سوییپ = سودده
            score += 0.03
            expected_return += 0.82
            evidence_count += 1
            positive_evidence += 1

        # فاکتور 7: Liquidity
        if advanced_pack.liquidity is not None:
            liq_score = advanced_pack.liquidity.liquidity_score
            if 0.50 <= liq_score < 0.70:
                # بهترین منطقه لیکوییدیتی
                score += 0.05
                expected_return += 1.45
                positive_evidence += 1
                reasons.append(f"Liquidity={liq_score:.2f} - لیکوییدیتی متوسط (سودده: +1.45%)")
            elif liq_score >= 0.70:
                score += 0.02
                expected_return += 0.36
            evidence_count += 1

        adv_dict = advanced_pack.to_dict()
        data_sources = advanced_pack.get_data_source_summary()

    # ===== فاکتور 8: Volume Surge (با تأخیر منفی) =====
    if ind.volume_surge_ratio is not None:
        vsr = ind.volume_surge_ratio
        if vsr > 1.20:
            # حجم زیاد = خستگی بازار (در داده‌های ما منفی)
            score -= 0.04
            expected_return -= 0.67
            reasons.append(f"Volume surge={vsr:.1f}x - خستگی بازار (زیان‌ده: -0.67%)")
        elif 0.80 <= vsr <= 1.20:
            # حجم نرمال - بهترین
            score += 0.03
            expected_return += 0.69
            positive_evidence += 1
        elif vsr < 0.80:
            # حجم کم - قیمت پایین
            score += 0.04
            expected_return += 0.86
            positive_evidence += 1
        evidence_count += 1

    # محدودسازی امتیاز
    score = max(0.1, min(0.9, score))

    # تصمیم سیگنال - آستانه‌های جدید بر اساس داده‌ها
    if score >= 0.62:
        signal = Signal.BUY
    elif score <= 0.40:
        signal = Signal.SELL
    else:
        signal = Signal.HOLD

    # اطمینان بر اساس تعداد شواهد مثبت
    confidence = min(0.95, 0.3 + (positive_evidence / max(1, evidence_count)) * 0.7)

    return ProfitableResult(
        coin_id=coin.get("id", ""),
        symbol=(coin.get("symbol") or "").upper(),
        name=coin.get("name", ""),
        current_price=coin.get("current_price") or 0.0,
        market_cap=coin.get("market_cap") or 0.0,
        volume_24h=coin.get("total_volume") or 0.0,
        change_24h_pct=coin.get("price_change_percentage_24h") or 0.0,
        change_7d_pct=coin.get("price_change_percentage_7d_in_currency") or 0.0,
        score=score,
        signal=signal,
        confidence=confidence,
        expected_return_pct=expected_return,
        reasons=reasons,
        indicators=indicators.to_dict(),
        advanced=adv_dict,
        data_sources=data_sources,
    )
