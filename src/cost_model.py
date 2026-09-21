"""
cost_model.py
مدل هزینه‌های واقعی معامله - V2.0

بدون درنظرگرفتن slippage، commission و spread، هر بک‌تستی فریبنده است.
این ماژول هزینه‌های واقعی معامله میم‌کوین را محاسبه می‌کند.

برای میم‌کوین‌ها:
- Slippage: 0.5% - 3% (بسته به نقدینگی)
- Commission: 0.1% (Binance spot) یا 0.04% (Futures)
- Spread: 0.1% - 1% (بسته به نقدینگی)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class TradeCosts:
    """هزینه‌های یک معامله."""
    slippage_pct: float       # درصد
    commission_pct: float     # درصد
    spread_pct: float         # درصد (نیمی از bid-ask spread)
    total_cost_pct: float     # مجموع هزینه‌ها

    def __str__(self) -> str:
        return (f"Slippage: {self.slippage_pct:.3f}% | "
                f"Commission: {self.commission_pct:.3f}% | "
                f"Spread: {self.spread_pct:.3f}% | "
                f"Total: {self.total_cost_pct:.3f}%")


def estimate_costs(market_cap: float = 0,
                    volume_24h: float = 0,
                    spread_pct: Optional[float] = None,
                    is_futures: bool = False) -> TradeCosts:
    """
    تخمین هزینه‌های معامله بر اساس نقدینگی.

    قواعد:
    - میم‌کوین با نقدینگی بالا (volume > 10M): هزینه پایین
    - میم‌کوین با نقدینگی متوسط (1M-10M): هزینه متوسط
    - میم‌کوین با نقدینگی پایین (<1M): هزینه بالا
    """
    # Commission ثابت
    commission = 0.04 if is_futures else 0.10

    # Spread: اگر داده واقعی داریم از آن استفاده کن
    if spread_pct is not None and spread_pct > 0:
        spread = spread_pct / 2  # نیمی از bid-ask spread
    else:
        # تخمین بر اساس نقدینگی
        if volume_24h >= 10_000_000:
            spread = 0.10  # 0.10%
        elif volume_24h >= 1_000_000:
            spread = 0.25
        elif volume_24h >= 100_000:
            spread = 0.50
        elif volume_24h >= 10_000:
            spread = 1.00
        else:
            spread = 2.00  # 2% - بسیار بالا

    # Slippage: وابسته به حجم سفارش نسبت به نقدینگی
    # برای یک سفارش با اندازه استاندارد (مثلاً $1000)
    # تخمین: slippage ≈ order_size / volume * 100
    order_size = 1000  # فرض: سفارش $1000
    if volume_24h > 0:
        slippage_ratio = order_size / volume_24h
        slippage = min(5.0, slippage_ratio * 100 * 10)  # cap at 5%
    else:
        slippage = 2.0

    # برای میم‌کوین‌ها، slippage معمولاً بالاتر است
    if volume_24h < 1_000_000:
        slippage = max(slippage, 1.0)  # حداقل 1%
    if volume_24h < 100_000:
        slippage = max(slippage, 2.5)  # حداقل 2.5%

    total = slippage + commission + spread

    return TradeCosts(
        slippage_pct=slippage,
        commission_pct=commission,
        spread_pct=spread,
        total_cost_pct=total,
    )


def apply_costs_to_return(gross_return_pct: float,
                           costs: TradeCosts,
                           trades_count: int = 1) -> float:
    """
    اعمال هزینه‌ها بر بازده خام.

    trades_count: تعداد تریدها (هر ترید = 1 خرید + 1 فروش = 2x هزینه)
    """
    # هر ترید یک خرید و یک فروش دارد، پس 2x هزینه
    total_cost = costs.total_cost_pct * 2 * trades_count
    net_return = gross_return_pct - total_cost
    return net_return


def get_cost_tier(volume_24h: float) -> str:
    """دریافت رده هزینه بر اساس حجم."""
    if volume_24h >= 10_000_000:
        return "A (نقدینگی عالی)"
    if volume_24h >= 1_000_000:
        return "B (نقدینگی خوب)"
    if volume_24h >= 100_000:
        return "C (نقدینگی متوسط)"
    if volume_24h >= 10_000:
        return "D (نقدینگی ضعیف)"
    return "F (نقدینگی بسیار ضعیف)"
