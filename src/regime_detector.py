"""
regime_detector.py
تشخیص فاز بازار (trending/ranging/volatile) - V2.0

این ماژول با ترکیب ADX، Hurst Exponent و Bollinger Width
فاز بازار را تشخیص می‌دهد تا ربات در فاز اشتباه معامله نکند.

روش‌ها:
- ADX: > 25 trending، < 20 ranging
- Hurst: > 0.5 trending، < 0.5 mean-reverting
- Bollinger Width percentile: بالا = volatile، پایین = quiet
"""
from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


class MarketRegime(str, Enum):
    TRENDING_UP = "صعودی قوی"
    TRENDING_DOWN = "نزولی قوی"
    RANGING = "رنج (محدوده)"
    VOLATILE = "نوسانی شدید"
    QUIET = "آرام"
    CHOPPY = "هرج و مرج"


@dataclass
class RegimeResult:
    """نتیجه تشخیص رژیم بازار."""
    regime: MarketRegime = MarketRegime.RANGING
    adx: float = 0.0
    hurst: float = 0.5
    bollinger_width_percentile: float = 0.5
    volatility_regime: str = "medium"   # low/medium/high/extreme
    # آیا معامله کنیم؟
    should_trade: bool = True
    # توصیه
    recommendation: str = ""
    confidence: float = 0.0  # 0..1

    def to_dict(self) -> dict:
        return {
            "regime": self.regime.value,
            "adx": round(self.adx, 2),
            "hurst": round(self.hurst, 3),
            "bb_width_percentile": round(self.bollinger_width_percentile, 3),
            "volatility": self.volatility_regime,
            "should_trade": self.should_trade,
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 3),
        }


