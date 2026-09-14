"""
test_indicators.py
تست‌های واحد برای اندیکاتورهای تکنیکال: RSI، MACD، MA، ATR، Bollinger.
Unit tests for technical indicators.

اجرا:
    python -m pytest tests/test_indicators.py -v
یا:
    python tests/test_indicators.py
"""
import sys
import os
import unittest

# اضافه کردن ریشه پروژه به path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.indicators import (
    rsi, macd, ma_trend, volume_surge, price_momentum,
    atr, bollinger_bands, compute_indicators
)


class TestRSI(unittest.TestCase):
    """تست‌های RSI با روش هموارسازی ویلدر."""

    def test_oversold(self):
        """RSI در بازار نزولی شدید باید کمتر از 30 باشد."""
        # بازار نزولی شدید
        prices = [100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30]
        result = rsi(prices, period=14)
        self.assertIsNotNone(result)
        self.assertLess(result, 30, f"RSI باید کمتر از 30 باشد ولی {result} است")

    def test_overbought(self):
        """RSI در بازار صعودی شدید باید بیشتر از 70 باشد."""
        # بازار صعودی شدید
        prices = [30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        result = rsi(prices, period=14)
        self.assertIsNotNone(result)
        self.assertGreater(result, 70, f"RSI باید بیشتر از 70 باشد ولی {result} است")

    def test_neutral(self):
        """RSI در بازار خنثی باید بین 30-70 باشد."""
        # نوسان متوازن (صعودی و نزولی)
        import random
        random.seed(42)
        prices = [100]
        for _ in range(30):
            prices.append(prices[-1] + random.uniform(-1, 1))
        result = rsi(prices, period=14)
        self.assertIsNotNone(result)
        self.assertGreater(result, 30)
        self.assertLess(result, 70)

    def test_insufficient_data(self):
        """RSI با داده کمتر از period باید None برگرداند."""
        prices = [100, 101, 102]
        result = rsi(prices, period=14)
        self.assertIsNone(result)

    def test_all_gains(self):
        """اگر فقط سود باشد، RSI باید 100 باشد."""
        prices = list(range(100, 120))  # همیشه افزایش
        result = rsi(prices, period=14)
        self.assertEqual(result, 100.0)


class TestMACD(unittest.TestCase):
    """تست‌های MACD."""

    def test_bullish(self):
        """MACD در روند صعودی شتاب‌دار طولانی باید bullish باشد."""
        # روند صعودی شتاب‌دار طولانی (macd نیاز به stabilization دارد)
        prices = [100]
        for i in range(100):
            prices.append(prices[-1] + (i + 1) * 0.3)
        result = macd(prices)
        self.assertIsNotNone(result)
        self.assertTrue(result.bullish, "MACD باید bullish باشد در روند صعودی")

    def test_bearish(self):
        """MACD در روند نزولی باید bearish (نه bullish) باشد."""
        prices = list(range(150, 100, -1))  # روند نزولی
        result = macd(prices)
        self.assertIsNotNone(result)
        self.assertFalse(result.bullish, "MACD باید bearish باشد در روند نزولی")

    def test_insufficient_data(self):
        """MACD با داده ناکافی باید None برگرداند."""
        prices = [100, 101, 102]
        result = macd(prices)
        self.assertIsNone(result)


class TestMA(unittest.TestCase):
    """تست‌های Moving Average."""

    def test_bullish_cross(self):
        """MA در روند صعودی باید bullish باشد."""
        prices = list(range(100, 130))  # روند صعودی
        result = ma_trend(prices, short=7, long=21)
        self.assertIsNotNone(result)
        self.assertTrue(result.bullish_cross)
        self.assertGreater(result.ma_short, result.ma_long)

    def test_bearish_cross(self):
        """MA در روند نزولی باید bearish باشد."""
        prices = list(range(130, 100, -1))  # روند نزولی
        result = ma_trend(prices, short=7, long=21)
        self.assertIsNotNone(result)
        self.assertFalse(result.bullish_cross)
        self.assertLess(result.ma_short, result.ma_long)

    def test_insufficient_data(self):
        """MA با داده کمتر از period طولانی باید None برگرداند."""
        prices = [100, 101, 102, 103]
        result = ma_trend(prices, short=7, long=21)
        self.assertIsNone(result)


class TestVolumeSurge(unittest.TestCase):
    """تست‌های حجم."""

    def test_surge(self):
        """حجم آخرین روز باید 2x میانگین باشد."""
        volumes = [1000000] * 15  # میانگین 1M
        volumes[-1] = 3000000   # آخرین روز 3M
        result = volume_surge(volumes, lookback=14)
        self.assertIsNotNone(result)
        self.assertGreater(result, 2.0)

    def test_normal(self):
        """حجم عادی باید نزدیک 1.0 باشد."""
        volumes = [1000000] * 16
        result = volume_surge(volumes, lookback=14)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 1.0, delta=0.1)

    def test_insufficient_data(self):
        """با داده ناکافی باید None."""
        volumes = [100, 200]
        result = volume_surge(volumes, lookback=14)
        self.assertIsNone(result)


