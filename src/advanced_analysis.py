"""
advanced_analysis.py
ماژول‌های تحلیل پیشرفته: لیکوییدیتی، سوییپ، اردرفلو، والیوم پروفایل.

V1.3.0 - تغییرات اساسی:
  - اضافه شدن لایه واقعی Binance برای OrderFlow و Liquidity
  - برچسب «پروکسی/تقریبی» در تمام نتایج
  - ترکیب داده‌های واقعی و تقریبی به‌صورت هوشمند
  - تأثیر اختیاری سیگنال‌های پیشرفته روی امتیاز

طبقات داده:
  1. داده واقعی (Binance aggTrades + depth): برای کوین‌های لیست‌شده در CEX
  2. داده تقریبی (CoinGecko + heuristics): برای کوین‌های فقط DEX

برچسب‌های شفافیت:
  - "واقعی (Binance)": داده واقعی از Binance API
  - "پروکسی (CoinGecko)": تقریبی بر اساس داده CoinGecko
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


# --------------------------------------------------------------------------- #
# 1. Liquidity Analysis
# --------------------------------------------------------------------------- #
@dataclass
class LiquidityResult:
    """نتیجه تحلیل لیکوییدیتی."""
    avg_volume_30d: float
    liquidity_score: float                # 0..1
    is_liquid: bool
    spread_estimate: float                # درصد
    # V1.3.0 - فیلدهای جدید
    is_real: bool = False                 # آیا داده واقعی است؟
    source: str = "CoinGecko volume-based"  # منبع داده
    proxy_label: str = "پروکسی (CoinGecko volume-based)"
    bid_depth_usd: Optional[float] = None
    ask_depth_usd: Optional[float] = None
    imbalance: Optional[float] = None     # -1..1
    notes: List[str] = field(default_factory=list)


def analyze_liquidity(volumes: List[float], prices: List[float],
                      real_liquidity: Optional[Any] = None) -> Optional[LiquidityResult]:
    """
    تحلیل لیکوییدیتی.

    اگر real_liquidity (از Binance) موجود باشد، از آن استفاده می‌شود.
    در غیر این صورت، از حجم CoinGecko به‌عنوان پروکسی استفاده می‌شود.
    """
    if real_liquidity is not None:
        # داده واقعی از Binance depth
        # تبدیل imbalance به امتیاز: imbalance مثبت = خریداران قوی‌تر = خوب
        imb = real_liquidity.imbalance
        # امتیاز بر اساس عدم تعادل (imbalance بین -1 و 1)
        if imb > 0.3:
            score = 0.8  # خریداران بسیار قوی
        elif imb > 0.1:
            score = 0.7
        elif imb > -0.1:
            score = 0.6  # متعادل
        elif imb > -0.3:
            score = 0.45
        else:
            score = 0.3  # فروشندگان قوی

        # اسپرد کم = لیکوییدیتی بهتر
        if real_liquidity.spread_pct < 0.1:
            score = min(1.0, score + 0.1)
        elif real_liquidity.spread_pct > 1.0:
            score = max(0.0, score - 0.2)

        is_liquid = real_liquidity.total_depth_usd > 100_000

        notes = list(real_liquidity.notes)
        notes.append(f"منبع: واقعی (Binance depth)")

        return LiquidityResult(
            avg_volume_30d=0.0,  # در داده واقعی مرتبط نیست
            liquidity_score=score,
            is_liquid=is_liquid,
            spread_estimate=real_liquidity.spread_pct,
            is_real=True,
            source="Binance depth",
            proxy_label=settings.get_proxy_label("liquidity_binance"),
            bid_depth_usd=real_liquidity.bid_depth_usd,
            ask_depth_usd=real_liquidity.ask_depth_usd,
            imbalance=imb,
            notes=notes,
        )

    # داده تقریبی از CoinGecko
    if len(volumes) < 14 or len(prices) < 14:
        return None

    avg_vol = sum(volumes[-30:]) / min(30, len(volumes))

    # امتیاز لیکوییدیتی بر اساس حجم دلاری (پروکسی)
    if avg_vol >= 10_000_000:
        score = 0.9
        spread = 0.1
    elif avg_vol >= 1_000_000:
        score = 0.7
        spread = 0.3
    elif avg_vol >= 100_000:
        score = 0.5
        spread = 0.7
    elif avg_vol >= 10_000:
        score = 0.3
        spread = 1.5
    else:
        score = 0.15
        spread = 3.0

    is_liquid = avg_vol >= 100_000

    notes: List[str] = []
    if avg_vol >= 10_000_000:
        notes.append("لیکوییدیتی عالی (پروکسی حجم)")
    elif avg_vol >= 1_000_000:
        notes.append("لیکوییدیتی مناسب (پروکسی حجم)")
    elif avg_vol >= 100_000:
        notes.append("لیکوییدیتی متوسط (پروکسی حجم)")
    else:
        notes.append("لیکوییدیتی ضعیف (پروکسی حجم)")
    notes.append(f"منبع: پروکسی (CoinGecko volume-based)")

    return LiquidityResult(
        avg_volume_30d=avg_vol,
        liquidity_score=score,
        is_liquid=is_liquid,
        spread_estimate=spread,
        is_real=False,
        source="CoinGecko volume-based",
        proxy_label=settings.get_proxy_label("liquidity_cg"),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# 2. Sweep Analysis (تقریبی - بر اساس OHLC)
# --------------------------------------------------------------------------- #
@dataclass
class SweepResult:
    """نتیجه تحلیل سوییپ - همیشه پروکسی (OHLC-based)."""
    sweep_detected: bool
    sweep_type: str
    sweep_price: Optional[float]
    recovery: bool
    strength: float
    is_real: bool = False
    source: str = "OHLC-based heuristic"
    proxy_label: str = "پروکسی (OHLC-based)"
    notes: List[str] = field(default_factory=list)


def analyze_sweep(prices: List[float], highs: List[float], lows: List[float]) -> Optional[SweepResult]:
    """
    تشخیص سوییپ لیکوییدیتی (پروکسی).

    توجه: این تحلیل تقریبی است چون داده order book tick-by-tick ندارد.
    برای تشخیص واقعی سوییپ، نیاز به داده real-time order book داریم.
    """
    if len(prices) < 5 or len(highs) < 5 or len(lows) < 5:
        return None

    recent_highs = highs[-5:]
    recent_lows = lows[-5:]
    recent_prices = prices[-5:]

    prev_high = max(recent_highs[:-1])
    prev_low = min(recent_lows[:-1])

    last_high = recent_highs[-1]
    last_low = recent_lows[-1]
    last_price = recent_prices[-1]

    sweep_detected = False
    sweep_type = ""
    sweep_price = None
    recovery = False
    strength = 0.0

    if last_high > prev_high and last_price < prev_high:
        sweep_detected = True
        sweep_type = "high_sweep"
        sweep_price = last_high
        recovery = True
        overshoot = (last_high - prev_high) / prev_high if prev_high > 0 else 0
        strength = min(1.0, 0.5 + overshoot * 10)
    elif last_low < prev_low and last_price > prev_low:
        sweep_detected = True
        sweep_type = "low_sweep"
        sweep_price = last_low
        recovery = True
        overshoot = (prev_low - last_low) / prev_low if prev_low > 0 else 0
        strength = min(1.0, 0.5 + overshoot * 10)

    notes: List[str] = []
    if sweep_detected:
        if sweep_type == "low_sweep":
            notes.append(f"سوییپ پایینی - شکست کف {sweep_price:.6f} و بازگشت")
            notes.append("نشانه جمع‌آوری (Smart Money proxy)")
        elif sweep_type == "high_sweep":
            notes.append(f"سوییپ بالایی - شکست سقف {sweep_price:.6f} و بازگشت")
            notes.append("نشانه توزیع (Smart Money proxy)")
    notes.append(f"منبع: پروکسی (OHLC-based)")

    return SweepResult(
        sweep_detected=sweep_detected,
        sweep_type=sweep_type if sweep_detected else "none",
        sweep_price=sweep_price,
        recovery=recovery,
        strength=strength,
        is_real=False,
        source="OHLC-based heuristic",
        proxy_label=settings.get_proxy_label("sweep"),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# 3. Order Flow Analysis (واقعی یا تقریبی)
# --------------------------------------------------------------------------- #
@dataclass
class OrderFlowResult:
    """نتیجه تحلیل اردرفلو."""
    buy_pressure: float
    sell_pressure: float
    delta: float                          # خرید - فروش (یکا: مقدار raw)
    cumulative_delta: float
    absorption: bool
    # V1.3.0 - فیلدهای جدید
    is_real: bool = False
    source: str = "CoinGecko price-direction heuristic"
    proxy_label: str = "پروکسی (price-direction)"
    large_trades_count: int = 0
    large_buys: int = 0
    large_sells: int = 0
    large_trade_volume: float = 0.0
    notes: List[str] = field(default_factory=list)


def analyze_orderflow(prices: List[float], volumes: List[float],
                      real_orderflow: Optional[Any] = None) -> Optional[OrderFlowResult]:
    """
    تحلیل اردرفلو.

    اگر real_orderflow (از Binance aggTrades) موجود باشد، از آن استفاده می‌شود.
    در غیر این صورت، از جهت قیمت به‌عنوان پروکسی استفاده می‌شود.
    """
    if real_orderflow is not None:
        # داده واقعی از Binance aggTrades
        notes = list(real_orderflow.notes)
        notes.append(f"منبع: واقعی (Binance aggTrades)")

        return OrderFlowResult(
            buy_pressure=real_orderflow.buy_pressure,
            sell_pressure=real_orderflow.sell_pressure,
            delta=real_orderflow.cvd,
            cumulative_delta=real_orderflow.cvd,
            absorption=False,  # در داده واقعی قابل محاسبه است
            is_real=True,
            source="Binance aggTrades",
            proxy_label=settings.get_proxy_label("orderflow_binance"),
            large_trades_count=real_orderflow.large_trades_count,
            large_buys=real_orderflow.large_buys,
            large_sells=real_orderflow.large_sells,
            large_trade_volume=real_orderflow.large_trade_volume,
            notes=notes,
        )

    # داده تقریبی از CoinGecko
    if len(prices) < 7 or len(volumes) < 7:
        return None

    buy_vol = 0.0
    sell_vol = 0.0
    delta_sum = 0.0

    for i in range(1, min(len(prices), len(volumes))):
        price_change = prices[i] - prices[i - 1]
        vol = volumes[i]

        if price_change > 0:
            buy_vol += vol
            delta_sum += vol
        elif price_change < 0:
            sell_vol += vol
            delta_sum -= vol

    total_vol = buy_vol + sell_vol
    if total_vol == 0:
        return None

    buy_pressure = buy_vol / total_vol
    sell_pressure = sell_vol / total_vol
    delta = (buy_vol - sell_vol) / 1_000_000
    cumulative_delta = delta_sum / 1_000_000

    absorption = False
    if buy_pressure > 0.6 and prices[-1] < prices[0]:
        absorption = True
    elif sell_pressure > 0.6 and prices[-1] > prices[0]:
        absorption = True

    notes: List[str] = []
    if buy_pressure > 0.65:
        notes.append(f"فشار خرید تقریبی ({buy_pressure*100:.0f}%)")
    elif sell_pressure > 0.65:
        notes.append(f"فشار فروش تقریبی ({sell_pressure*100:.0f}%)")
    if absorption:
        notes.append("جذب سفارش (Absorption)")
    notes.append(f"منبع: پروکسی (price-direction heuristic)")

    return OrderFlowResult(
        buy_pressure=buy_pressure,
        sell_pressure=sell_pressure,
        delta=delta,
        cumulative_delta=cumulative_delta,
        absorption=absorption,
        is_real=False,
        source="CoinGecko price-direction heuristic",
        proxy_label=settings.get_proxy_label("orderflow_cg"),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# 4. Volume Profile Analysis
# --------------------------------------------------------------------------- #
@dataclass
class VolumeProfileResult:
    """نتیجه تحلیل والیوم پروفایل - همیشه پروکسی."""
    poc_price: float
    vah: float
    val: float
    value_area_pct: float
    profile_shape: str
    is_real: bool = False
    source: str = "price-binned"
    proxy_label: str = "پروکسی (price-binned)"
    notes: List[str] = field(default_factory=list)


def analyze_volume_profile(prices: List[float], volumes: List[float],
                            bins: int = 20) -> Optional[VolumeProfileResult]:
    """تحلیل والیوم پروفایل - تقریبی."""
    if len(prices) < 14 or len(volumes) < 14:
        return None

    min_price = min(prices)
    max_price = max(prices)
    if max_price == min_price:
        return None

    bin_size = (max_price - min_price) / bins
    volume_at_price = [0.0] * bins

    for i, price in enumerate(prices):
        if i >= len(volumes):
            break
        bin_idx = min(int((price - min_price) / bin_size), bins - 1)
        volume_at_price[bin_idx] += volumes[i]

    poc_bin = volume_at_price.index(max(volume_at_price))
    poc_price = min_price + (poc_bin + 0.5) * bin_size

    total_vol = sum(volume_at_price)
    if total_vol == 0:
        return None

    target_vol = total_vol * 0.7
    current_vol = volume_at_price[poc_bin]
    low_bin = poc_bin
    high_bin = poc_bin

    while current_vol < target_vol and (low_bin > 0 or high_bin < bins - 1):
        extend_low = volume_at_price[low_bin - 1] if low_bin > 0 else 0
        extend_high = volume_at_price[high_bin + 1] if high_bin < bins - 1 else 0
        if extend_low >= extend_high and low_bin > 0:
            low_bin -= 1
            current_vol += extend_low
        elif high_bin < bins - 1:
            high_bin += 1
            current_vol += extend_high
        else:
            break

    val = min_price + low_bin * bin_size
    vah = min_price + (high_bin + 1) * bin_size
    value_area_pct = current_vol / total_vol

    avg_low = sum(volume_at_price[:bins // 3]) / (bins // 3)
    avg_mid = sum(volume_at_price[bins // 3:2 * bins // 3]) / (bins // 3)
    avg_high = sum(volume_at_price[2 * bins // 3:]) / (bins - 2 * bins // 3)

    if avg_low > avg_high * 1.5:
        profile_shape = "p_shape"
    elif avg_high > avg_low * 1.5:
        profile_shape = "b_shape"
    elif avg_mid > avg_low * 1.5 and avg_mid > avg_high * 1.5:
        profile_shape = "d_shape"
    else:
        profile_shape = "normal"

    notes: List[str] = []
    notes.append(f"POC: {poc_price:.6f} - بیشترین حجم در این سطح")
    if profile_shape == "p_shape":
        notes.append("شکل P - تجمیع در پایین")
    elif profile_shape == "b_shape":
        notes.append("شکل B - توزیع در بالا")
    notes.append(f"منبع: پروکسی (price-binned)")

    current_price = prices[-1]
    if val <= current_price <= vah:
        notes.append("قیمت در Value Area (متعادل)")
    elif current_price > vah:
        notes.append("قیمت بالای Value Area (صعودی)")
    else:
        notes.append("قیمت زیر Value Area (نزولی)")

    return VolumeProfileResult(
        poc_price=poc_price,
        vah=vah,
        val=val,
        value_area_pct=value_area_pct,
        profile_shape=profile_shape,
        is_real=False,
        source="price-binned",
        proxy_label=settings.get_proxy_label("volume_profile"),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Multi-Timeframe Confluence
# --------------------------------------------------------------------------- #
@dataclass
class MTFConfluenceResult:
    """نتیجه تحلیل هم‌جهتی چند بازه زمانی."""
    timeframes: Dict[str, str] = field(default_factory=dict)  # tf → bullish/bearish/neutral
    aligned_count: int = 0
    total_count: int = 0
    confluence_score: float = 0.5  # 0..1 (0.5 = خنثی)
    notes: List[str] = field(default_factory=list)


def analyze_mtf_confluence(mtf_data: Dict[str, List]) -> Optional[MTFConfluenceResult]:
    """
    تحلیل هم‌جهتی چند بازه زمانی.

    مکانیزم: برای هر بازه، روند صعودی/نزولی را با MA تشخیص می‌دهیم.
    اگر اکثر بازه‌ها هم‌جهت باشند → confluence قوی.
    """
    if not mtf_data or len(mtf_data) < 1:
        return None

    from .indicators import ma_trend

    tf_signals: Dict[str, str] = {}
    aligned_bullish = 0
    aligned_bearish = 0
    total = 0

    for tf, klines in mtf_data.items():
        if not klines or len(klines) < 21:
            continue
        # استخراج قیمت‌های close از klines
        closes = []
        for k in klines:
            try:
                closes.append(float(k[4]))  # index 4 = close
            except (ValueError, IndexError, TypeError):
                continue
        if len(closes) < 21:
            continue

        ma_result = ma_trend(closes, short=7, long=21)
        if ma_result is None:
            tf_signals[tf] = "neutral"
            continue

        if ma_result.bullish_cross:
            tf_signals[tf] = "bullish"
            aligned_bullish += 1
        else:
            tf_signals[tf] = "bearish"
            aligned_bearish += 1
        total += 1

    if total == 0:
        return None

    # محاسبه امتیاز confluence
    if aligned_bullish >= settings.MTF_CONFLUENCE_MIN:
        score = 0.7 + (aligned_bullish - settings.MTF_CONFLUENCE_MIN) * 0.1
    elif aligned_bearish >= settings.MTF_CONFLUENCE_MIN:
        score = 0.3 - (aligned_bearish - settings.MTF_CONFLUENCE_MIN) * 0.1
    else:
        score = 0.5

    score = max(0.1, min(0.9, score))

    notes: List[str] = []
    aligned_count = max(aligned_bullish, aligned_bearish)
    if aligned_count >= settings.MTF_CONFLUENCE_MIN:
        direction = "صعودی" if aligned_bullish > aligned_bearish else "نزولی"
        notes.append(f"Confluence {direction} در {aligned_count}/{total} بازه")
    else:
        notes.append(f"بدون confluence قوی ({aligned_bullish}B / {aligned_bearish}S از {total})")

    return MTFConfluenceResult(
        timeframes=tf_signals,
        aligned_count=aligned_count,
        total_count=total,
        confluence_score=score,
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Aggregated advanced pack
# --------------------------------------------------------------------------- #
@dataclass
class AdvancedAnalysisPack:
    """بسته تحلیل‌های پیشرفته."""
    liquidity: Optional[LiquidityResult] = None
    sweep: Optional[SweepResult] = None
    orderflow: Optional[OrderFlowResult] = None
    volume_profile: Optional[VolumeProfileResult] = None
    mtf_confluence: Optional[MTFConfluenceResult] = None  # V1.3.0

    def to_dict(self) -> dict:
        return {
            "liquidity_score": round(self.liquidity.liquidity_score, 3) if self.liquidity else None,
            "liquidity_is_real": self.liquidity.is_real if self.liquidity else None,
            "liquidity_source": self.liquidity.source if self.liquidity else None,
            "liquidity_proxy_label": self.liquidity.proxy_label if self.liquidity else None,
            "is_liquid": self.liquidity.is_liquid if self.liquidity else None,
            "spread_estimate": round(self.liquidity.spread_estimate, 3) if self.liquidity else None,
            "liquidity_imbalance": round(self.liquidity.imbalance, 3) if self.liquidity and self.liquidity.imbalance is not None else None,
            "sweep_detected": self.sweep.sweep_detected if self.sweep else None,
            "sweep_type": self.sweep.sweep_type if self.sweep else None,
            "sweep_strength": round(self.sweep.strength, 3) if self.sweep else None,
            "sweep_proxy_label": self.sweep.proxy_label if self.sweep else None,
            "buy_pressure": round(self.orderflow.buy_pressure, 3) if self.orderflow else None,
            "sell_pressure": round(self.orderflow.sell_pressure, 3) if self.orderflow else None,
            "orderflow_is_real": self.orderflow.is_real if self.orderflow else None,
            "orderflow_source": self.orderflow.source if self.orderflow else None,
            "orderflow_proxy_label": self.orderflow.proxy_label if self.orderflow else None,
            "cumulative_delta": round(self.orderflow.cumulative_delta, 3) if self.orderflow else None,
            "large_trades_count": self.orderflow.large_trades_count if self.orderflow else None,
            "large_buys": self.orderflow.large_buys if self.orderflow else None,
            "large_sells": self.orderflow.large_sells if self.orderflow else None,
            "orderflow_absorption": self.orderflow.absorption if self.orderflow else None,
            "poc_price": round(self.volume_profile.poc_price, 6) if self.volume_profile else None,
            "vah": round(self.volume_profile.vah, 6) if self.volume_profile else None,
            "val": round(self.volume_profile.val, 6) if self.volume_profile else None,
            "value_area_pct": round(self.volume_profile.value_area_pct, 3) if self.volume_profile else None,
            "profile_shape": self.volume_profile.profile_shape if self.volume_profile else None,
            "mtf_confluence_score": round(self.mtf_confluence.confluence_score, 3) if self.mtf_confluence else None,
            "mtf_aligned_count": self.mtf_confluence.aligned_count if self.mtf_confluence else None,
            "mtf_total_count": self.mtf_confluence.total_count if self.mtf_confluence else None,
        }

    def get_all_notes(self) -> List[str]:
        """دریافت همه یادداشت‌های تحلیل پیشرفته."""
        notes: List[str] = []
        if self.liquidity:
            notes.extend(self.liquidity.notes)
        if self.sweep and self.sweep.sweep_detected:
            notes.extend(self.sweep.notes)
        if self.orderflow:
            notes.extend(self.orderflow.notes)
        if self.volume_profile:
            notes.extend(self.volume_profile.notes)
        if self.mtf_confluence:
            notes.extend(self.mtf_confluence.notes)
        return notes

    def get_data_source_summary(self) -> str:
        """خلاصه منابع داده استفاده شده."""
        real_count = 0
        proxy_count = 0
        if self.liquidity:
            if self.liquidity.is_real:
                real_count += 1
            else:
                proxy_count += 1
        if self.orderflow:
            if self.orderflow.is_real:
                real_count += 1
            else:
                proxy_count += 1
        # Sweep و VP همیشه پروکسی هستند
        if self.sweep:
            proxy_count += 1
        if self.volume_profile:
            proxy_count += 1
        return f"{real_count} واقعی + {proxy_count} پروکسی"


def compute_advanced_analysis(prices: List[float],
                              volumes: List[float],
                              highs: Optional[List[float]] = None,
                              lows: Optional[List[float]] = None,
                              real_orderflow: Optional[Any] = None,
                              real_liquidity: Optional[Any] = None,
                              mtf_data: Optional[Dict[str, List]] = None) -> AdvancedAnalysisPack:
    """
    اجرای تمام تحلیل‌های پیشرفته.

    V1.3.0 - اکنون از داده واقعی Binance (اگر موجود باشد) استفاده می‌کند.
    """
    pack = AdvancedAnalysisPack()

    if settings.ENABLE_LIQUIDITY:
        pack.liquidity = analyze_liquidity(volumes, prices, real_liquidity=real_liquidity)
    if settings.ENABLE_SWEEP and highs is not None and lows is not None:
        pack.sweep = analyze_sweep(prices, highs, lows)
    if settings.ENABLE_ORDERFLOW:
        pack.orderflow = analyze_orderflow(prices, volumes, real_orderflow=real_orderflow)
    if settings.ENABLE_VOLUME_PROFILE:
        pack.volume_profile = analyze_volume_profile(prices, volumes)
    if settings.ENABLE_MULTI_TIMEFRAME and mtf_data:
        pack.mtf_confluence = analyze_mtf_confluence(mtf_data)

    return pack
