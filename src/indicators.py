"""
indicators.py
محاسبه اندیکاتورهای تکنیکال: RSI (Wilder)، MACD، MA، ATR، Bollinger Bands و افزایش حجم.
Computes technical indicators: Wilder RSI, MACD, MA, ATR, Bollinger Bands and volume surge.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_prev = sum(values[:period]) / period  # SMA as seed
    for value in values[period:]:
        ema_prev = (value - ema_prev) * multiplier + ema_prev
    return ema_prev


# --------------------------------------------------------------------------- #
# RSI (Wilder's smoothing) - اصلاح شده
# --------------------------------------------------------------------------- #
def rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    محاسبه Relative Strength Index با روش هموارسازی ویلدر (Wilder's smoothing).
    این روش استاندارد صنعتی است و در اکثر پلتفرم‌های معاملاتی استفاده می‌شود.

    RSI < 30 → اشباع فروش (بالقوه خرید)
    RSI > 70 → اشباع خرید (بالقوه فروش)
    """
    if len(prices) < period + 1:
        return None

    # محاسبه تغییرات قیمت
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # جدا کردن سود و زیان
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    # مقدار اولیه: میانگین ساده دوره اول
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # هموارسازی ویلدر: avg = (prev_avg * (period - 1) + current) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# --------------------------------------------------------------------------- #
# MACD
# --------------------------------------------------------------------------- #
@dataclass
class MACDResult:
    macd_line: float
    signal_line: float
    histogram: float
    bullish: bool  # MACD بالاتر از signal → صعودی


def macd(prices: List[float],
         fast: int = 12,
         slow: int = 26,
         signal: int = 9) -> Optional[MACDResult]:
    """
    محاسبه MACD.
    هیستوگرام مثبت → فشار خرید، منفی → فشار فروش.
    """
    if len(prices) < slow + signal:
        return None

    mult_fast = 2 / (fast + 1)
    mult_slow = 2 / (slow + 1)

    # محاسبه EMA برای کل سری از روز fast-1 به بعد
    ema_fast_series: List[float] = []
    ema_fast = sum(prices[:fast]) / fast  # seed: SMA از fast روز اول
    for i in range(fast, len(prices)):
        ema_fast = (prices[i] - ema_fast) * mult_fast + ema_fast
        ema_fast_series.append(ema_fast)

    # محاسبه EMA برای کل سری از روز slow-1 به بعد
    ema_slow_series: List[float] = []
    ema_slow = sum(prices[:slow]) / slow  # seed: SMA از slow روز اول
    for i in range(slow, len(prices)):
        ema_slow = (prices[i] - ema_slow) * mult_slow + ema_slow
        ema_slow_series.append(ema_slow)

    # هر دو سری باید هم‌فاز باشند (طول یکسان)
    # ema_fast_series طولانی‌تر است، پس از انتهای آن برش می‌زنیم
    if len(ema_fast_series) > len(ema_slow_series):
        # برش از ابتدا برای هم‌رنگ کردن
        diff = len(ema_fast_series) - len(ema_slow_series)
        ema_fast_series = ema_fast_series[diff:]

    if len(ema_fast_series) < signal:
        return None

    # خط MACD = EMA_fast - EMA_slow
    macd_line_series = [f - s for f, s in zip(ema_fast_series, ema_slow_series)]

    # خط سیگنال = EMA از MACD
    signal_seed = sum(macd_line_series[:signal]) / signal
    signal_line = signal_seed
    mult_sig = 2 / (signal + 1)
    for v in macd_line_series[signal:]:
        signal_line = (v - signal_line) * mult_sig + signal_line

    macd_value = macd_line_series[-1]
    hist = macd_value - signal_line
    return MACDResult(
        macd_line=macd_value,
        signal_line=signal_line,
        histogram=hist,
        bullish=hist > 0,
    )


# --------------------------------------------------------------------------- #
# Moving Average trend
# --------------------------------------------------------------------------- #
@dataclass
class MAResult:
    ma_short: float
    ma_long: float
    bullish_cross: bool


def ma_trend(prices: List[float], short: int = 7, long: int = 21) -> Optional[MAResult]:
    """
    میانگین متحرک کوتاه و بلندمدت برای تشخیص روند.
    MA_short > MA_long → روند صعودی
    """
    ma_s = _sma(prices, short)
    ma_l = _sma(prices, long)
    if ma_s is None or ma_l is None:
        return None
    return MAResult(
        ma_short=ma_s,
        ma_long=ma_l,
        bullish_cross=ma_s > ma_l,
    )


# --------------------------------------------------------------------------- #
# Volume surge
# --------------------------------------------------------------------------- #
def volume_surge(volumes: List[float], lookback: int = 14) -> Optional[float]:
    """
    نسبت حجم امروز به میانگین حجم N روز اخیر.
    مقدار > 2 یعنی حجم دو برابر میانگین = توجه خریداران/فروشندگان.
    """
    if len(volumes) < lookback + 1:
        return None
    avg_vol = sum(volumes[-lookback - 1:-1]) / lookback
    if avg_vol == 0:
        return None
    return volumes[-1] / avg_vol


# --------------------------------------------------------------------------- #
# Price momentum
# --------------------------------------------------------------------------- #
def price_momentum(prices: List[float], window: int = 7) -> Optional[float]:
    """
    درصد تغییر قیمت در N روز اخیر.
    مقدار مثبت = روند صعودی، منفی = نزولی.
    """
    if len(prices) < window + 1:
        return None
    past = prices[-window - 1]
    now = prices[-1]
    if past == 0:
        return None
    return (now - past) / past * 100