class TestATR(unittest.TestCase):
    """تست‌های ATR."""

    def test_high_volatility(self):
        """ATR در بازار پرنوسان باید بزرگ باشد."""
        # نوسان زیاد
        highs = [110, 105, 115, 100, 120, 95, 125, 90]
        lows = [90, 85, 95, 80, 100, 75, 105, 70]
        closes = [100, 95, 105, 90, 110, 85, 115, 80]
        result = atr(highs, lows, closes, period=5)
        self.assertIsNotNone(result)
        self.assertGreater(result.atr, 10)  # ATR بزرگ
        self.assertGreater(result.atr_percent, 5)  # نوسان نسبی بالا

    def test_low_volatility(self):
        """ATR در بازار آرام باید کوچک باشد."""
        highs = [100.5, 100.6, 100.4, 100.5, 100.7, 100.3, 100.5, 100.6]
        lows = [99.5, 99.4, 99.6, 99.5, 99.3, 99.7, 99.5, 99.4]
        closes = [100, 100, 100, 100, 100, 100, 100, 100]
        result = atr(highs, lows, closes, period=5)
        self.assertIsNotNone(result)
        self.assertLess(result.atr, 2)

    def test_insufficient_data(self):
        """ATR با داده ناکافی باید None."""
        highs = [100, 101]
        lows = [99, 100]
        closes = [100, 100]
        result = atr(highs, lows, closes, period=14)
        self.assertIsNone(result)


class TestBollingerBands(unittest.TestCase):
    """تست‌های Bollinger Bands."""

    def test_middle_equals_sma(self):
        """خط میانی Bollinger باید با SMA برابر باشد."""
        prices = list(range(100, 130))
        result = bollinger_bands(prices, period=20, std_dev=2.0)
        self.assertIsNotNone(result)
        expected_middle = sum(prices[-20:]) / 20
        self.assertAlmostEqual(result.middle, expected_middle, places=4)

    def test_upper_greater_than_lower(self):
        """باند بالا باید بزرگتر از باند پایین باشد."""
        prices = [100 + i * 0.5 for i in range(25)]
        result = bollinger_bands(prices, period=20, std_dev=2.0)
        self.assertIsNotNone(result)
        self.assertGreater(result.upper, result.lower)

    def test_percent_b_range(self):
        """percent_b باید بین 0 و 1 باشد."""
        prices = list(range(100, 130))
        result = bollinger_bands(prices, period=20, std_dev=2.0)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.percent_b, 0)
        self.assertLessEqual(result.percent_b, 1)

    def test_insufficient_data(self):
        """با داده کمتر از period باید None."""
        prices = [100, 101, 102]
        result = bollinger_bands(prices, period=20)
        self.assertIsNone(result)


class TestComputeIndicators(unittest.TestCase):
    """تست تابع ترکیبی compute_indicators."""

    def test_full_pack(self):
        """بسته کامل اندیکاتورها باید ساخته شود."""
        prices = list(range(100, 150))
        volumes = [1000000 + i * 10000 for i in range(50)]
        highs = [p + 5 for p in prices]
        lows = [p - 5 for p in prices]

        pack = compute_indicators(prices, volumes, highs, lows)
        self.assertIsNotNone(pack.rsi)
        self.assertIsNotNone(pack.macd)
        self.assertIsNotNone(pack.ma)
        self.assertIsNotNone(pack.volume_surge_ratio)
        self.assertIsNotNone(pack.price_momentum_pct)
        self.assertIsNotNone(pack.atr)
        self.assertIsNotNone(pack.bollinger)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestATRMismatch(unittest.TestCase):
    """V1.3.2 - جلوگیری از IndexError وقتی طول highs/lows با closes فرق دارد."""

    def test_atr_mismatched_lengths(self):
        closes = [100 + i for i in range(40)]
        highs = [c + 1 for c in closes[:20]]  # کوتاه‌تر
        lows = [c - 1 for c in closes[:20]]
        result = atr(highs, lows, closes, period=14)
        # نباید Exception بدهد؛ یا None یا ATRResult معتبر
        self.assertTrue(result is None or hasattr(result, "atr"))

    def test_atr_equal_lengths(self):
        closes = [100 + i * 0.5 for i in range(40)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        result = atr(highs, lows, closes, period=14)
        self.assertIsNotNone(result)
        self.assertGreater(result.atr, 0)

    def test_compute_indicators_mismatch(self):
        prices = [100 + i for i in range(40)]
        volumes = [1000] * 40
        highs = [p + 1 for p in prices[:15]]
        lows = [p - 1 for p in prices[:15]]
        pack = compute_indicators(prices, volumes, highs=highs, lows=lows)
        self.assertIsNotNone(pack)
        # نباید کرش کند