# --------------------------------------------------------------------------- #
# ADX (Average Directional Index)
# --------------------------------------------------------------------------- #
def _true_range(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    """محاسبه True Range."""
    tr: List[float] = []
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    return tr


def _wilder_smoothing(values: List[float], period: int) -> List[float]:
    """هموارسازی Wilder (مثل RSI)."""
    if len(values) < period:
        return values
    smoothed: List[float] = [sum(values[:period]) / period]
    for v in values[period:]:
        smoothed.append((smoothed[-1] * (period - 1) + v) / period)
    return smoothed


def compute_adx(highs: List[float], lows: List[float], closes: List[float],
                period: int = 14) -> Optional[float]:
    """
    محاسبه ADX.
    ADX > 25: روند قوی
    ADX < 20: بدون روند
    """
    if len(closes) < period * 2:
        return None

    # +DM and -DM
    plus_dm: List[float] = [0]
    minus_dm: List[float] = [0]
    for i in range(1, len(highs)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)

    # True Range
    tr = _true_range(highs, lows, closes)

    # Wilder smoothing
    if len(tr) < period:
        return None
    atr_series = _wilder_smoothing(tr, period)
    plus_dm_series = _wilder_smoothing(plus_dm[1:], period)
    minus_dm_series = _wilder_smoothing(minus_dm[1:], period)

    # +DI and -DI
    plus_di: List[float] = []
    minus_di: List[float] = []
    dx: List[float] = []
    min_len = min(len(atr_series), len(plus_dm_series), len(minus_dm_series))
    for i in range(min_len):
        if atr_series[i] > 0:
            pdi = (plus_dm_series[i] / atr_series[i]) * 100
            mdi = (minus_dm_series[i] / atr_series[i]) * 100
            plus_di.append(pdi)
            minus_di.append(mdi)
            if pdi + mdi > 0:
                dx.append(abs(pdi - mdi) / (pdi + mdi) * 100)

    if not dx or len(dx) < period:
        return None

    # ADX = Wilder smoothing of DX
    adx_series = _wilder_smoothing(dx, period)
    if adx_series:
        return adx_series[-1]
    return None


# --------------------------------------------------------------------------- #
# Hurst Exponent
# --------------------------------------------------------------------------- #
def compute_hurst(prices: List[float], max_lag: int = 20) -> Optional[float]:
    """
    محاسبه Hurst Exponent با روش R/S.

    H > 0.5: trending (پایدار)
    H = 0.5: random walk
    H < 0.5: mean-reverting
    """
    if len(prices) < max_lag * 2:
        return None

    # Convert to log returns
    returns: List[float] = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))

    if len(returns) < max_lag:
        return None

    # Compute R/S for different lags
    lags: List[int] = []
    rs_values: List[float] = []
    for lag in range(2, min(max_lag + 1, len(returns) // 2)):
        rs_list: List[float] = []
        for i in range(0, len(returns) - lag, lag):
            segment = returns[i:i + lag]
            if len(segment) < 2:
                continue
            mean = sum(segment) / len(segment)
            cum_dev = 0.0
            max_dev = -1e9
            min_dev = 1e9
            for r in segment:
                cum_dev += (r - mean)
                if cum_dev > max_dev:
                    max_dev = cum_dev
                if cum_dev < min_dev:
                    min_dev = cum_dev
            r_val = max_dev - min_dev
            std = statistics.stdev(segment) if len(segment) > 1 else 0
            if std > 0:
                rs_list.append(r_val / std)
        if rs_list:
            avg_rs = sum(rs_list) / len(rs_list)
            lags.append(lag)
            rs_values.append(math.log(avg_rs))

    if len(lags) < 3:
        return None

    # Linear regression: log(R/S) = H * log(lag) + c
    n = len(lags)
    sum_x = sum(math.log(l) for l in lags)
    sum_y = sum(rs_values)
    sum_xy = sum(math.log(lags[i]) * rs_values[i] for i in range(n))
    sum_xx = sum(math.log(l) ** 2 for l in lags)

    denom = n * sum_xx - sum_x ** 2
    if denom == 0:
        return None

    hurst = (n * sum_xy - sum_x * sum_y) / denom
    return hurst


# --------------------------------------------------------------------------- #
# Bollinger Width Percentile
# --------------------------------------------------------------------------- #
def compute_bollinger_width_percentile(prices: List[float],
                                        period: int = 20,
                                        lookback: int = 100) -> Optional[float]:
    """
    محاسبه percentile عرض Bollinger Bands.

    بالا = نوسان زیاد
    پایین = نوسان کم (squeeze)
    """
    if len(prices) < period:
        return None

    # Compute BB width series
    widths: List[float] = []
    for i in range(period, len(prices)):
        window = prices[i - period:i]
        mean = sum(window) / period
        variance = sum((p - mean) ** 2 for p in window) / period
        std = math.sqrt(variance)
        if mean > 0:
            widths.append((2 * std * 2) / mean)  # width / mean

    if not widths:
        return None

    # Take last `lookback` widths
    recent = widths[-lookback:] if len(widths) > lookback else widths
    current_width = widths[-1]

    # Compute percentile
    below = sum(1 for w in recent if w < current_width)
    percentile = below / len(recent)
    return percentile


# --------------------------------------------------------------------------- #
# Main regime detection
# --------------------------------------------------------------------------- #
def detect_regime(prices: List[float],
                  highs: Optional[List[float]] = None,
                  lows: Optional[List[float]] = None,
                  closes: Optional[List[float]] = None) -> RegimeResult:
    """
    تشخیص رژیم بازار با ترکیب ADX + Hurst + Bollinger Width.
    """
    result = RegimeResult()

    if len(prices) < 20:
        result.recommendation = "داده ناکافی برای تشخیص رژیم"
        result.should_trade = False
        result.confidence = 0.0
        return result

    # ADX (if OHLC available)
    if highs and lows and closes:
        adx = compute_adx(highs, lows, closes)
        if adx is not None:
            result.adx = adx

    # Hurst
    hurst = compute_hurst(prices)
    if hurst is not None:
        result.hurst = hurst

    # Bollinger width percentile
    bb_pct = compute_bollinger_width_percentile(prices)
    if bb_pct is not None:
        result.bollinger_width_percentile = bb_pct

    # Volatility regime
    if bb_pct is not None:
        if bb_pct > 0.9:
            result.volatility_regime = "extreme"
        elif bb_pct > 0.7:
            result.volatility_regime = "high"
        elif bb_pct > 0.3:
            result.volatility_regime = "medium"
        else:
            result.volatility_regime = "low"

    # Determine regime
    adx = result.adx
    hurst_val = result.hurst
    bb_p = result.bollinger_width_percentile

    # Decision tree
    confidence_score = 0.0

    if adx > 25 and hurst_val > 0.55:
        # Strong trend
        # Determine direction from price momentum
        if len(prices) >= 2 and prices[-1] > prices[0]:
            result.regime = MarketRegime.TRENDING_UP
        else:
            result.regime = MarketRegime.TRENDING_DOWN
        result.should_trade = True
        result.recommendation = "روند قوی - بهترین زمان برای trend-following"
        confidence_score = 0.8

    elif adx < 20 and 0.4 < hurst_val < 0.6:
        result.regime = MarketRegime.RANGING
        result.should_trade = True
        result.recommendation = "بازار رنج - از mean-reversion استفاده کنید"
        confidence_score = 0.6

    elif bb_p > 0.9:
        result.regime = MarketRegime.VOLATILE
        result.should_trade = False
        result.recommendation = "نوسان شدید - احتیاط، ریسک بالا"
        confidence_score = 0.7

    elif bb_p < 0.1 and adx < 20:
        result.regime = MarketRegime.QUIET
        result.should_trade = False
        result.recommendation = "بازار آرام - صبر کنید تا حرکت بزرگ"
        confidence_score = 0.6

    elif hurst_val < 0.4:
        result.regime = MarketRegime.CHOPPY
        result.should_trade = False
        result.recommendation = "بازار هرج و مرج - از معامله خودداری کنید"
        confidence_score = 0.5

    else:
        result.regime = MarketRegime.RANGING
        result.should_trade = True
        result.recommendation = "بازار متعادل - با احتیاط معامله کنید"
        confidence_score = 0.4

    result.confidence = confidence_score
    return result


def format_regime_report(regime: RegimeResult) -> str:
    """قالب‌بندی گزارش رژیم بازار."""
    lines: List[str] = []
    lines.append("=" * 50)
    lines.append("  📊 رژیم بازار")
    lines.append("=" * 50)
    lines.append(f"  فاز: {regime.regime.value}")
    lines.append(f"  ADX: {regime.adx:.2f}")
    lines.append(f"  Hurst: {regime.hurst:.3f}")
    lines.append(f"  BB Width Percentile: {regime.bollinger_width_percentile:.2f}")
    lines.append(f"  نوسان: {regime.volatility_regime}")
    lines.append(f"  توصیه: {regime.recommendation}")
    lines.append(f"  معامله: {'✅ بله' if regime.should_trade else '❌ خیر'}")
    lines.append(f"  اطمینان: {regime.confidence*100:.0f}%")
    lines.append("=" * 50)
    return "\n".join(lines)