# --------------------------------------------------------------------------- #
# ATR (Average True Range) - جدید در V1.1.0
# --------------------------------------------------------------------------- #
@dataclass
class ATRResult:
    atr: float
    atr_percent: float  # نسبت ATR به قیمت (نوسان نسبی)


def atr(highs: List[float], lows: List[float], closes: List[float],
        period: int = 14) -> Optional[ATRResult]:
    """
    محاسبه Average True Range با روش ویلدر.
    نیاز به داده OHLC دارد.
    ATR بالا = نوسان زیاد (ریسک بالا)
    """
    if len(closes) < period + 1 or len(highs) != len(lows) != len(closes):
        return None

    # محاسبه True Range برای هر روز
    tr_values: List[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    # میانگین اولیه ساده
    atr_value = sum(tr_values[:period]) / period
    # هموارسازی ویلدر
    for i in range(period, len(tr_values)):
        atr_value = (atr_value * (period - 1) + tr_values[i]) / period

    # نسبت به قیمت فعلی (نوسان نسبی)
    current_price = closes[-1]
    atr_pct = (atr_value / current_price * 100) if current_price > 0 else 0.0

    return ATRResult(atr=atr_value, atr_percent=atr_pct)


# --------------------------------------------------------------------------- #
# Bollinger Bands - جدید در V1.1.0
# --------------------------------------------------------------------------- #
@dataclass
class BollingerResult:
    upper: float
    middle: float
    lower: float
    bandwidth: float       # عرض باندها (نوسان)
    percent_b: float       # موقعیت قیمت فعلی (0=پایین، 1=بالا)
    squeeze: bool          # آیا باندها فشرده شده‌اند (نوسان کم → احتمال شکست)


def bollinger_bands(prices: List[float], period: int = 20,
                    std_dev: float = 2.0) -> Optional[BollingerResult]:
    """
    محاسبه Bollinger Bands.
    - قیمت نزدیک باندهای پایین → اشباع فروش
    - قیمت نزدیک باندهای بالا → اشباع خرید
    - bandwidth کم → فشار (squeeze) → احتمال حرکت بزرگ
    """
    if len(prices) < period:
        return None

    # میانگین متحرک و انحراف معیار
    recent = prices[-period:]
    middle = sum(recent) / period
    variance = sum((p - middle) ** 2 for p in recent) / period
    std = math.sqrt(variance)

    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bandwidth = (upper - lower) / middle if middle > 0 else 0.0

    # موقعیت قیمت فعلی (0 تا 1)
    current = prices[-1]
    if upper == lower:
        percent_b = 0.5
    else:
        percent_b = (current - lower) / (upper - lower)

    # تشخیص squeeze: bandwidth کمتر از میانگین 5 دوره اخیر
    # (تقریبی: اگر bandwidth < 0.1، squeeze در نظر گرفته می‌شود)
    squeeze = bandwidth < 0.1

    return BollingerResult(
        upper=upper,
        middle=middle,
        lower=lower,
        bandwidth=bandwidth,
        percent_b=percent_b,
        squeeze=squeeze,
    )


# --------------------------------------------------------------------------- #
# Aggregated indicator pack
# --------------------------------------------------------------------------- #
@dataclass
class IndicatorPack:
    rsi: Optional[float]
    macd: Optional[MACDResult]
    ma: Optional[MAResult]
    volume_surge_ratio: Optional[float]
    price_momentum_pct: Optional[float]
    # جدید در V1.1.0
    atr: Optional[ATRResult] = None
    bollinger: Optional[BollingerResult] = None

    def to_dict(self) -> dict:
        return {
            "rsi": round(self.rsi, 2) if self.rsi is not None else None,
            "macd_line": round(self.macd.macd_line, 6) if self.macd else None,
            "macd_signal": round(self.macd.signal_line, 6) if self.macd else None,
            "macd_hist": round(self.macd.histogram, 6) if self.macd else None,
            "ma_short": round(self.ma.ma_short, 4) if self.ma else None,
            "ma_long": round(self.ma.ma_long, 4) if self.ma else None,
            "ma_bullish": self.ma.bullish_cross if self.ma else None,
            "volume_surge_ratio": round(self.volume_surge_ratio, 2) if self.volume_surge_ratio is not None else None,
            "price_momentum_pct": round(self.price_momentum_pct, 2) if self.price_momentum_pct is not None else None,
            "atr": round(self.atr.atr, 6) if self.atr else None,
            "atr_percent": round(self.atr.atr_percent, 2) if self.atr else None,
            "bollinger_upper": round(self.bollinger.upper, 6) if self.bollinger else None,
            "bollinger_lower": round(self.bollinger.lower, 6) if self.bollinger else None,
            "bollinger_percent_b": round(self.bollinger.percent_b, 3) if self.bollinger else None,
            "bollinger_squeeze": self.bollinger.squeeze if self.bollinger else None,
        }


def compute_indicators(prices: List[float],
                       volumes: List[float],
                       highs: Optional[List[float]] = None,
                       lows: Optional[List[float]] = None) -> IndicatorPack:
    """
    محاسبه تمام اندیکاتورها در یک فراخوانی.
    اگر highs/lows داده شود، ATR هم محاسبه می‌شود.
    """
    from .config import settings

    pack = IndicatorPack(
        rsi=rsi(prices, period=14),
        macd=macd(prices),
        ma=ma_trend(prices),
        volume_surge_ratio=volume_surge(volumes),
        price_momentum_pct=price_momentum(prices, window=7),
    )

    # اندیکاتورهای اختیاری پیشرفته
    if settings.ENABLE_ATR and highs is not None and lows is not None:
        pack.atr = atr(highs, lows, prices, period=14)
    if settings.ENABLE_BOLLINGER:
        pack.bollinger = bollinger_bands(prices, period=20, std_dev=2.0)

    return pack
