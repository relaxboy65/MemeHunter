"""
smc_detector.py
Smart Money Concepts: Order Block، Fair Value Gap، Break of Structure - V2.0

پیاده‌سازی محلی (بدون نیاز به کتابخانه external) با داده OHLCV.

مفاهیم:
- Break of Structure (BOS): شکست آخرین swing high/low
- Order Block (OB): آخرین کندل مخالف قبل از حرکت impulsive
- Fair Value Gap (FVG): imbalance سه کندلی
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class SwingPoint:
    """نقطه swing (high یا low)."""
    index: int
    price: float
    type: str  # 'high' or 'low'


@dataclass
class OrderBlock:
    """ناحیه Order Block."""
    index: int
    high: float
    low: float
    type: str  # 'bullish' (last down candle before up move) or 'bearish'


@dataclass
class FairValueGap:
    """Fair Value Gap - imbalance سه کندلی."""
    index: int
    top: float    # بالای گپ
    bottom: float # پایین گپ
    type: str     # 'bullish' یا 'bearish'
    filled: bool = False


@dataclass
class SMCResult:
    """نتیجه تحلیل Smart Money Concepts."""
    bos_detected: bool = False
    bos_direction: str = ""  # 'bullish' یا 'bearish'
    choch_detected: bool = False  # Change of Character
    choch_direction: str = ""
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fair_value_gaps: List[FairValueGap] = field(default_factory=list)
    signal_score: float = 0.5  # 0..1 (high = bullish)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "bos_detected": self.bos_detected,
            "bos_direction": self.bos_direction,
            "choch_detected": self.choch_detected,
            "choch_direction": self.choch_direction,
            "order_blocks_count": len(self.order_blocks),
            "fvg_count": len(self.fair_value_gaps),
            "unfilled_fvg_count": sum(1 for f in self.fair_value_gaps if not f.filled),
            "signal_score": round(self.signal_score, 3),
            "notes": self.notes,
        }


def find_swing_points(highs: List[float], lows: List[float],
                       lookback: int = 2) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """
    پیدا کردن نقاط swing با fractal.
    یک swing high وقتی است که N کندل سمت چپ و راست پایین‌تر باشند.
    """
    swing_highs: List[SwingPoint] = []
    swing_lows: List[SwingPoint] = []

    for i in range(lookback, len(highs) - lookback):
        # Swing high
        is_high = True
        for j in range(1, lookback + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                is_high = False
                break
        if is_high:
            swing_highs.append(SwingPoint(index=i, price=highs[i], type="high"))

        # Swing low
        is_low = True
        for j in range(1, lookback + 1):
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                is_low = False
                break
        if is_low:
            swing_lows.append(SwingPoint(index=i, price=lows[i], type="low"))

    return swing_highs, swing_lows


def detect_bos(swing_highs: List[SwingPoint],
               swing_lows: List[SwingPoint],
               current_price: float) -> Tuple[bool, str]:
    """
    تشخیص Break of Structure.
    BOS صعودی: قیمت آخرین swing high را شکست
    BOS نزولی: قیمت آخرین swing low را شکست
    """
    if not swing_highs and not swing_lows:
        return False, ""

    last_high = swing_highs[-1] if swing_highs else None
    last_low = swing_lows[-1] if swing_lows else None

    if last_high and current_price > last_high.price:
        return True, "bullish"
    if last_low and current_price < last_low.price:
        return True, "bearish"
    return False, ""


def detect_order_blocks(opens: List[float], closes: List[float],
                         highs: List[float], lows: List[float],
                         volumes: List[float] = None) -> List[OrderBlock]:
    """
    تشخیص Order Blocks.
    Bullish OB: آخرین کندل نزولی قبل از حرکت صعودی قوی
    Bearish OB: آخرین کندل صعودی قبل از حرکت نزولی قوی
    """
    obs: List[OrderBlock] = []
    if len(closes) < 5:
        return obs

    # میانگین حجم برای threshold
    avg_vol = 0
    if volumes and len(volumes) > 0:
        avg_vol = sum(volumes) / len(volumes)

    for i in range(2, len(closes) - 2):
        # Bullish OB: کندل i نزولی، بعد از آن حرکت صعودی قوی
        if closes[i] < opens[i]:  # کندل نزولی
            # بررسی حرکت صعودی بعدی
            next_move_up = (closes[i + 1] > highs[i] and
                           closes[i + 2] > closes[i + 1])
            # اگر حجم بالا
            vol_ok = True
            if volumes and avg_vol > 0:
                vol_ok = volumes[i] > avg_vol * 1.2

            if next_move_up and vol_ok:
                obs.append(OrderBlock(
                    index=i, high=highs[i], low=lows[i], type="bullish"
                ))

        # Bearish OB: کندل i صعودی، بعد از آن حرکت نزولی قوی
        elif closes[i] > opens[i]:  # کندل صعودی
            next_move_down = (closes[i + 1] < lows[i] and
                             closes[i + 2] < closes[i + 1])
            vol_ok = True
            if volumes and avg_vol > 0:
                vol_ok = volumes[i] > avg_vol * 1.2

            if next_move_down and vol_ok:
                obs.append(OrderBlock(
                    index=i, high=highs[i], low=lows[i], type="bearish"
                ))

    # فقط آخرین 5 OB را نگه دار
    return obs[-5:]


def detect_fvg(opens: List[float], highs: List[float], lows: List[float]) -> List[FairValueGap]:
    """
    تشخیص Fair Value Gap - imbalance سه کندلی.

    Bullish FVG: low کندل 3 > high کندل 1 (gap رو به بالا)
    Bearish FVG: high کندل 3 < low کندل 1 (gap رو به پایین)
    """
    fvgs: List[FairValueGap] = []
    if len(highs) < 3:
        return fvgs

    for i in range(2, len(highs)):
        # Bullish FVG
        if lows[i] > highs[i - 2]:
            top = lows[i]
            bottom = highs[i - 2]
            fvgs.append(FairValueGap(
                index=i, top=top, bottom=bottom, type="bullish"
            ))
        # Bearish FVG
        elif highs[i] < lows[i - 2]:
            top = lows[i - 2]
            bottom = highs[i]
            fvgs.append(FairValueGap(
                index=i, top=top, bottom=bottom, type="bearish"
            ))

    return fvgs[-10:]  # آخرین 10 FVG


def analyze_smc(opens: List[float], highs: List[float], lows: List[float],
                closes: List[float], volumes: List[float] = None,
                current_price: float = 0) -> SMCResult:
    """
    تحلیل کامل Smart Money Concepts.
    """
    result = SMCResult()

    if len(closes) < 5:
        return result

    if current_price == 0:
        current_price = closes[-1]

    # Swing points
    swing_highs, swing_lows = find_swing_points(highs, lows, lookback=2)

    # BOS
    bos_detected, bos_dir = detect_bos(swing_highs, swing_lows, current_price)
    if bos_detected:
        result.bos_detected = True
        result.bos_direction = bos_dir
        if bos_dir == "bullish":
            result.signal_score = 0.70
            result.notes.append(f"BOS صعودی - شکست سقف {swing_highs[-1].price:.6f}")
        else:
            result.signal_score = 0.30
            result.notes.append(f"BOS نزولی - شکست کف {swing_lows[-1].price:.6f}")

    # Order Blocks
    obs = detect_order_blocks(opens, closes, highs, lows, volumes)
    result.order_blocks = obs
    if obs:
        last_ob = obs[-1]
        if last_ob.type == "bullish" and current_price >= last_ob.low and current_price <= last_ob.high:
            result.notes.append("قیمت در Order Block صعودی - ناحیه حمایت")
            result.signal_score = max(result.signal_score, 0.65)
        elif last_ob.type == "bearish" and current_price >= last_ob.low and current_price <= last_ob.high:
            result.notes.append("قیمت در Order Block نزولی - ناحیه مقاومت")
            result.signal_score = min(result.signal_score, 0.35)

    # Fair Value Gaps
    fvgs = detect_fvg(opens, highs, lows)
    result.fair_value_gaps = fvgs
    if fvgs:
        unfilled = [f for f in fvgs if not f.filled]
        if unfilled:
            last_fvg = unfilled[-1]
            if last_fvg.type == "bullish":
                result.notes.append(f"FVG صعودی نشده در {last_fvg.bottom:.6f}-{last_fvg.top:.6f}")
            else:
                result.notes.append(f"FVG نزولی نشده در {last_fvg.bottom:.6f}-{last_fvg.top:.6f}")

    # CHoCH (Change of Character) - ساده
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        # اگر بعد از یک روند نزولی، قیمت آخرین swing high را شکست = CHoCH صعودی
        if swing_highs[-1].price > swing_highs[-2].price:
            result.choch_detected = True
            result.choch_direction = "bullish"
            result.notes.append("CHoCH صعودی - احتمال تغییر روند")
        elif swing_lows[-1].price < swing_lows[-2].price:
            result.choch_detected = True
            result.choch_direction = "bearish"
            result.notes.append("CHoCH نزولی - احتمال تغییر روند")

    return result


def format_smc_report(result: SMCResult) -> str:
    """قالب‌بندی گزارش SMC."""
    lines: List[str] = []
    lines.append("=" * 50)
    lines.append("  Smart Money Concepts (SMC)")
    lines.append("=" * 50)
    lines.append(f"  BOS: {'✅ ' + result.bos_direction if result.bos_detected else '❌'}")
    lines.append(f"  CHoCH: {'✅ ' + result.choch_direction if result.choch_detected else '❌'}")
    lines.append(f"  Order Blocks: {len(result.order_blocks)}")
    lines.append(f"  FVGs: {len(result.fair_value_gaps)} (unfilled: {sum(1 for f in result.fair_value_gaps if not f.filled)})")
    lines.append(f"  Signal Score: {result.signal_score:.3f}")
    if result.notes:
        lines.append("  Notes:")
        for note in result.notes:
            lines.append(f"    • {note}")
    lines.append("=" * 50)
    return "\n".join(lines)
