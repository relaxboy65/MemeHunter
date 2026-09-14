"""
test_binance_provider.py
تست‌های واحد برای لایه داده واقعی Binance - V1.3.0.

توجه: تست‌های واقعی نیاز به اینترنت دارند. تست‌های واحد با mock انجام می‌شوند.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.binance_provider import BinanceClient, OrderFlowReal, LiquidityReal


class TestBinanceClient(unittest.TestCase):
    """تست‌های BinanceClient."""

    def test_make_symbol_basic(self):
        """تبدیل نماد معمول به نماد Binance."""
        client = BinanceClient()
        self.assertEqual(client._make_symbol("BTC"), "BTCUSDT")
        self.assertEqual(client._make_symbol("btc"), "BTCUSDT")

    def test_make_symbol_already_complete(self):
        """اگر نماد از قبل کامل است، تغییر نکند."""
        client = BinanceClient()
        self.assertEqual(client._make_symbol("BTCUSDT"), "BTCUSDT")

    def test_make_symbol_override(self):
        """استفاده از override برای نمادهای خاص."""
        client = BinanceClient()
        self.assertEqual(client._make_symbol("PEPE"), "PEPEUSDT")
        self.assertEqual(client._make_symbol("BONK"), "BONKUSDT")

    def test_make_symbol_empty(self):
        """نماد خالی باید رشته خالی برگرداند."""
        client = BinanceClient()
        self.assertEqual(client._make_symbol(""), "")


class TestOrderFlowComputation(unittest.TestCase):
    """تست‌های محاسبه OrderFlow از aggTrades."""

    def test_buy_pressure_dominant(self):
        """اگر اکثر تریدها خرید تهاجمی باشد، buy_pressure باید بالا باشد."""
        client = BinanceClient()
        # ساخت تریدهای mock: m=False یعنی خرید تهاجمی
        mock_trades = [
            {"p": "100", "q": "1.0", "m": False},  # buy
            {"p": "100", "q": "1.0", "m": False},  # buy
            {"p": "100", "q": "1.0", "m": False},  # buy
            {"p": "100", "q": "0.5", "m": True},   # sell
        ]
        with patch.object(client, 'get_agg_trades', return_value=mock_trades):
            result = client.compute_orderflow("TEST", current_price=100)
        self.assertIsNotNone(result)
        self.assertGreater(result.buy_pressure, 0.7)
        self.assertGreater(result.cvd, 0)  # CVD مثبت

    def test_sell_pressure_dominant(self):
        """اگر اکثر تریدها فروش تهاجمی باشد، sell_pressure باید بالا باشد."""
        client = BinanceClient()
        mock_trades = [
            {"p": "100", "q": "1.0", "m": True},  # sell
            {"p": "100", "q": "1.0", "m": True},  # sell
            {"p": "100", "q": "1.0", "m": True},  # sell
            {"p": "100", "q": "0.5", "m": False}, # buy
        ]
        with patch.object(client, 'get_agg_trades', return_value=mock_trades):
            result = client.compute_orderflow("TEST", current_price=100)
        self.assertIsNotNone(result)
        self.assertGreater(result.sell_pressure, 0.7)
        self.assertLess(result.cvd, 0)  # CVD منفی

    def test_large_trades_detection(self):
        """تریدهای بزرگ باید تشخیص داده شوند."""
        client = BinanceClient()
        # ترید بزرگ: price=100, qty=1000 → value=100,000 (>50k threshold)
        mock_trades = [
            {"p": "100", "q": "1000", "m": False},  # large buy
            {"p": "100", "q": "1000", "m": True},   # large sell
            {"p": "100", "q": "0.1", "m": False},   # small buy
        ]
        with patch.object(client, 'get_agg_trades', return_value=mock_trades):
            result = client.compute_orderflow("TEST", current_price=100)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.large_trades_count, 2)

    def test_no_trades_returns_none(self):
        """بدون ترید باید None برگرداند."""
        client = BinanceClient()
        with patch.object(client, 'get_agg_trades', return_value=None):
            result = client.compute_orderflow("TEST")
        self.assertIsNone(result)

    def test_is_real_flag(self):
        """برچسب is_real باید True باشد."""
        client = BinanceClient()
        mock_trades = [{"p": "100", "q": "1.0", "m": False}]
        with patch.object(client, 'get_agg_trades', return_value=mock_trades):
            result = client.compute_orderflow("TEST", current_price=100)
        self.assertIsNotNone(result)
        self.assertTrue(result.is_real)
        self.assertEqual(result.source, "Binance aggTrades")


class TestLiquidityComputation(unittest.TestCase):
    """تست‌های محاسبه Liquidity از depth."""

    def test_basic_depth(self):
        """محاسبه عمق و اسپرد."""
        client = BinanceClient()
        mock_depth = {
            "bids": [["100.0", "10.0"], ["99.5", "5.0"]],   # bid depth = 1000 + 497.5
            "asks": [["100.1", "8.0"], ["100.5", "4.0"]],   # ask depth = 800.8 + 402.0
        }
        with patch.object(client, 'get_depth', return_value=mock_depth):
            result = client.compute_liquidity("TEST")
        self.assertIsNotNone(result)
        self.assertGreater(result.total_depth_usd, 0)
        self.assertGreater(result.spread_pct, 0)
        self.assertTrue(result.is_real)

    def test_imbalance_buyers(self):
        """عدم تعادل به نفع خریداران."""
        client = BinanceClient()
        mock_depth = {
            "bids": [["100.0", "100.0"], ["99.5", "50.0"]],  # 10000 + 4975 = 14975
            "asks": [["100.1", "10.0"], ["100.5", "5.0"]],   # 1001 + 502.5 = 1503.5
        }
        with patch.object(client, 'get_depth', return_value=mock_depth):
            result = client.compute_liquidity("TEST")
        self.assertIsNotNone(result)
        self.assertGreater(result.imbalance, 0.5)  # خریداران قوی

    def test_no_depth_returns_none(self):
        """بدون depth باید None."""
        client = BinanceClient()
        with patch.object(client, 'get_depth', return_value=None):
            result = client.compute_liquidity("TEST")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
