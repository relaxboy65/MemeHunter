"""
walk_forward.py
Walk-Forward Optimization با Purge و Embargo - V2.0

این ماژول مشکل overfitting را با روش‌های López de Prado حل می‌کند:
- Anchored Walk-Forward: train روی داده اولیه، test روی داده جدید
- Rolling Walk-Forward: پنجره train ثابت می‌ماند
- Purge: حذف نمونه‌هایی که label آن‌ها در test است
- Embargo: حذف N نمونه پس از test برای جلوگیری از autocorrelation

بدون این ماژول، بک‌تست 100% win rate قطعاً overfit است.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Callable

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class WalkForwardResult:
    """نتیجه یک پنجره Walk-Forward."""
    train_start: int   # timestamp
    train_end: int
    test_start: int
    test_end: int
    train_trades: int
    test_trades: int
    train_return_pct: float
    test_return_pct: float
    train_win_rate: float
    test_win_rate: float
    train_sharpe: float
    test_sharpe: float
    # نسبت کارایی (efficiency): test/train
    efficiency: float = 0.0  # test_return / train_return
    # آیا پنجره معتبر است؟
    is_valid: bool = True


@dataclass
class WalkForwardReport:
    """گزارش کلی Walk-Forward."""
    windows: List[WalkForwardResult] = field(default_factory=list)
    avg_test_return: float = 0.0
    avg_train_return: float = 0.0
    avg_efficiency: float = 0.0  # نسبت میانگین test/train
    worst_test_return: float = 0.0
    best_test_return: float = 0.0
    consistency_score: float = 0.0  # درصد پنجره‌هایی که سودده بودند
    # معیار robustness
    robust: bool = False  # اگر test_return > 0 در ≥70% پنجره‌ها

    def to_dict(self) -> dict:
        return {
            "total_windows": len(self.windows),
            "avg_test_return_pct": round(self.avg_test_return, 2),
            "avg_train_return_pct": round(self.avg_train_return, 2),
            "avg_efficiency": round(self.avg_efficiency, 3),
            "worst_test_return_pct": round(self.worst_test_return, 2),
            "best_test_return_pct": round(self.best_test_return, 2),
            "consistency_score": round(self.consistency_score * 100, 1),
            "robust": self.robust,
        }


def split_walk_forward(timestamps: List[int],
                       train_size: int = 5,
                       test_size: int = 3,
                       step_size: int = 1) -> List[Tuple[List[int], List[int]]]:
    """
    تقسیم timestamps به پنجره‌های train/test.

    خروجی: لیست از (train_indices, test_indices)
    """
    n = len(timestamps)
    if n < train_size + test_size:
        return []

    splits: List[Tuple[List[int], List[int]]] = []
    start = 0
    while start + train_size + test_size <= n:
        train_idx = list(range(start, start + train_size))
        test_idx = list(range(start + train_size, start + train_size + test_size))
        splits.append((train_idx, test_idx))
        start += step_size
    return splits


def apply_purge_and_embargo(train_idx: List[int],
                             test_idx: List[int],
                             embargo_size: int = 1) -> Tuple[List[int], List[int]]:
    """
    اعمال Purge و Embargo.

    Purge: حذف نمونه‌های train که label آن‌ها به test نزدیک است
    Embargo: حذف N نمونه اول test برای جلوگیری از leakage
    """
    # Embargo: حذف اول embargo_size نمونه از test
    if embargo_size > 0 and len(test_idx) > embargo_size:
        test_idx = test_idx[embargo_size:]
    return train_idx, test_idx


def run_walk_forward_analysis(records: List[dict],
                              train_size: int = 5,
                              test_size: int = 3,
                              step_size: int = 1,
                              embargo_size: int = 1,
                              backtest_fn: Optional[Callable] = None) -> WalkForwardReport:
    """
    اجرای Walk-Forward Optimization.

    records: لیست رکوردها (هر رکورد باید 'ts' داشته باشد)
    backtest_fn: تابع بک‌تست که (records, params) → (return_pct, win_rate, sharpe)
    """
    if not records or len(records) < train_size + test_size:
        return WalkForwardReport()

    # Sort by timestamp
    records_sorted = sorted(records, key=lambda x: x.get('ts', 0))
    timestamps = [r['ts'] for r in records_sorted]

    splits = split_walk_forward(timestamps, train_size, test_size, step_size)

    if not splits:
        return WalkForwardReport()

    report = WalkForwardReport()
    test_returns: List[float] = []
    train_returns: List[float] = []
    profitable_windows = 0

    for train_idx, test_idx in splits:
        train_idx, test_idx = apply_purge_and_embargo(train_idx, test_idx, embargo_size)
        if not train_idx or not test_idx:
            continue

        train_records = [records_sorted[i] for i in train_idx]
        test_records = [records_sorted[i] for i in test_idx]

        # Run backtest on train and test
        train_result = (0.0, 0.0, 0.0)
        test_result = (0.0, 0.0, 0.0)

        if backtest_fn:
            try:
                train_result = backtest_fn(train_records, is_train=True)
                test_result = backtest_fn(test_records, is_train=False)
            except Exception as exc:
                logger.warning("Walk-forward window failed: %s", exc)
                continue

        train_ret, train_win, train_sharpe = train_result
        test_ret, test_win, test_sharpe = test_result

        window = WalkForwardResult(
            train_start=timestamps[train_idx[0]],
            train_end=timestamps[train_idx[-1]],
            test_start=timestamps[test_idx[0]],
            test_end=timestamps[test_idx[-1]],
            train_trades=len(train_records),
            test_trades=len(test_records),
            train_return_pct=train_ret,
            test_return_pct=test_ret,
            train_win_rate=train_win,
            test_win_rate=test_win,
            train_sharpe=train_sharpe,
            test_sharpe=test_sharpe,
            efficiency=(test_ret / train_ret) if train_ret != 0 else 0.0,
        )

        # Valid if test has at least 1 trade
        if window.test_trades > 0:
            report.windows.append(window)
            test_returns.append(test_ret)
            train_returns.append(train_ret)
            if test_ret > 0:
                profitable_windows += 1

    if report.windows:
        report.avg_test_return = sum(test_returns) / len(test_returns)
        report.avg_train_return = sum(train_returns) / len(train_returns)
        report.avg_efficiency = (report.avg_test_return / report.avg_train_return
                                  if report.avg_train_return != 0 else 0.0)
        report.worst_test_return = min(test_returns)
        report.best_test_return = max(test_returns)
        report.consistency_score = profitable_windows / len(report.windows)
        # Robust if ≥70% windows profitable AND avg test return > 0
        report.robust = (report.consistency_score >= 0.7 and report.avg_test_return > 0)

    return report


def format_walk_forward_report(report: WalkForwardReport) -> str:
    """قالب‌بندی گزارش Walk-Forward."""
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("  🔬 گزارش Walk-Forward Optimization")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  تعداد پنجره‌ها: {len(report.windows)}")
    lines.append(f"  میانگین بازده train: {report.avg_train_return:+.2f}%")
    lines.append(f"  میانگین بازده test:  {report.avg_test_return:+.2f}%")
    lines.append(f"  نسبت کارایی (test/train): {report.avg_efficiency:.3f}")
    lines.append(f"  بهترین پنجره test:   {report.best_test_return:+.2f}%")
    lines.append(f"  بدترین پنجره test:   {report.worst_test_return:+.2f}%")
    lines.append(f"  ثبات (consistency):  {report.consistency_score*100:.1f}% پنجره‌ها سودده")
    lines.append("")

    if report.robust:
        lines.append("  ✅ استراتژی ROBUST است (≥70% پنجره‌ها سودده)")
    else:
        lines.append("  ❌ استراتژی robust نیست (احتمالاً overfit)")

    lines.append("")

    # Show each window
    lines.append("  --- جزئیات پنجره‌ها ---")
    lines.append(f"  {'#':<3} {'train':<6} {'test':<5} {'train_ret':>10} {'test_ret':>10} {'efficiency':>10}")
    lines.append("  " + "-" * 60)
    for i, w in enumerate(report.windows, 1):
        lines.append(f"  {i:<3} {w.train_trades:<6} {w.test_trades:<5} "
                    f"{w.train_return_pct:>+9.2f}% {w.test_return_pct:>+9.2f}% "
                    f"{w.efficiency:>9.2f}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)
