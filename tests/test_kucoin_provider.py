"""
تست‌های پایه KuCoin provider - V1.4.0
بدون وابستگی به شبکه زنده برای unitهای منطقی؛
تست شبکه به‌صورت اختیاری و soft-skip.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.kucoin_provider import KuCoinClient, KuCoinAvailability
from src.binance_provider import OrderFlowReal, LiquidityReal


class TestKuCoinSymbol(unittest.TestCase):
    def test_make_symbol_override(self):
        client = KuCoinClient()
        client._available_symbols = {"PEPE-USDT", "SHIB-USDT"}
        self.assertEqual(client._make_symbol("PEPE"), "PEPE-USDT")
        self.assertEqual(client._make_symbol("shib"), "SHIB-USDT")

    def test_is_available_true(self):
        client = KuCoinClient()
        client._available_symbols = {"DOGE-USDT"}
        av = client.is_available("DOGE")
        self.assertTrue(av.available)
        self.assertEqual(av.symbol, "DOGE-USDT")

    def test_is_available_false(self):
        client = KuCoinClient()
        client._available_symbols = {"BTC-USDT"}
        av = client.is_available("NOTACOINXYZ")
        self.assertFalse(av.available)

    def test_history_from_klines_parse(self):
        client = KuCoinClient()
        # شبیه‌سازی پاسخ KuCoin: [time, open, close, high, low, volume, turnover]
        fake = [
            ["1000000010", "2", "2.2", "2.3", "1.9", "100", "220"],
            ["1000000000", "1", "2", "2.1", "0.9", "50", "100"],
        ]
        with patch.object(client, "_get", return_value=fake):
            rows = client.get_klines("TEST", interval="1d", limit=10)
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 2)
        # بعد از reverse باید قدیمی‌تر اول باشد
        self.assertEqual(rows[0][1], 1.0)  # open
        self.assertEqual(rows[0][4], 2.0)  # close
        self.assertEqual(rows[1][4], 2.2)

    def test_orderflow_from_trades(self):
        client = KuCoinClient()
        trades = [
            {"price": "1.0", "size": "10", "side": "buy"},
            {"price": "1.0", "size": "5", "side": "sell"},
            {"price": "1.0", "size": "20", "side": "buy"},
        ]
        with patch.object(client, "get_recent_trades", return_value=trades):
            of = client.compute_orderflow("PEPE", current_price=1.0, market_cap=50_000_000)
        self.assertIsInstance(of, OrderFlowReal)
        self.assertAlmostEqual(of.buy_volume, 30.0)
        self.assertAlmostEqual(of.sell_volume, 5.0)
        self.assertTrue(of.is_real)
        self.assertIn("KuCoin", of.source)

    def test_liquidity_from_depth(self):
        client = KuCoinClient()
        depth = {
            "bids": [["1.0", "100"], ["0.99", "50"]],
            "asks": [["1.01", "80"], ["1.02", "40"]],
        }
        with patch.object(client, "get_depth", return_value=depth):
            liq = client.compute_liquidity("PEPE")
        self.assertIsInstance(liq, LiquidityReal)
        self.assertGreater(liq.spread_pct, 0)
        self.assertTrue(liq.is_real)
        self.assertIn("KuCoin", liq.source)


if __name__ == "__main__":
    unittest.main()
