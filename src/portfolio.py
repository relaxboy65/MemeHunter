"""
portfolio.py
مدیریت پورتفوی چند کوینی - V2.0

محاسبه:
- Correlation matrix بین میم‌کوین‌ها
- Risk parity: وزن هر کوین بر اساس وارایانسش
- Maximum diversification
"""
from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class PortfolioResult:
    """نتیجه تحلیل پورتفوی."""
    optimal_weights: Dict[str, float] = field(default_factory=dict)
    correlations: Dict[Tuple[str, str], float] = field(default_factory=dict)
    avg_correlation: float = 0.0
    diversification_ratio: float = 1.0
    recommended_portfolio_size: int = 3
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "optimal_weights": {k: round(v, 3) for k, v in self.optimal_weights.items()},
            "avg_correlation": round(self.avg_correlation, 3),
            "diversification_ratio": round(self.diversification_ratio, 3),
            "recommended_portfolio_size": self.recommended_portfolio_size,
            "notes": self.notes,
        }


def compute_correlation(returns_a: List[float], returns_b: List[float]) -> float:
    """محاسبه همبستگی Pearson بین دو سری."""
    n = min(len(returns_a), len(returns_b))
    if n < 3:
        return 0.0
    a = returns_a[:n]
    b = returns_b[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = (sum((x - mean_a) ** 2 for x in a) / n) ** 0.5
    std_b = (sum((x - mean_b) ** 2 for x in b) / n) ** 0.5
    if std_a == 0 or std_b == 0:
        return 0.0
    return cov / (std_a * std_b)


def risk_parity_weights(volatilities: Dict[str, float]) -> Dict[str, float]:
    """
    محاسبه وزن risk parity.
    هر دارایی بر اساس وارایانسش وزن می‌گیرد (دارایی با نوسان کمتر، وزن بیشتر).
    """
    if not volatilities:
        return {}

    # Inverse variance weighting
    inv_vars = {k: 1 / (v ** 2) if v > 0 else 0 for k, v in volatilities.items()}
    total = sum(inv_vars.values())
    if total == 0:
        # Equal weights if all vols are 0
        n = len(volatilities)
        return {k: 1 / n for k in volatilities}

    return {k: v / total for k, v in inv_vars.items()}


def analyze_portfolio(coins_data: Dict[str, Dict]) -> PortfolioResult:
    """
    تحلیل پورتفوی.

    coins_data: {symbol: {'returns': [list], 'volatility': float}}
    """
    result = PortfolioResult()

    if not coins_data:
        return result

    symbols = list(coins_data.keys())
    if len(symbols) < 2:
        result.optimal_weights = {symbols[0]: 1.0} if symbols else {}
        result.notes.append("فقط یک کوین - پورتفوی متمرکز")
        return result

    # Compute correlations
    correlations: Dict[Tuple[str, str], float] = {}
    for i, sym_a in enumerate(symbols):
        for sym_b in symbols[i + 1:]:
            returns_a = coins_data[sym_a].get("returns", [])
            returns_b = coins_data[sym_b].get("returns", [])
            corr = compute_correlation(returns_a, returns_b)
            correlations[(sym_a, sym_b)] = corr

    result.correlations = correlations

    # Average correlation
    if correlations:
        result.avg_correlation = sum(correlations.values()) / len(correlations)

    # Compute volatilities
    vols = {sym: data.get("volatility", 10.0) for sym, data in coins_data.items()}

    # Risk parity weights
    result.optimal_weights = risk_parity_weights(vols)

    # Diversification ratio
    if result.avg_correlation < 0.3:
        result.diversification_ratio = 1.5
        result.recommended_portfolio_size = min(5, len(symbols))
        result.notes.append("همبستگی پایین - فرصت diversification خوب")
    elif result.avg_correlation < 0.7:
        result.diversification_ratio = 1.2
        result.recommended_portfolio_size = min(3, len(symbols))
        result.notes.append("همبستگی متوسط - diversification محدود")
    else:
        result.diversification_ratio = 1.0
        result.recommended_portfolio_size = 1
        result.notes.append("همبستگی بالا - پورتفوی متمرکز توصیه می‌شود")

    # Notes
    high_corr_pairs = [(k, v) for k, v in correlations.items() if v > 0.8]
    if high_corr_pairs:
        result.notes.append(f"{len(high_corr_pairs)} جفت با همبستگی > 0.8")

    return result
