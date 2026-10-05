"""
pump_predictor.py
پیش‌بینی‌گر پامپ - تشخیص ارزهای در حال انباشت قبل از پامپ - V2.2.0

منطق: پیدا کردن ارزهایی که حجم در حال افزایش است ولی قیمت هنوز حرکت نکرده.
این یعنی پول هوشمند در حال انباشت است و پامپ در راه است.

نشانه‌های pre-pump:
1. Volume buildup: حجم در حال افزایش ولی قیمت ثابت
2. Bollinger Squeeze: فشار نوسان قبل از انفجار
3. Funding rate منفی: شورت‌ها انباشته‌اند (short squeeze fuel)
4. Open Interest افزایش + قیمت ثابت
5. Smart money inflow: تریدهای بزرگ خرید > فروش
6. Spring pattern: تست کف و برگشت سریع
7. Wyckoff Phase C: فاز انباشت پیشرفته
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


class PumpPhase(str, Enum):
    """فاز پامپ ارز."""
    ACCUMULATION = "انباشت"         # قبل از پامپ - سیگنال خرید
    READY_TO_PUMP = "آماده پامپ"    # انباشت کامل - خرید قوی
    PUMPING = "در حال پامپ"         # پامپ شروع شده - هولد
    DISTRIBUTING = "توزیع"          # بعد از پامپ - سیگنال فروش
    EXHAUSTED = "خستگی"             # پامپ تمام شده - فروش
    DORMANT = "خواب"                # بدون فعالیت - صبر


@dataclass
class PumpSignal:
    """سیگنال پیش‌بینی پامپ."""
    phase: PumpPhase = PumpPhase.DORMANT
    confidence: float = 0.0          # 0..1 - اطمینان به پیش‌بینی
    expected_move_pct: float = 0.0   # حرکت مورد انتظار (درصد)
    time_to_pump_hours: int = 0       # زمان تخمینی تا پامپ
    # نشانه‌های تشخیصی
    signals: List[str] = field(default_factory=list)
    # امتیاز ترکیبی
    pump_score: float = 0.0          # 0..1 - احتمال پامپ
    distribution_score: float = 0.0  # 0..1 - احتمال توزیع
    # توصیه
    action: str = "WAIT"             # BUY / HOLD / SELL / WAIT / NO_TRADE
    confirmations: int = 0
    risk_gate: str = "UNKNOWN"
    signal_tier: str = "IGNORE"
    entry_zone: Optional[tuple] = None  # (lower, upper) قیمت پیشنهادی ورود
    stop_loss_pct: float = 0.08       # حد ضرر پیشنهادی
    take_profit_pct: float = 0.30    # حد سود پیشنهادی

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "confidence": round(self.confidence, 3),
            "expected_move_pct": round(self.expected_move_pct, 1),
            "time_to_pump_hours": self.time_to_pump_hours,
            "pump_score": round(self.pump_score, 3),
            "distribution_score": round(self.distribution_score, 3),
            "action": self.action,
            "confirmations": self.confirmations,
            "risk_gate": self.risk_gate,
            "signal_tier": self.signal_tier,
            "entry_zone": [round(self.entry_zone[0], 6), round(self.entry_zone[1], 6)]
                        if self.entry_zone else None,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "signals": self.signals,
        }


# --------------------------------------------------------------------------- #
# 1. تشخیص Volume Buildup (مهم‌ترین نشانه pre-pump)
# --------------------------------------------------------------------------- #
def detect_volume_buildup(volumes: List[float],
                           prices: List[float],
                           lookback: int = 7) -> Optional[dict]:
    """
    تشخیص افزایش حجم بدون حرکت قیمت.

    منطق:
    - حجم اخیر (3 روز) > میانگین حجم (lookback روز)
    - تغییر قیمت کم (کمتر از threshold)
    - این یعنی: کسی دارد حجم زیادی می‌خرد ولی قیمت را بالا نبرده

    خروجی:
    - volume_ratio: نسبت حجم اخیر به میانگین
    - price_stability: ثبات قیمت (0..1, 1=کاملاً ثابت)
    - buildup_score: 0..1 (1 = buildup قوی)
    """
    if len(volumes) < lookback + 3 or len(prices) < lookback + 3:
        return None

    # حجم اخیر (3 روز آخر) vs میانگین (lookback روز قبل)
    recent_vol = statistics.mean(volumes[-3:])
    baseline_vol = statistics.mean(volumes[-lookback - 3:-3])

    if baseline_vol <= 0:
        return None

    volume_ratio = recent_vol / baseline_vol

    # ثبات قیمت: تغییر قیمت در 3 روز اخیر
    recent_prices = prices[-3:]
    if recent_prices[0] > 0:
        price_change_pct = abs(recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
    else:
        return None

    # ثبات: تغییر کمتر = ثبات بیشتر
    # اگر تغییر < 2% → ثبات کامل (1.0)
    # اگر تغییر > 10% → ناپایدار (0.0)
    if price_change_pct < 2:
        price_stability = 1.0
    elif price_change_pct > 10:
        price_stability = 0.0
    else:
        price_stability = 1.0 - (price_change_pct - 2) / 8

    # Buildup score
    # حجم 2x + ثبات بالا = buildup قوی
    # حجم 1.5x + ثبات متوسط = buildup متوسط
    if volume_ratio >= 2.0 and price_stability >= 0.7:
        buildup_score = 0.9
    elif volume_ratio >= 1.5 and price_stability >= 0.5:
        buildup_score = 0.7
    elif volume_ratio >= 1.2 and price_stability >= 0.3:
        buildup_score = 0.5
    else:
        buildup_score = 0.2

    return {
        "volume_ratio": volume_ratio,
        "price_stability": price_stability,
        "price_change_pct": price_change_pct,
        "buildup_score": buildup_score,
    }


# --------------------------------------------------------------------------- #
# 2. تشخیص Bollinger Squeeze (فشار قبل از انفجار)
# --------------------------------------------------------------------------- #
def detect_bollinger_squeeze(prices: List[float],
                               period: int = 20,
                               lookback: int = 50) -> Optional[dict]:
    """
    تشخیص Bollinger Squeeze - فشار نوسان قبل از حرکت بزرگ.

    منطق:
    - اگر width فعلی در 10% پایین تاریخ باشه = squeeze
    - این یعنی نوسان کم است و به‌زودی انفجار نوسان می‌آید
    """
    if len(prices) < max(period, lookback):
        return None

    # محاسبه width برای دوره‌های مختلف
    widths = []
    for i in range(period, len(prices)):
        window = prices[i - period:i]
        mean = statistics.mean(window)
        if mean > 0:
            std = statistics.stdev(window) if len(window) > 1 else 0
            widths.append((2 * std * 2) / mean)

    if not widths:
        return None

    current_width = widths[-1]
    recent_widths = widths[-lookback:] if len(widths) > lookback else widths

    # Percentile: درصد width‌هایی که بزرگتر از فعلی هستند
    below = sum(1 for w in recent_widths if w < current_width)
    percentile = below / len(recent_widths)

    # Squeeze: اگر در 10% پایین باشه
    is_squeeze = percentile < 0.10
    # Strong squeeze: 5% پایین
    is_strong_squeeze = percentile < 0.05

    if is_strong_squeeze:
        squeeze_score = 0.9
    elif is_squeeze:
        squeeze_score = 0.7
    elif percentile < 0.20:
        squeeze_score = 0.5
    else:
        squeeze_score = 0.2

    return {
        "current_width": current_width,
        "percentile": percentile,
        "is_squeeze": is_squeeze,
        "is_strong_squeeze": is_strong_squeeze,
        "squeeze_score": squeeze_score,
    }


# --------------------------------------------------------------------------- #
# 3. تشخیص Smart Money Inflow
# --------------------------------------------------------------------------- #
def detect_smart_money_inflow(real_orderflow: Optional[Any],
                               real_liquidity: Optional[Any] = None) -> Optional[dict]:
    """
    تشخیص ورود پول هوشمند.

    منطق:
    - تریدهای بزرگ خرید > فروش (smart money buying)
    - CVD مثبت (فشار خرید تهاجمی)
    - Buy pressure > 55%
    """
    if real_orderflow is None:
        return None

    result = {
        "large_buys": real_orderflow.large_buys,
        "large_sells": real_orderflow.large_sells,
        "cvd": real_orderflow.cvd,
        "buy_pressure": real_orderflow.buy_pressure,
        "smart_money_score": 0.0,
        "is_smart_money_buying": False,
    }

    # Smart money buying اگر:
    # - large_buys > large_sells
    # - buy_pressure > 0.55
    # - CVD مثبت

    score = 0.0
    if real_orderflow.large_buys > real_orderflow.large_sells:
        score += 0.3
    if real_orderflow.buy_pressure > 0.55:
        score += 0.3
    if real_orderflow.buy_pressure > 0.65:
        score += 0.2
    if real_orderflow.cvd > 0:
        score += 0.2

    result["smart_money_score"] = min(1.0, score)
    result["is_smart_money_buying"] = score >= 0.5

    return result


# --------------------------------------------------------------------------- #
# 4. تشخیص Short Squeeze Setup (از Funding/OI)
# --------------------------------------------------------------------------- #
def detect_short_squeeze_setup(funding_oi: Optional[Any]) -> Optional[dict]:
    """
    تشخیص شرایط short squeeze.

    منطق:
    - Funding rate خیلی منفی = شورت‌ها زیاد هستند
    - OI در حال افزایش = پوزیشن‌های جدید
    - این یعنی: اگر قیمت کمی بالا برود، short squeeze رخ می‌دهد
    """
    if funding_oi is None:
        return None

    result = {
        "funding_rate": funding_oi.funding_rate,
        "funding_regime": funding_oi.funding_rate_regime,
        "oi_change": funding_oi.open_interest_change_24h,
        "short_squeeze_score": 0.0,
        "is_short_squeeze_setup": False,
    }

    score = 0.0
    # Funding خیلی منفی = سوخت short squeeze
    if funding_oi.funding_rate < -0.05:
        score += 0.4
    elif funding_oi.funding_rate < -0.02:
        score += 0.2

    # OI افزایش = پوزیشن‌های جدید
    if funding_oi.open_interest_change_24h > 5:
        score += 0.3
    elif funding_oi.open_interest_change_24h > 0:
        score += 0.1

    # volatility coming signal
    if hasattr(funding_oi, 'volatility_coming') and funding_oi.volatility_coming > 0.6:
        score += 0.3

    result["short_squeeze_score"] = min(1.0, score)
    result["is_short_squeeze_setup"] = score >= 0.5

    return result


# --------------------------------------------------------------------------- #
# 5. تشخیص Spring Pattern (Wyckoff)
# --------------------------------------------------------------------------- #
def detect_spring_pattern(highs: List[float],
                           lows: List[float],
                           closes: List[float],
                           volumes: List[float]) -> Optional[dict]:
    """
    تشخیص Spring - تست کف و برگشت سریع.

    منطق:
    - قیمت به زیر کف قبلی می‌رود (fake breakdown)
    - ولی با حجم کم
    - سپس برمی‌گردد
    - این نشانه accumulation کامل
    """
    if len(lows) < 10 or len(volumes) < 10:
        return None

    # کف 5 روز اخیر (به‌جز آخرین)
    recent_lows = lows[-6:-1]
    if not recent_lows:
        return None

    min_low = min(recent_lows)
    last_low = lows[-1]
    last_close = closes[-1]

    # میانگین حجم
    avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
    last_vol = volumes[-1]

    # Spring conditions:
    # 1. آخرین low زیر کف قبلی
    # 2. ولی close بالاتر از کف (برگشت)
    # 3. حجم کم (کمتر از میانگین)
    is_spring = (last_low < min_low and
                 last_close > min_low and
                 last_vol < avg_vol * 0.8)

    if is_spring:
        spring_score = 0.85
    else:
        spring_score = 0.0

    return {
        "min_low": min_low,
        "last_low": last_low,
        "last_close": last_close,
        "is_spring": is_spring,
        "spring_score": spring_score,
    }


# --------------------------------------------------------------------------- #
# تابع اصلی: پیش‌بینی پامپ
# --------------------------------------------------------------------------- #
def predict_pump(prices: List[float],
                  volumes: List[float],
                  highs: Optional[List[float]] = None,
                  lows: Optional[List[float]] = None,
                  closes: Optional[List[float]] = None,
                  real_orderflow: Optional[Any] = None,
                  real_liquidity: Optional[Any] = None,
                  funding_oi: Optional[Any] = None,
                  current_price: float = 0,
                  volume_surge_ratio: Optional[float] = None,
                  price_change_24h_pct: Optional[float] = None,
                  rsi: Optional[float] = None) -> PumpSignal:
    """
    پیش‌بینی پامپ - تابع اصلی.

    V2.4.0: اکنون از indicators موجود (volume_surge_ratio, price_change_24h, rsi) هم استفاده می‌کند.

    ترکیب همه نشانه‌ها برای تشخیص:
    1. آیا ارز در حال انباشت است؟ (pre-pump → BUY)
    2. آیا ارز در حال پامپ است؟ (pumping → HOLD)
    3. آیا ارز در حال توزیع است؟ (post-pump → SELL)
    4. یا خواب است؟ (dormant → WAIT)
    """
    signal = PumpSignal()

    if len(prices) < 20 or len(volumes) < 20:
        signal.signals.append("داده ناکافی برای پیش‌بینی")
        signal.action = "WAIT"
        return signal

    if current_price == 0:
        current_price = prices[-1]

    if closes is None:
        closes = prices
    if highs is None:
        highs = [p * 1.01 for p in prices]
    if lows is None:
        lows = [p * 0.99 for p in prices]

    # ===== تحلیل نشانه‌های pre-pump =====
    pump_score = 0.0
    evidence_count = 0

    # 1. Volume Buildup
    buildup = detect_volume_buildup(volumes, prices)
    if buildup:
        pump_score += buildup["buildup_score"] * 0.30  # وزن 30%
        evidence_count += 1
        if buildup["buildup_score"] >= 0.7:
            signal.signals.append(
                f"Volume buildup: حجم {buildup['volume_ratio']:.1f}x میانگین "
                f"+ قیمت ثابت ({buildup['price_change_pct']:.1f}%)"
            )

    # 2. Bollinger Squeeze
    squeeze = detect_bollinger_squeeze(prices)
    if squeeze:
        pump_score += squeeze["squeeze_score"] * 0.20  # وزن 20%
        evidence_count += 1
        if squeeze["is_squeeze"]:
            signal.signals.append(
                f"Bollinger Squeeze: percentile {squeeze['percentile']:.0%} "
                f"{'(قوی)' if squeeze['is_strong_squeeze'] else ''}"
            )

    # 3. Smart Money Inflow
    smart_money = detect_smart_money_inflow(real_orderflow, real_liquidity)
    if smart_money:
        pump_score += smart_money["smart_money_score"] * 0.25  # وزن 25%
        evidence_count += 1
        if smart_money["is_smart_money_buying"]:
            signal.signals.append(
                f"Smart money buying: {smart_money['large_buys']} خرید بزرگ "
                f"vs {smart_money['large_sells']} فروش، buy_pressure={smart_money['buy_pressure']:.0%}"
            )

    # 4. Short Squeeze Setup
    short_squeeze = detect_short_squeeze_setup(funding_oi)
    if short_squeeze:
        pump_score += short_squeeze["short_squeeze_score"] * 0.15  # وزن 15%
        evidence_count += 1
        if short_squeeze["is_short_squeeze_setup"]:
            signal.signals.append(
                f"Short squeeze setup: funding={short_squeeze['funding_rate']:+.4f}%, "
                f"OI change={short_squeeze['oi_change']:+.1f}%"
            )

    # 5. Spring Pattern
    spring = detect_spring_pattern(highs, lows, closes, volumes)
    if spring:
        pump_score += spring["spring_score"] * 0.10  # وزن 10%
        evidence_count += 1
        if spring["is_spring"]:
            signal.signals.append(
                f"Spring pattern: تست کف {spring['min_low']:.6f} و برگشت با حجم کم"
            )

    # نرمال‌سازی صحیح: فقط وزن فاکتورهای موجود در مخرج می‌آید.
    # نسخه قبلی evidence_count * 0.20 باعث می‌شد یک فاکتور تنها
    # بتواند به‌اشتباه Pump Score=1.0 تولید کند.
    available_weight = 0.0
    weighted_score = 0.0
    if buildup:
        weighted_score += buildup["buildup_score"] * 0.30
        available_weight += 0.30
    if squeeze:
        weighted_score += squeeze["squeeze_score"] * 0.20
        available_weight += 0.20
    if smart_money:
        weighted_score += smart_money["smart_money_score"] * 0.25
        available_weight += 0.25
    if short_squeeze:
        weighted_score += short_squeeze["short_squeeze_score"] * 0.15
        available_weight += 0.15
    if spring:
        weighted_score += spring["spring_score"] * 0.10
        available_weight += 0.10

    # V2.7.0 - نرمال‌سازی ساده‌تر و کارآمدتر
    # به‌جای تقسیم بر available_weight، مجموع وزن‌های کامل را استفاده می‌کنیم
    # این باعث می‌شود حتی با 1 نشانه، score معقول باشد
    total_possible_weight = 0.30 + 0.20 + 0.25 + 0.15 + 0.10  # = 1.0
    pump_score = weighted_score / total_possible_weight if total_possible_weight > 0 else 0.0

    # V2.7.0: boost اگر چند نشانه همزمان فعال باشند (confluence)
    active_count = sum([
        bool(buildup and buildup["buildup_score"] >= 0.5),
        bool(squeeze and squeeze["squeeze_score"] >= 0.5),
        bool(smart_money and smart_money["smart_money_score"] >= 0.4),
        bool(short_squeeze and short_squeeze["short_squeeze_score"] >= 0.3),
        bool(spring and spring["is_spring"]),
    ])
    if active_count >= 2:
        pump_score = min(1.0, pump_score * 1.3)  # 30% boost for confluence
    if active_count >= 3:
        pump_score = min(1.0, pump_score * 1.2)  # additional 20% boost

    signal.pump_score = min(1.0, pump_score)
    signal.confirmations = sum([
        bool(buildup and buildup["buildup_score"] >= 0.5),
        bool(squeeze and squeeze["squeeze_score"] >= 0.5),
        bool(smart_money and smart_money["smart_money_score"] >= 0.4),
        bool(short_squeeze and short_squeeze["short_squeeze_score"] >= 0.3),
        bool(spring and spring["is_spring"]),
    ])

    # ===== تشخیص post-pump (توزیع) =====
    # اگر قیمت اخیر به‌شدت بالا رفته (10%+ در 3 روز)
    if len(prices) >= 4 and prices[-4] > 0:
        recent_return = (prices[-1] - prices[-4]) / prices[-4] * 100
    else:
        recent_return = 0

    # اگر حجم فعلی خیلی بالا (3x) و قیمت بالا = توزیع
    if len(volumes) >= 4:
        recent_vol = statistics.mean(volumes[-3:])
        baseline_vol = statistics.mean(volumes[-14:-3]) if len(volumes) >= 14 else statistics.mean(volumes)
        vol_ratio = recent_vol / baseline_vol if baseline_vol > 0 else 1
    else:
        vol_ratio = 1

    # V2.4.0: استفاده از volume_surge_ratio و price_change_24h اگر موجودند
    if volume_surge_ratio is not None:
        # volume_surge_ratio از CSV: نسبت حجم امروز به میانگین
        vol_ratio = max(vol_ratio, volume_surge_ratio)
    if price_change_24h_pct is not None:
        # price_change_24h_pct از CSV: تغییر قیمت 24 ساعت
        recent_return = max(recent_return, price_change_24h_pct)

    # Distribution score
    distribution_score = 0.0
    if recent_return > 20 and vol_ratio > 2:
        distribution_score = 0.8
        signal.signals.append(
            f"⚠️ توزیع احتمالی: رشد {recent_return:.1f}% + حجم {vol_ratio:.1f}x"
        )
    elif recent_return > 10 and vol_ratio > 1.5:
        distribution_score = 0.5
        signal.signals.append(
            f"خستگی بازار: رشد {recent_return:.1f}% + حجم {vol_ratio:.1f}x"
        )

    # V2.4.0: RSI-based signals (اگر RSI موجود است)
    if rsi is not None:
        if rsi > 75:
            # RSI بسیار بالا = اشباع خرید شدید = احتمال فروش
            distribution_score = min(1.0, distribution_score + 0.2)
            signal.signals.append(f"RSI={rsi:.0f} - اشباع خرید شدید (احتمال برگشت)")
        elif rsi < 30:
            # RSI بسیار پایین = اشباع فروش = احتمال برگشت صعودی
            pump_score = min(1.0, pump_score + 0.15)
            signal.signals.append(f"RSI={rsi:.0f} - اشباع فروش (احتمال برگشت صعودی)")
        elif 40 <= rsi <= 60:
            # RSI خنثی = بازار در حالت تعادل
            pass

    # اگر funding rate خیلی مثبت = long squeeze risk
    if funding_oi and funding_oi.funding_rate > 0.10:
        distribution_score += 0.3
        signal.signals.append(
            f"⚠️ Long squeeze risk: funding={funding_oi.funding_rate:+.4f}%"
        )

    signal.distribution_score = min(1.0, distribution_score)

    # ===== tiering: discovery can be sensitive, trading remains strict =====
    if signal.pump_score >= 0.82 and signal.confirmations >= 3:
        signal.signal_tier = "EXTREME"
    elif signal.pump_score >= 0.72 and signal.confirmations >= 3:
        signal.signal_tier = "STRONG"
    elif signal.pump_score >= settings.PUMP_MIN_SCORE and signal.confirmations >= settings.PUMP_CANDIDATE_MIN_CONFIRMATIONS:
        signal.signal_tier = "CANDIDATE"
    elif signal.pump_score >= settings.PUMP_WATCH_MIN_SCORE:
        signal.signal_tier = "WATCH"
    else:
        signal.signal_tier = "IGNORE"

    # ===== تصمیم‌گیری - V2.5.0: فقط BUY/SELL/WAIT (بدون HOLD) =====
    # BUY: قبل از پامپ (در حال انباشت)
    # SELL: بعد از پامپ (در حال توزیع)
    # WAIT: در غیر این صورت (شامل در حال پامپ - چون دیر است)
    #       در حال پامپ دیگر نمی‌گوییم HOLD چون دیر شده برای خرید

    if signal.distribution_score >= 0.5:
        # توزیع قوی → SELL (بعد از پامپ)
        signal.phase = PumpPhase.DISTRIBUTING
        signal.action = "SELL"
        signal.confidence = signal.distribution_score
        signal.expected_move_pct = -15
    elif signal.distribution_score >= 0.3 and recent_return > 10:
        # خستگی بازار → SELL
        signal.phase = PumpPhase.EXHAUSTED
        signal.action = "SELL"
        signal.confidence = signal.distribution_score
        signal.expected_move_pct = -10
    elif recent_return > 10 and signal.distribution_score < 0.3:
        # در حال پامپ → WAIT (دیر شده، نخر)
        signal.phase = PumpPhase.PUMPING
        signal.action = "WAIT"
        signal.confidence = 0.7
        signal.expected_move_pct = recent_return / 2
        signal.signals.append("⚠️ در حال پامپ است - خرید دیر است، صبر کن تا تمام شود")
    elif signal.pump_score >= 0.20 and signal.confirmations >= 1:
        # انباشت قابل توجه با حداقل 1 تأیید → BUY (قبل از پامپ)
        # V2.7.0: آستانه 0.20 چون با نرمال‌سازی جدید، یک نشانه قوی ≈ 0.20-0.25
        signal.phase = PumpPhase.READY_TO_PUMP
        signal.action = "BUY"
        signal.confidence = signal.pump_score
        signal.expected_move_pct = 20
        signal.time_to_pump_hours = 24
        signal.entry_zone = (current_price * 0.98, current_price * 1.02)
        signal.stop_loss_pct = 0.08
        signal.take_profit_pct = 0.30
    elif signal.pump_score >= 0.10:
        # انباشت اولیه → WATCH
        signal.phase = PumpPhase.ACCUMULATION
        signal.action = "WAIT"
        signal.confidence = signal.pump_score * 0.6
        signal.expected_move_pct = 10
    else:
        # خواب → WAIT
        signal.phase = PumpPhase.DORMANT
        signal.action = "WAIT"
        signal.confidence = 0.3

    if not signal.signals:
        signal.signals.append("بدون نشانه واضح - صبر کنید")

    return signal


def format_pump_signal(signal: PumpSignal, symbol: str = "") -> str:
    """قالب‌بندی سیگنال پامپ."""
    lines = []
    prefix = f"[{symbol}] " if symbol else ""
    lines.append(f"{prefix}فاز: {signal.phase.value}")
    lines.append(f"{prefix}اکشن: {signal.action}")
    lines.append(f"{prefix}اطمینان: {signal.confidence:.0%}")
    lines.append(f"{prefix}حرکت مورد انتظار: {signal.expected_move_pct:+.1f}%")
    if signal.time_to_pump_hours > 0:
        lines.append(f"{prefix}زمان تا پامپ: ~{signal.time_to_pump_hours} ساعت")
    lines.append(f"{prefix}Pump Score: {signal.pump_score:.2f}")
    lines.append(f"{prefix}Distribution Score: {signal.distribution_score:.2f}")
    if signal.entry_zone:
        lines.append(f"{prefix}Entry Zone: ${signal.entry_zone[0]:.6f} - ${signal.entry_zone[1]:.6f}")
        lines.append(f"{prefix}Stop Loss: -{signal.stop_loss_pct*100:.0f}%")
        lines.append(f"{prefix}Take Profit: +{signal.take_profit_pct*100:.0f}%")
    lines.append(f"{prefix}نشانه‌ها:")
    for s in signal.signals:
        lines.append(f"  • {s}")
    return "\n".join(lines)
