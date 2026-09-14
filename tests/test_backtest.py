"""
test_backtest.py
تست‌های واحد برای ماژول بک‌تست.

V1.2.0
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


class TestBacktest(unittest.TestCase):
    """تست‌های بک‌تست."""

    def setUp(self):
        """ساخت دیتابیس موقت با داده تست."""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "coins_database.csv"
        # patching
        self._original_get_db_path = backtest.get_db_path
        backtest.get_db_path = lambda: self.db_path
        self._write_test_data()

    def tearDown(self):
        backtest.get_db_path = self._original_get_db_path

    def _write_test_data(self):
        """نوشتن داده تست در CSV."""
        now = datetime.now()
        rows = []
        # یک سیگنال خرید 10 روز پیش
        buy_ts = now - timedelta(days=10)
        rows.append([
            buy_ts.strftime("%Y-%m-%d %H:%M:%S"),
            int(buy_ts.timestamp()),
            "test-coin", "TEST", "Test Coin",
            100.0,   # price at buy
            1000000, 100000, 5.0, 10.0,
            25.0,    # rsi
            0.001,   # macd_hist
            102, 100, True,  # ma
            2.5, 15.0,  # volume, momentum
            0.75, "خرید", 0.5,  # score, signal, confidence
            1.5, 12.0, 0.3, False,  # atr, bollinger
        ])
        # همان کوین 3 روز پیش (با قیمت بالاتر = سود)
        later_ts = now - timedelta(days=3)
        rows.append([
            later_ts.strftime("%Y-%m-%d %H:%M:%S"),
            int(later_ts.timestamp()),
            "test-coin", "TEST", "Test Coin",
            110.0,   # price up = +10% from buy
            1100000, 110000, 3.0, 5.0,
            55.0, 0.0005, 108, 105, True,
            1.5, 8.0,
            0.5, "نگه‌داری", 0.1,
            1.5, 12.0, 0.5, False,
        ])

        with self.db_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(DB_COLUMNS)
            writer.writerows(rows)

    def test_run_backtest(self):
        """بک‌تست باید اجرا شود."""
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        self.assertIsNotNone(stats)
        # باید حداقل 1 سیگنال داشته باشد
        self.assertGreaterEqual(stats.total_signals, 1)
        # باید 1 سیگنال خرید باشد
        self.assertGreaterEqual(stats.total_buy, 1)

    def test_format_backtest_report(self):
        """گزارش بک‌تست باید قالب‌بندی شود."""
        stats = backtest.run_backtest(days_back=30, hold_days=7)
        report = backtest.format_backtest_report(stats)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)


class TestBacktestEmptyDB(unittest.TestCase):
    """تست بک‌تست با دیتابیس خالی."""

    def test_no_db(self):
        """بدون دیتابیس باید آمار خالی برگرداند."""
        # patching
        original = backtest.get_db_path
        backtest.get_db_path = lambda: Path("/nonexistent/path.csv")
        try:
            stats = backtest.run_backtest()
            self.assertEqual(stats.total_signals, 0)
        finally:
            backtest.get_db_path = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
