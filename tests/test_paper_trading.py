"""
test_paper_trading.py
تست‌های واحد برای Paper Trading - V1.3.0.
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import paper_trading
from src.paper_trading import (
    PaperPosition, open_position, close_position,
    check_open_positions, get_open_positions, get_paper_trading_stats,
    _read_all_positions, _rewrite_all_positions,
)


class TestPaperTrading(unittest.TestCase):
    """تست‌های Paper Trading."""

    def setUp(self):
        """ساخت فایل موقت برای هر تست."""
        self.tmpdir = tempfile.mkdtemp()
        self.test_file = Path(self.tmpdir) / "paper_trades.csv"
        # patch کردن فایل اصلی
        self._original_file = paper_trading.PAPER_TRADE_FILE
        paper_trading.PAPER_TRADE_FILE = self.test_file

    def tearDown(self):
        paper_trading.PAPER_TRADE_FILE = self._original_file

    def test_open_position(self):
        """باز کردن پوزیشن باید ذخیره شود."""
        pos = open_position("TEST", "Test Coin", entry_price=100, signal_score=0.8)
        self.assertIsNotNone(pos)
        self.assertEqual(pos.symbol, "TEST")
        self.assertEqual(pos.entry_price, 100)
        self.assertEqual(pos.status, "open")
        self.assertLess(pos.stop_loss, 100)  # SL زیر قیمت ورودی
        self.assertGreater(pos.take_profit, 100)  # TP بالای قیمت ورودی

    def test_close_position_win(self):
        """بستن پوزیشن سودده."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        closed = close_position("TEST", current_price=110, reason="manual")
        self.assertIsNotNone(closed)
        self.assertIn(closed.status, ("closed_win", "closed_tp"))
        self.assertGreater(closed.pnl_pct, 0)

    def test_close_position_loss(self):
        """بستن پوزیشن زیان‌ده."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        closed = close_position("TEST", current_price=90, reason="manual")
        self.assertIsNotNone(closed)
        self.assertIn(closed.status, ("closed_loss", "closed_sl"))
        self.assertLess(closed.pnl_pct, 0)

    def test_stop_loss_trigger(self):
        """بررسی hit کردن stop loss."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        # قیمت به زیر SL می‌رود
        closed = check_open_positions({"TEST": 85})  # SL ≈ 90 (10% below 100)
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].close_reason, "stop_loss")

    def test_take_profit_trigger(self):
        """بررسی hit کردن take profit."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        # قیمت به بالای TP می‌رود
        closed = check_open_positions({"TEST": 125})  # TP = 120 (20% above 100)
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].close_reason, "take_profit")

    def test_get_open_positions(self):
        """دریافت پوزیشن‌های باز."""
        open_position("A", "Coin A", entry_price=100, signal_score=0.8)
        open_position("B", "Coin B", entry_price=200, signal_score=0.75)
        open_pos = get_open_positions()
        self.assertEqual(len(open_pos), 2)

    def test_stats_empty(self):
        """آمار با فایل خالی باید صفر باشد."""
        stats = get_paper_trading_stats()
        self.assertEqual(stats["total_positions"], 0)
        self.assertEqual(stats["closed_positions"], 0)

    def test_stats_with_closed(self):
        """آمار با پوزیشن‌های بسته شده."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        close_position("TEST", current_price=110, reason="manual")
        stats = get_paper_trading_stats()
        self.assertEqual(stats["total_positions"], 1)
        self.assertEqual(stats["closed_positions"], 1)
        self.assertGreater(stats["win_rate"], 0)

    def test_max_positions_limit(self):
        """حداکثر تعداد پوزیشن‌های باز."""
        from src.config import settings
        original_max = settings.PAPER_TRADING_MAX_POSITIONS
        settings.PAPER_TRADING_MAX_POSITIONS = 2
        try:
            open_position("A", "A", entry_price=100, signal_score=0.8)
            open_position("B", "B", entry_price=100, signal_score=0.8)
            result = open_position("C", "C", entry_price=100, signal_score=0.8)
            self.assertIsNone(result)  # باید رد شود
        finally:
            settings.PAPER_TRADING_MAX_POSITIONS = original_max

    def test_duplicate_symbol_skipped(self):
        """پوزیشن تکراری برای همان نماد نباید باز شود."""
        open_position("TEST", "Test", entry_price=100, signal_score=0.8)
        result = open_position("TEST", "Test", entry_price=105, signal_score=0.7)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
