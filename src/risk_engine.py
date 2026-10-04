"""MemeHunter V2.3 - tradeability / rug-risk gate.

This module deliberately uses only evidence already available in the scanner.
It is a hard safety gate, not a pump predictor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RiskAssessment:
    score: float = 0.0  # 0 = low risk, 1 = extreme risk
    tradeable: bool = True
    level: str = "LOW"
    reasons: list[str] = field(default_factory=list)
    liquidity_usd: float = 0.0
    spread_pct: float = 0.0
    atr_pct: float = 0.0
    position_size_multiplier: float = 1.0

    def to_dict(self) -> dict:
        return {
            "risk_score": round(self.score, 3),
            "tradeable": self.tradeable,
            "risk_level": self.level,
            "reasons": list(self.reasons),
            "liquidity_usd": self.liquidity_usd,
            "spread_pct": self.spread_pct,
            "atr_pct": round(self.atr_pct, 2),
            "position_size_multiplier": round(self.position_size_multiplier, 2),
        }


def assess_trade_risk(
    market_cap: float,
    volume_24h: float,
    current_price: float,
    liquidity: Optional[Any] = None,
    pump_score: float = 0.0,
    distribution_score: float = 0.0,
    atr_pct: float = 0.0,
    position_usd: float = 0.0,
) -> RiskAssessment:
    """Score observable market/liquidity risks.

    It intentionally does not claim to detect honeypots or malicious contracts;
    those require chain-level contract simulation/auditing data.
    """
    risk = 0.0
    reasons: list[str] = []
    liquidity_usd = 0.0
    spread_pct = 0.0
    position_size_multiplier = 1.0

    if market_cap <= 0 or volume_24h <= 0 or current_price <= 0:
        return RiskAssessment(1.0, False, "EXTREME", ["داده بازار ناقص یا نامعتبر"])

    if liquidity is not None:
        liquidity_usd = float(getattr(liquidity, "liquidity_usd", 0.0) or 0.0)
        if liquidity_usd <= 0:
            liquidity_usd = float(getattr(liquidity, "total_depth_usd", 0.0) or 0.0)
        if liquidity_usd <= 0:
            liquidity_usd = float(getattr(liquidity, "bid_depth_usd", 0.0) or 0.0) + float(getattr(liquidity, "ask_depth_usd", 0.0) or 0.0)
        spread_pct = float(getattr(liquidity, "spread_pct", getattr(liquidity, "spread_estimate", 0.0)) or 0.0)
        is_liquid = getattr(liquidity, "is_liquid", True)
        if liquidity_usd > 0:
            if liquidity_usd < 50_000:
                risk += 0.55
                reasons.append("نقدینگی بسیار پایین (<$50K) — عدم معامله")
            elif liquidity_usd < 100_000:
                risk += 0.25
                position_size_multiplier = min(position_size_multiplier, 0.50)
                reasons.append("نقدینگی پایین (<$100K) — اندازه پوزیشن کاهش یافت")
            elif liquidity_usd < 250_000:
                risk += 0.10
                position_size_multiplier = min(position_size_multiplier, 0.75)
                reasons.append("نقدینگی متوسط (<$250K) — احتیاط")
        if not is_liquid:
            risk += 0.45
            reasons.append("عمق نقدینگی ناکافی")
        if liquidity_usd > 0:
            liq_ratio = liquidity_usd / market_cap
            if liq_ratio < 0.01:
                risk += 0.30
                reasons.append("نسبت نقدینگی به مارکت‌کپ بسیار پایین")
            elif liq_ratio < 0.03:
                risk += 0.15
                reasons.append("نسبت نقدینگی به مارکت‌کپ پایین")
        if spread_pct > 3:
            risk += 0.25
            reasons.append(f"اسپرد بالا ({spread_pct:.2f}%)")
        elif spread_pct > 1:
            risk += 0.10
            reasons.append(f"اسپرد قابل توجه ({spread_pct:.2f}%)")

    if liquidity_usd > 0 and position_usd > 0:
        exposure_ratio = position_usd / liquidity_usd
        if exposure_ratio > 0.02:
            risk += 0.25
            position_size_multiplier = min(position_size_multiplier, 0.50)
            reasons.append(f"نسبت پوزیشن به نقدینگی بالا ({exposure_ratio:.1%})")
        elif exposure_ratio > 0.01:
            risk += 0.10
            position_size_multiplier = min(position_size_multiplier, 0.75)
            reasons.append(f"نسبت پوزیشن به نقدینگی قابل توجه ({exposure_ratio:.1%})")

    # ATR is primarily a sizing/risk input, not a pump veto: high volatility can be the setup.
    if atr_pct > 0:
        if atr_pct >= 30:
            risk += 0.25
            position_size_multiplier = min(position_size_multiplier, 0.25)
            reasons.append(f"ATR بسیار بالا ({atr_pct:.1f}%) — نوسان افراطی")
        elif atr_pct >= 25:
            risk += 0.15
            position_size_multiplier = min(position_size_multiplier, 0.50)
            reasons.append(f"ATR بالا ({atr_pct:.1f}%) — اندازه پوزیشن کاهش یافت")
        elif atr_pct >= 15:
            risk += 0.07
            position_size_multiplier = min(position_size_multiplier, 0.75)
            reasons.append(f"ATR بالا ({atr_pct:.1f}%) — احتیاط")

    volume_mc = volume_24h / market_cap if market_cap else 0.0
    if volume_mc < 0.01:
        risk += 0.15
        reasons.append("گردش حجم 24ساعته ضعیف")
    elif volume_mc > 5:
        risk += 0.10
        reasons.append("گردش غیرعادی حجم نسبت به مارکت‌کپ")

    if market_cap < 250_000:
        risk += 0.55
        reasons.append("مارکت‌کپ بسیار کوچک — عدم معامله")
    elif market_cap < 1_000_000:
        risk += 0.10
        reasons.append("مارکت‌کپ کوچک")

    if pump_score >= 0.85 and distribution_score >= 0.5:
        risk += 0.15
        reasons.append("پامپ قوی همزمان با نشانه توزیع")

    risk = min(1.0, risk)
    if risk >= 0.65:
        level, tradeable = "EXTREME", False
    elif risk >= 0.45:
        level, tradeable = "HIGH", False
    elif risk >= 0.25:
        level, tradeable = "MEDIUM", True
    else:
        level, tradeable = "LOW", True

    return RiskAssessment(risk, tradeable, level, reasons, liquidity_usd, spread_pct, atr_pct, position_size_multiplier)
