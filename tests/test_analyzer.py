"""
test_analyzer.py
تست‌های واحد برای منطق امتیازدهی و صدور سیگنال.
Unit tests for scoring and signal logic.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.indicators import IndicatorPack, MACDResult, MAResult, ATRResult, BollingerResult
from src.analyzer import analyze_coin, Signal, _rsi_score, _volume_score, _momentum_score, _ma_score


class TestScorers(unittest.TestCase):
    """تست توابع امتیازدهی."""

    def test_rsi_oversold(self):
        """RSI کمتر از 30 باید امتیاز خرید بالا بدهد."""
        self.assertGreater(_rsi_score(25), 0.8)

    def test_rsi_overbought(self):
        """RSI بیشتر از 70 باید امتیاز خرید پایین بدهد."""
        self.assertLess(_rsi_score(75), 0.2)

    def test_rsi_neutral(self):
        """RSI خنثی باید امتیاز نزدیک 0.5 بدهد."""
        score = _rsi_score(50)
        self.assertAlmostEqual(score, 0.5, delta=0.1)

    def test_volume_high_surge(self):
        """حجم 3x باید امتیاز بالا بدهد."""
        self.assertGreaterEqual(_volume_score(3.5), 0.9)

    def test_volume_low(self):
        """حجم کم باید امتیاز پایین بدهد."""
        self.assertLess(_volume_score(0.5), 0.4)

    def test_momentum_positive(self):
        """مومنتوم مثبت قوی باید امتیاز بالا بدهد."""
        self.assertGreaterEqual(_momentum_score(35), 0.9)

    def test_momentum_negative(self):
        """مومنتوم منفی قوی باید امتیاز پایین بدهد."""
        self.assertLess(_momentum_score(-35), 0.2)


class TestAnalyzeCoin(unittest.TestCase):
    """تست تابع اصلی analyze_coin."""

    def _make_coin(self, **kwargs):
        """ساخت کوین فیک برای تست."""
        defaults = {
            "id": "test-coin",
            "symbol": "test",
            "name": "Test Coin",
            "current_price": 0.0001,
            "market_cap": 100_000_000,
            "total_volume": 5_000_000,
            "price_change_percentage_24h": 10.0,
            "price_change_percentage_7d_in_currency": 25.0,
        }
        defaults.update(kwargs)
        return defaults

    def test_buy_signal(self):
        """بسته اندیکاتورهای صعودی باید سیگنال خرید بدهد."""
        pack = IndicatorPack(
            rsi=25.0,  # اشباع فروش
            macd=MACDResult(macd_line=0.001, signal_line=0.0005, histogram=0.0005, bullish=True),
            ma=MAResult(ma_short=0.00012, ma_long=0.00010, bullish_cross=True),
            volume_surge_ratio=3.0,
            price_momentum_pct=35.0,
        )
        coin = self._make_coin()
        result = analyze_coin(coin, pack)
        self.assertEqual(result.signal, Signal.BUY, f"باید BUY باشد ولی {result.signal} است")
        self.assertGreaterEqual(result.score, 0.65)

    def test_sell_signal(self):
        """بسته اندیکاتورهای نزولی باید سیگنال فروش بدهد."""
        pack = IndicatorPack(
            rsi=80.0,  # اشباع خرید
            macd=MACDResult(macd_line=-0.001, signal_line=0.0005, histogram=-0.0015, bullish=False),
            ma=MAResult(ma_short=0.00008, ma_long=0.00010, bullish_cross=False),
            volume_surge_ratio=0.5,
            price_momentum_pct=-35.0,
        )
        coin = self._make_coin()
        result = analyze_coin(coin, pack)
        self.assertEqual(result.signal, Signal.SELL, f"باید SELL باشد ولی {result.signal} است")
        self.assertLessEqual(result.score, 0.35)

    def test_hold_signal(self):
        """بسته اندیکاتورهای خنثی باید سیگنال نگه‌داری بدهد."""
        pack = IndicatorPack(
            rsi=50.0,
            macd=MACDResult(macd_line=0.0001, signal_line=0.0001, histogram=0.0, bullish=False),
            ma=MAResult(ma_short=0.00010, ma_long=0.00010, bullish_cross=False),
            volume_surge_ratio=1.0,
            price_momentum_pct=0.0,
        )
        coin = self._make_coin()
        result = analyze_coin(coin, pack)
        self.assertEqual(result.signal, Signal.HOLD, f"باید HOLD باشد ولی {result.signal} است")

    def test_reasons_not_empty(self):
        """دلایل سیگنال نباید خالی باشند."""
        pack = IndicatorPack(
            rsi=25.0,
            macd=MACDResult(macd_line=0.001, signal_line=0.0005, histogram=0.0005, bullish=True),
            ma=MAResult(ma_short=0.00012, ma_long=0.00010, bullish_cross=True),
            volume_surge_ratio=3.0,
            price_momentum_pct=35.0,
        )
        coin = self._make_coin()
        result = analyze_coin(coin, pack)
        self.assertGreater(len(result.reasons), 0)

    def test_to_dict(self):
        """تبدیل به dict باید همه فیلدها را داشته باشد."""
        pack = IndicatorPack(
            rsi=50.0,
            macd=MACDResult(macd_line=0.001, signal_line=0.0005, histogram=0.0005, bullish=True),
            ma=MAResult(ma_short=0.00012, ma_long=0.00010, bullish_cross=True),
            volume_surge_ratio=2.0,
            price_momentum_pct=10.0,
        )
        coin = self._make_coin()
        result = analyze_coin(coin, pack)
        d = result.to_dict()
        self.assertIn("score", d)
        self.assertIn("signal", d)
        self.assertIn("reasons", d)
        self.assertIn("indicators", d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
