"""
analyzer.py
ترکیب اندیکاتورها و صدور سیگنال خرید/فروش/نگه‌داری.
Combines indicators into a Buy/Sell/Hold signal with score.

V1.2.0 - نرمال‌سازی MACD با ATR + تأثیر صریح ATR و Bollinger روی امتیاز.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .config import settings
from .indicators import IndicatorPack


logger = logging.getLogger(settings.PROJECT_SLUG)


class Signal(str, Enum):
    BUY = "خرید"
    SELL = "فروش"
    HOLD = "نگه‌داری"


# --------------------------------------------------------------------------- #
# per-factor scorers (each returns 0..1 where 1 = strong buy)
# --------------------------------------------------------------------------- #
def _rsi_score(rsi_val: Optional[float]) -> float:
    if rsi_val is None:
        return 0.5
    if rsi_val < 30:
        return 0.85
    if rsi_val < 45:
        return 0.65
    if rsi_val < 55:
        return 0.5
    if rsi_val < 70:
        return 0.35
    return 0.15


def _macd_score(pack: IndicatorPack) -> float:
    """
    امتیاز MACD با نرمال‌سازی بر اساس ATR - V1.2.0.
    MACD هیستوگرام نسبت به نوسان بازار (ATR) ارزیابی می‌شود.
    اگر ATR در دسترس نباشد، از قیمت فعلی استفاده می‌شود.
    """
    if pack.macd is None:
        return 0.5

    hist = pack.macd.histogram

    # نرمال‌سازی با ATR (ترجیحی)
    if pack.atr is not None and pack.atr.atr > 0:
        normalized = hist / pack.atr.atr
    # یا نرمال‌سازی با قیمت فعلی (پشتیبان)
    elif pack.ma is not None and pack.ma.ma_short > 0:
        normalized = hist / pack.ma.ma_short
    else:
        # در صورت نبود مرجع، از tanh استفاده کن
        normalized = math.tanh(hist * 1e6)

    # نرمال‌سازی نهایی با tanh
    return 0.5 + 0.5 * math.tanh(normalized)


def _volume_score(ratio: Optional[float]) -> float:
    if ratio is None:
        return 0.5
    if ratio >= 3:
        return 0.9
    if ratio >= 2:
        return 0.75
    if ratio >= 1.2:
        return 0.6
    if ratio >= 0.8:
        return 0.45
    return 0.3


def _momentum_score(pct: Optional[float]) -> float:
    if pct is None:
        return 0.5
    if pct >= 30:
        return 0.9
    if pct >= 10:
        return 0.7
    if pct >= 0:
        return 0.55
    if pct >= -10:
        return 0.4
    if pct >= -30:
        return 0.25
    return 0.1


def _ma_score(pack: IndicatorPack) -> float:
    """
    امتیاز بر اساس MA Trend.
    MA_short > MA_long → صعودی → امتیاز بالا
    """
    if pack.ma is None:
        return 0.5
    if pack.ma.bullish_cross:
        return 0.75
    return 0.25


def _atr_score(pack: IndicatorPack) -> float:
    """
    امتیاز بر اساس ATR - V1.2.0 (تأثیر صریح روی امتیاز نهایی).
    نوسان متوسط = خوب (0.7-0.9)، نوسان خیلی کم یا خیلی زیاد = بد.
    """
    if pack.atr is None:
        return 0.5
    pct = pack.atr.atr_percent
    # نوسان متوسط (5-15%) بهترین برای معامله
    if 5 <= pct <= 15:
        return 0.7
    # نوسان کم (1-5%) - آرامش بازار
    if 1 <= pct < 5:
        return 0.55
    # نوسان زیاد (15-30%) - ریسک بالا ولی فرصت
    if 15 < pct <= 30:
        return 0.45
    # نوسان بسیار زیاد (>30%) - خطرناک
    if pct > 30:
        return 0.25
    # نوسان بسیار کم (<1%) - بازار مرده
    return 0.35


def _bollinger_score(pack: IndicatorPack) -> float:
    """
    امتیاز بر اساس Bollinger Bands - V1.2.0 (تأثیر صریح روی امتیاز نهایی).
    قیمت نزدیک باند پایین = اشباع فروش = خرید بالقوه
    قیمت نزدیک باند بالا = اشباع خرید = فروش
    """
    if pack.bollinger is None:
        return 0.5
    pb = pack.bollinger.percent_b
    # percent_b < 0.2 → قیمت نزدیک باند پایین → خرید
    if pb < 0.2:
        return 0.8
    if pb < 0.4:
        return 0.65
    if pb < 0.6:
        return 0.5
    if pb < 0.8:
        return 0.35
    return 0.2  # percent_b >= 0.8 → اشباع خرید → فروش


# --------------------------------------------------------------------------- #
# analyzer
# --------------------------------------------------------------------------- #
@dataclass
class AnalysisResult:
    coin_id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    volume_24h: float
    change_24h_pct: float
    change_7d_pct: float
    score: float                       # 0..1
    signal: Signal
    confidence: float                  # 0..1
    reasons: list = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    # V1.3.0 - داده‌های پیشرفته
    advanced: dict = field(default_factory=dict)
    data_sources: str = ""             # خلاصه منابع داده
    telegram_message_id: object = None  # message_id تلگرام برای ریپلای بعدی

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
            "reasons": self.reasons,
            "indicators": self.indicators,
            "advanced": self.advanced,
            "data_sources": self.data_sources,
            "telegram_message_id": self.telegram_message_id,
        }


def analyze_coin(coin: dict, indicators: IndicatorPack,
                 advanced_pack: Optional[Any] = None) -> AnalysisResult:
    """
    ترکیب اندیکاتورها و محاسبه امتیاز نهایی و سیگنال.
    V1.3.0 - اکنون از تحلیل پیشرفته (اگر موجود باشد) هم استفاده می‌کند.
    """
    reasons: list = []

    # محاسبه امتیاز هر فاکتور اصلی
    rsi_score = _rsi_score(indicators.rsi)
    macd_score = _macd_score(indicators)
    vol_score = _volume_score(indicators.volume_surge_ratio)
    mom_score = _momentum_score(indicators.price_momentum_pct)
    ma_score = _ma_score(indicators)
    atr_score = _atr_score(indicators)
    bb_score = _bollinger_score(indicators)

    # V1.3.0 - امتیاز اختیاری از تحلیل‌های پیشرفته
    liq_score = 0.5
    of_score = 0.5
    mtf_score = 0.5
    advanced_impact = 0.0  # مجموع وزن‌های فعال

    if advanced_pack is not None and settings.ENABLE_ADVANCED_IMPACT:
        # V1.3.1 - اکنون MTF هم تأثیر دارد
        if advanced_pack.liquidity:
            liq_score = advanced_pack.liquidity.liquidity_score
            advanced_impact += settings.WEIGHT_LIQUIDITY
        if advanced_pack.orderflow:
            # تبدیل buy_pressure به امتیاز (0.5 = خنثی، 1 = خرید قوی)
            of_score = advanced_pack.orderflow.buy_pressure
            advanced_impact += settings.WEIGHT_ORDERFLOW
        if advanced_pack.mtf_confluence:
            mtf_score = advanced_pack.mtf_confluence.confluence_score
            advanced_impact += settings.WEIGHT_MTF_CONFLUENCE

    # دلایل - RSI
    if indicators.rsi is not None:
        if indicators.rsi < 30:
            reasons.append(f"RSI={indicators.rsi:.1f} - اشباع فروش (خرید بالقوه)")
        elif indicators.rsi > 70:
            reasons.append(f"RSI={indicators.rsi:.1f} - اشباع خرید (احتیاط)")
        else:
            reasons.append(f"RSI={indicators.rsi:.1f} - منطقه خنثی")

    # دلایل - MACD
    if indicators.macd is not None:
        if indicators.macd.bullish:
            reasons.append("MACD: هیستوگرام مثبت - فشار خریداران")
        else:
            reasons.append("MACD: هیستوگرام منفی - فشار فروشندگان")

    # دلایل - حجم
    if indicators.volume_surge_ratio is not None:
        if indicators.volume_surge_ratio >= 2:
            reasons.append(f"حجم {indicators.volume_surge_ratio:.1f}x میانگین - توجه ویژه")
        elif indicators.volume_surge_ratio < 0.7:
            reasons.append(f"حجم {indicators.volume_surge_ratio:.1f}x - کاهش علاقه")

    # دلایل - مومنتوم
    if indicators.price_momentum_pct is not None:
        reasons.append(f"مومنتوم 7 روزه: {indicators.price_momentum_pct:+.1f}%")

    # دلایل - MA
    if indicators.ma is not None:
        if indicators.ma.bullish_cross:
            reasons.append("MA صعودی: میانگین کوتاه‌مدت بالاتر از بلندمدت")
        else:
            reasons.append("MA نزولی: میانگین کوتاه‌مدت پایین‌تر از بلندمدت")

    # دلایل - ATR
    if indicators.atr is not None:
        if indicators.atr.atr_percent > 10:
            reasons.append(f"ATR={indicators.atr.atr_percent:.1f}% - نوسان بسیار بالا (ریسک زیاد)")
        elif indicators.atr.atr_percent < 3:
            reasons.append(f"ATR={indicators.atr.atr_percent:.1f}% - نوسان پایین (آرامش بازار)")

    # دلایل - Bollinger Bands
    if indicators.bollinger is not None:
        if indicators.bollinger.percent_b < 0.2:
            reasons.append("Bollinger: قیمت نزدیک باند پایین (اشباع فروش)")
        elif indicators.bollinger.percent_b > 0.8:
            reasons.append("Bollinger: قیمت نزدیک باند بالا (اشباع خرید)")
        if indicators.bollinger.squeeze:
            reasons.append("Bollinger: فشار (squeeze) - احتمال حرکت بزرگ")

    # V1.3.0 - افزودن یادداشت‌های تحلیل پیشرفته به دلایل
    if advanced_pack is not None:
        for note in advanced_pack.get_all_notes():
            reasons.append(note)

    # وزن‌دهی - V1.3.0
    # محاسبه وزن اصلی (7 فاکتور پایه)
    base_weight_sum = (
        settings.WEIGHT_RSI +
        settings.WEIGHT_MACD +
        settings.WEIGHT_VOLUME_SURGE +
        settings.WEIGHT_PRICE_MOMENTUM +
        settings.WEIGHT_MA_TREND +
        settings.WEIGHT_ATR +
        settings.WEIGHT_BOLLINGER
    )

    base_score = (
        rsi_score * settings.WEIGHT_RSI +
        macd_score * settings.WEIGHT_MACD +
        vol_score * settings.WEIGHT_VOLUME_SURGE +
        mom_score * settings.WEIGHT_PRICE_MOMENTUM +
        ma_score * settings.WEIGHT_MA_TREND +
        atr_score * settings.WEIGHT_ATR +
        bb_score * settings.WEIGHT_BOLLINGER
    )

    if advanced_impact > 0:
        # اگر تحلیل پیشرفته فعال است، وزن‌ها را بازتوزیع می‌کنیم
        total_weight = base_weight_sum + advanced_impact
        # نرمال‌سازی: امتیاز اصلی و امتیاز پیشرفته با وزن متناسب
        score = (base_score + liq_score * settings.WEIGHT_LIQUIDITY +
                 of_score * settings.WEIGHT_ORDERFLOW +
                 mtf_score * settings.WEIGHT_MTF_CONFLUENCE) / total_weight
    else:
        # فقط امتیاز اصلی، نرمال‌سازی بر اساس مجموع وزن‌های پایه
        score = base_score / base_weight_sum if base_weight_sum > 0 else 0.5

    # تصمیم سیگنال
    if score >= settings.BUY_THRESHOLD:
        signal = Signal.BUY
    elif score <= settings.SELL_THRESHOLD:
        signal = Signal.SELL
    else:
        signal = Signal.HOLD

    # میزان اطمینان
    confidence = abs(score - 0.5) * 2

    # خلاصه منابع داده
    data_sources = ""
    if advanced_pack is not None:
        data_sources = advanced_pack.get_data_source_summary()

    # داده‌های پیشرفته برای ذخیره در نتیجه
    advanced_dict = {}
    if advanced_pack is not None:
        advanced_dict = advanced_pack.to_dict()

    return AnalysisResult(
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
        reasons=reasons,
        indicators=indicators.to_dict(),
        advanced=advanced_dict,
        data_sources=data_sources,
    )
