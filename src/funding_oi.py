"""
funding_oi.py
Funding Rate و Open Interest از Binance Futures - V2.0

این مهم‌ترین سیگنال رایگان است که هنوز استفاده نمی‌کنیم:
- Funding rate خیلی منفی → short squeeze بالقوه (سیگنال خرید!)
- Funding rate خیلی مثبت → long squeeze بالقوه (سیگنال فروش!)
- OI افزایش + قیمت ثابت → حرکت بزرگ در راه
- OI کاهش + قیمت بالا → short covering

API کاملاً رایگان، بدون نیاز به کلید.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import requests

from .config import settings
from .rate_limiter import get_rate_limiter


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class FundingOIResult:
    """نتیجه تحلیل Funding Rate + Open Interest."""
    symbol: str
    funding_rate: float = 0.0           # درصد (مثلاً 0.01 یعنی 0.01%)
    funding_rate_regime: str = "neutral"  # neutral/extreme_positive/extreme_negative
    open_interest_usd: float = 0.0      # دلار
    open_interest_change_24h: float = 0.0  # درصد تغییر
    # سیگنال‌ها
    short_squeeze_signal: float = 0.5    # 0..1 (high = احتمال short squeeze)
    long_squeeze_signal: float = 0.5      # 0..1 (high = احتمال long squeeze)
    volatility_coming: float = 0.5        # 0..1 (high = حرکت بزرگ در راه)
    # توصیه
    signal_score: float = 0.5            # 0..1 (high = bullish)
    notes: List[str] = field(default_factory=list)
    is_real: bool = True
    source: str = "Binance Futures"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "funding_rate_pct": round(self.funding_rate, 6),
            "funding_regime": self.funding_rate_regime,
            "open_interest_usd": round(self.open_interest_usd, 0),
            "oi_change_24h_pct": round(self.open_interest_change_24h, 2),
            "short_squeeze_signal": round(self.short_squeeze_signal, 3),
            "long_squeeze_signal": round(self.long_squeeze_signal, 3),
            "volatility_coming": round(self.volatility_coming, 3),
            "signal_score": round(self.signal_score, 3),
            "notes": self.notes,
        }


class FundingOIClient:
    """کلاینت Binance Futures API برای funding/OI."""

    def __init__(self) -> None:
        self.base_url = settings.BINANCE_FUTURES_URL
        self.session = requests.Session()
        self.session.headers.update(settings.binance_headers)

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        url = f"{self.base_url}{path}"
        try:
            if not get_rate_limiter().acquire(timeout=30.0):
                return None
            resp = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(2)
                return None
            if resp.status_code != 200:
                return None
            return resp.json()
        except requests.exceptions.RequestException as exc:
            logger.debug("Funding/OI request failed: %s", exc)
            return None

    def _make_symbol(self, coin_symbol: str) -> str:
        """تبدیل نماد به نماد futures."""
        upper = coin_symbol.upper()
        if upper.endswith("USDT"):
            return upper
        return f"{upper}USDT"

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """دریافت funding rate فعلی."""
        sym = self._make_symbol(symbol)
        data = self._get("/fapi/v1/premiumIndex", {"symbol": sym})
        if data and "lastFundingRate" in data:
            try:
                rate = float(data["lastFundingRate"])
                return rate * 100  # تبدیل به درصد
            except (ValueError, TypeError):
                return None
        return None

    def get_open_interest(self, symbol: str) -> Optional[float]:
        """دریافت open interest فعلی (در تعداد قرارداد)."""
        sym = self._make_symbol(symbol)
        data = self._get("/fapi/v1/openInterest", {"symbol": sym})
        if data and "openInterest" in data:
            try:
                return float(data["openInterest"])
            except (ValueError, TypeError):
                return None
        return None

    def get_open_interest_history(self, symbol: str,
                                   period: str = "1d",
                                   limit: int = 2) -> List[Dict]:
        """دریافت تاریخچه open interest."""
        sym = self._make_symbol(symbol)
        data = self._get("/futures/data/openInterestHist",
                         {"symbol": sym, "period": period, "limit": limit})
        if isinstance(data, list):
            return data
        return []

    def analyze(self, symbol: str, current_price: float = 0) -> Optional[FundingOIResult]:
        """
        تحلیل کامل funding/OI برای یک نماد.
        """
        funding = self.get_funding_rate(symbol)
        oi = self.get_open_interest(symbol)
        oi_history = self.get_open_interest_history(symbol, "1d", 2)

        if funding is None and oi is None:
            return None

        result = FundingOIResult(symbol=symbol)

        if funding is not None:
            result.funding_rate = funding
            # تشخیص رژیم funding
            if funding < -0.05:  # خیلی منفی
                result.funding_rate_regime = "extreme_negative"
                result.short_squeeze_signal = 0.85
                result.signal_score = 0.75
                result.notes.append(f"Funding rate {funding:+.4f}% - احتمال short squeeze")
            elif funding < -0.02:
                result.funding_rate_regime = "negative"
                result.short_squeeze_signal = 0.65
                result.signal_score = 0.60
                result.notes.append(f"Funding rate {funding:+.4f}% - bearish positioning")
            elif funding > 0.10:  # خیلی مثبت
                result.funding_rate_regime = "extreme_positive"
                result.long_squeeze_signal = 0.85
                result.signal_score = 0.25
                result.notes.append(f"Funding rate {funding:+.4f}% - احتمال long squeeze")
            elif funding > 0.05:
                result.funding_rate_regime = "positive"
                result.long_squeeze_signal = 0.65
                result.signal_score = 0.40
                result.notes.append(f"Funding rate {funding:+.4f}% - bullish positioning")
            else:
                result.funding_rate_regime = "neutral"
                result.notes.append(f"Funding rate {funding:+.4f}% - خنثی")

        if oi is not None and current_price > 0:
            result.open_interest_usd = oi * current_price
            # اگر تاریخچه داریم، تغییر 24h
            if len(oi_history) >= 2:
                try:
                    prev_oi = float(oi_history[0].get("sumOpenInterest", 0))
                    if prev_oi > 0:
                        change = (oi - prev_oi) / prev_oi * 100
                        result.open_interest_change_24h = change

                        # OI افزایش + قیمت ثابت = volatility coming
                        if change > 5 and result.short_squeeze_signal < 0.6 and result.long_squeeze_signal < 0.6:
                            result.volatility_coming = 0.75
                            result.notes.append(f"OI +{change:.1f}% - انباشت پوزیشن، حرکت بزرگ در راه")

                        # OI کاهش + قیمت بالا = short covering
                        elif change < -5:
                            result.notes.append(f"OI {change:.1f}% - کاهش، احتمال short covering")
                except (ValueError, TypeError, KeyError):
                    pass

        # سیگنال نهایی ترکیبی
        if result.short_squeeze_signal > 0.7:
            result.signal_score = max(result.signal_score, 0.70)
        elif result.long_squeeze_signal > 0.7:
            result.signal_score = min(result.signal_score, 0.30)

        return result


def format_funding_oi_report(result: FundingOIResult) -> str:
    """قالب‌بندی گزارش funding/OI."""
    lines: List[str] = []
    lines.append(f"Funding Rate: {result.funding_rate:+.4f}% ({result.funding_rate_regime})")
    if result.open_interest_usd > 0:
        lines.append(f"Open Interest: ${result.open_interest_usd:,.0f}")
    if result.open_interest_change_24h != 0:
        lines.append(f"OI Change 24h: {result.open_interest_change_24h:+.2f}%")
    lines.append(f"Signal Score: {result.signal_score:.3f}")
    if result.notes:
        lines.append("Notes:")
        for note in result.notes:
            lines.append(f"  • {note}")
    return "\n".join(lines)
