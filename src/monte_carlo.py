"""
monte_carlo.py
Monte Carlo Simulation برای تست robustness استراتژی - V2.0

این ماژول با 10,000 بار shuffle کردن تراکنش‌های بک‌تست،
توزیع احتمالات بازده نهایی را محاسبه می‌کند.

خروجی کلیدی:
- Risk of Ruin: درصد سناریوهایی که سرمایه به زیر 50% می‌رسد
- Probabilistic Sharpe Ratio
- بازده مورد انتظار با 95% اطمینان
"""
from __future__ import annotations

import logging
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class MonteCarloResult:
    """نتیجه شبیه‌سازی Monte Carlo."""
    iterations: int = 0
    final_capitals: List[float] = field(default_factory=list)
    max_drawdowns: List[float] = field(default_factory=list)
    sharpe_ratios: List[float] = field(default_factory=list)
    # آمار خلاصه
    mean_final_capital: float = 0.0
    median_final_capital: float = 0.0
    std_final_capital: float = 0.0
    percentile_5_capital: float = 0.0     # بدترین 5%
    percentile_95_capital: float = 0.0    # بهترین 5%
    mean_max_drawdown: float = 0.0
    worst_drawdown: float = 0.0
    risk_of_ruin: float = 0.0    # % سناریوهایی که سرمایه < 50%
    probabilistic_sharpe: float = 0.0
    # تفسیر
    is_robust: bool = False     # اگر <5% risk of ruin

    def to_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "mean_final_capital": round(self.mean_final_capital, 2),
            "median_final_capital": round(self.median_final_capital, 2),
            "std_final_capital": round(self.std_final_capital, 2),
            "percentile_5_capital": round(self.percentile_5_capital, 2),
            "percentile_95_capital": round(self.percentile_95_capital, 2),
            "mean_max_drawdown_pct": round(self.mean_max_drawdown, 2),
            "worst_drawdown_pct": round(self.worst_drawdown, 2),
            "risk_of_ruin_pct": round(self.risk_of_ruin, 2),
            "probabilistic_sharpe": round(self.probabilistic_sharpe, 3),
            "is_robust": self.is_robust,
        }


