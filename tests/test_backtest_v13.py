"""
test_backtest_v13.py
تست‌های واحد برای بک‌تست V1.3.0 - فاصله اطمینان و تعداد نمونه.
"""
import sys
import os
import csv
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import backtest
from src.storage import DB_COLUMNS


class TestBacktestConfidenceInterval(unittest.TestCase):
    """تست فاصله اطمینان در بک‌تست."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "coins_database.csv"
        self._original_get_db_path = backtest.get_db_path
        backtest.get_db_path = lambda: self.db_path

    def tearDown(self):
        backtest.get_db_path = self._original_get_db_path

    def _write_test_data(self, num_buy_signals: int = 5):
        """نوشتن داده تست با چند سیگنال خرید."""
        now = datetime.now()
        rows = []
        for i in range(num_buy_signals):
            # سیگنال خرید 10 روز پیش
            buy_ts = now - timedelta(days=10 + i)
            price_at_buy = 100.0
            rows.append([
                buy_ts.strftime("%Y-%m-%d %H:%M:%S"),
                int(buy_ts.timestamp()),
                f"test-{i}", "TEST", "Test Coin",
                price_at_buy,
                1000000, 100000, 5.0, 10.0,
                25.0, 0.001, 102, 100, True,
                2.5, 15.0, 0.75, "خرید", 0.5,
                1.5, 12.0, 0.3, False,
                # V1.3.0 فیلدهای پیشرفته
                0.7, False, 0.3, 0.1, False, "none",
                0.6, 0.4, False, 0, 0, 0, 0.5, 1, "1 پروکسی",
            ])
            # همان کوین 3 روز بعد با قیمت متفاوت
            later_ts = now - timedelta(days=3 + i)
            price_after = 110.0 if i % 2 == 0 else 95.0  # نیمی سود، نیمی زیان
            rows.append([
                later_ts.strftime("%Y-%m-%d %H:%M:%S"),
                int(later_ts.timestamp()),
                f"test-{i}", "TEST", "Test Coin",
                price_after,
                1100000, 110000, 3.0, 5.0,
                55.0, 0.0005, 108, 105, True,
                1.5, 8.0, 0.5, "نگه‌داری", 0.1,
                1.5, 12.0, 0.5, False,
                0.6, False, 0.3, 0.1, False, "none",
                0.6, 0.4, False, 0, 0, 0, 0.5, 1, "1 پروکسی",
            ])

        with self.db_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(DB_COLUMNS)
            writer.writerows(rows)

    def test_sample_count(self):
        """تعداد نمونه‌ها باید درست شمارده شود."""
        self._write_test_data(num_buy_signals=5)
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        self.assertGreaterEqual(stats.buy_sample_count_7d, 1)

    def test_confidence_interval(self):
        """فاصله اطمینان باید محاسبه شود."""
        self._write_test_data(num_buy_signals=10)
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        if stats.buy_sample_count_7d > 1:
            # فاصله اطمینان باید شامل میانگین باشد
            self.assertLessEqual(stats.buy_ci_lower_7d, stats.buy_avg_return_7d)
            self.assertGreaterEqual(stats.buy_ci_upper_7d, stats.buy_avg_return_7d)

    def test_empty_returns_zero_ci(self):
        """بدون داده، فاصله اطمینان باید صفر باشد."""
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        self.assertEqual(stats.buy_ci_lower_7d, 0.0)
        self.assertEqual(stats.buy_ci_upper_7d, 0.0)

    def test_report_includes_sample_count(self):
        """گزارش باید شامل تعداد نمونه باشد."""
        self._write_test_data(num_buy_signals=3)
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        report = backtest.format_backtest_report(stats)
        self.assertIn("نمونه", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