def run_monte_carlo(trade_returns_pct: List[float],
                     initial_capital: float = 10000,
                     iterations: int = 10000,
                     risk_free_rate: float = 0.0,
                     ruin_threshold: float = 0.5) -> MonteCarloResult:
    """
    اجرای Monte Carlo Simulation.

    trade_returns_pct: لیست بازده هر ترید (درصد، مثلاً [5.2, -3.1, 8.7, ...])
    iterations: تعداد شبیه‌سازی‌ها (پیش‌فرض 10,000)
    ruin_threshold: درصد سرمایه‌ای که زیر آن = ruin (پیش‌فرض 50%)
    """
    if not trade_returns_pct or len(trade_returns_pct) < 2:
        return MonteCarloResult()

    result = MonteCarloResult(iterations=iterations)

    for _ in range(iterations):
        # Shuffle the returns
        shuffled = trade_returns_pct.copy()
        random.shuffle(shuffled)

        # Simulate equity curve
        capital = initial_capital
        peak = initial_capital
        max_dd = 0.0
        daily_returns: List[float] = []

        for ret_pct in shuffled:
            if capital <= 0:
                break
            # Apply return
            capital *= (1 + ret_pct / 100)
            daily_returns.append(ret_pct / 100)

            # Track drawdown
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100
            if dd > max_dd:
                max_dd = dd

        result.final_capitals.append(capital)
        result.max_drawdowns.append(max_dd)

        # Sharpe for this run
        if len(daily_returns) > 1:
            try:
                std = statistics.stdev(daily_returns)
                if std > 0:
                    avg = statistics.mean(daily_returns)
                    # Annualize (assume daily)
                    sharpe = (avg - risk_free_rate) / std * math.sqrt(365)
                    result.sharpe_ratios.append(sharpe)
            except statistics.StatisticsError:
                pass

    # Compute statistics
    if result.final_capitals:
        result.mean_final_capital = statistics.mean(result.final_capitals)
        result.median_final_capital = statistics.median(result.final_capitals)
        try:
            result.std_final_capital = statistics.stdev(result.final_capitals)
        except statistics.StatisticsError:
            result.std_final_capital = 0.0

        # Percentiles
        sorted_caps = sorted(result.final_capitals)
        n = len(sorted_caps)
        result.percentile_5_capital = sorted_caps[int(n * 0.05)]
        result.percentile_95_capital = sorted_caps[int(n * 0.95)]

    if result.max_drawdowns:
        result.mean_max_drawdown = statistics.mean(result.max_drawdowns)
        result.worst_drawdown = max(result.max_drawdowns)

    # Risk of Ruin
    ruined = sum(1 for c in result.final_capitals if c < initial_capital * ruin_threshold)
    result.risk_of_ruin = ruined / len(result.final_capitals) * 100

    # Probabilistic Sharpe Ratio (simplified)
    if result.sharpe_ratios:
        observed_sharpe = statistics.mean(result.sharpe_ratios)
        # PSR = normal CDF of (observed_sharpe - benchmark) considering variance
        try:
            std_sharpe = statistics.stdev(result.sharpe_ratios)
            if std_sharpe > 0:
                # Z-score approximation
                z = (observed_sharpe - 1.0) / std_sharpe  # benchmark = 1.0
                # Normal CDF approximation
                result.probabilistic_sharpe = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        except statistics.StatisticsError:
            pass

    # Robustness: risk of ruin < 5%
    result.is_robust = result.risk_of_ruin < 5

    return result


def format_monte_carlo_report(result: MonteCarloResult,
                                initial_capital: float = 10000) -> str:
    """قالب‌بندی گزارش Monte Carlo."""
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("  🎲 گزارش Monte Carlo Simulation")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  تعداد شبیه‌سازی‌ها: {result.iterations:,}")
    lines.append("")
    lines.append("  --- توزیع سرمایه نهایی ---")
    lines.append(f"  میانگین:    ${result.mean_final_capital:,.2f}  "
                f"({(result.mean_final_capital/initial_capital-1)*100:+.2f}%)")
    lines.append(f"  میانه:      ${result.median_final_capital:,.2f}  "
                f"({(result.median_final_capital/initial_capital-1)*100:+.2f}%)")
    lines.append(f"  انحراف معیار: ${result.std_final_capital:,.2f}")
    lines.append(f"  بدترین 5%:  ${result.percentile_5_capital:,.2f}  "
                f"({(result.percentile_5_capital/initial_capital-1)*100:+.2f}%)")
    lines.append(f"  بهترین 5%:  ${result.percentile_95_capital:,.2f}  "
                f"({(result.percentile_95_capital/initial_capital-1)*100:+.2f}%)")
    lines.append("")
    lines.append("  --- آمار Drawdown ---")
    lines.append(f"  میانگین max drawdown: {result.mean_max_drawdown:.2f}%")
    lines.append(f"  بدترین drawdown:     {result.worst_drawdown:.2f}%")
    lines.append("")
    lines.append("  --- معیارهای ریسک ---")
    lines.append(f"  🎲 Risk of Ruin (capital < 50%): {result.risk_of_ruin:.2f}%")
    lines.append(f"  📊 Probabilistic Sharpe Ratio:    {result.probabilistic_sharpe:.3f}")
    lines.append("")

    if result.is_robust:
        lines.append("  ✅ استراتژی ROBUST است (Risk of Ruin < 5%)")
    else:
        lines.append(f"  ❌ استراتژی robust نیست (Risk of Ruin = {result.risk_of_ruin:.2f}%)")

    lines.append("=" * 70)
    return "\n".join(lines)
