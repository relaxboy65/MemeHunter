"""
test_advanced_analysis.py
تست‌های واحد برای تحلیل‌های پیشرفته: لیکوییدیتی، سوییپ، اردرفلو، والیوم پروفایل.

V1.2.0
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.advanced_analysis import (
    analyze_liquidity, analyze_sweep, analyze_orderflow, analyze_volume_profile,
    compute_advanced_analysis,
)


class TestLiquidity(unittest.TestCase):
    """تست‌های تحلیل لیکوییدیتی."""

    def test_high_liquidity(self):
        """حجم بالا باید لیکوییدیتی عالی بدهد."""
        volumes = [15_000_000] * 30
        prices = [0.001] * 30
        result = analyze_liquidity(volumes, prices)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.liquidity_score, 0.9)
        self.assertTrue(result.is_liquid)
        self.assertLess(result.spread_estimate, 0.5)

    def test_low_liquidity(self):
        """حجم کم باید لیکوییدیتی ضعیف بدهد."""
        volumes = [5_000] * 30
        prices = [0.001] * 30
        result = analyze_liquidity(volumes, prices)
        self.assertIsNotNone(result)
        self.assertLess(result.liquidity_score, 0.4)
        self.assertFalse(result.is_liquid)
        self.assertGreater(result.spread_estimate, 1.0)

    def test_insufficient_data(self):
        """داده کم باید None برگرداند."""
        volumes = [1000] * 5
        prices = [0.001] * 5
        result = analyze_liquidity(volumes, prices)
        self.assertIsNone(result)


class TestSweep(unittest.TestCase):
    """تست‌های تحلیل سوییپ."""

    def test_low_sweep_detected(self):
        """سوییپ پایینی باید تشخیص داده شود."""
        # قیمت‌ها و سقف/کف که در آخرین شمع کف شکسته و برگشته
        prices = [100, 101, 99, 100, 100]
        highs = [101, 102, 100, 101, 101]
        lows = [99, 100, 98, 99, 95]  # آخرین کف = 95 (شکست قبلی 98)
        result = analyze_sweep(prices, highs, lows)
        self.assertIsNotNone(result)
        self.assertTrue(result.sweep_detected)
        self.assertEqual(result.sweep_type, "low_sweep")
        self.assertTrue(result.recovery)

    def test_no_sweep(self):
        """بدون شکست نباید سوییپ باشد."""
        prices = [100, 100, 100, 100, 100]
        highs = [101, 101, 101, 101, 101]
        lows = [99, 99, 99, 99, 99]
        result = analyze_sweep(prices, highs, lows)
        self.assertIsNotNone(result)
        self.assertFalse(result.sweep_detected)


class TestOrderFlow(unittest.TestCase):
    """تست‌های تحلیل اردرفلو."""

    def test_buy_pressure(self):
        """روند صعودی با حجم باید فشار خرید بدهد."""
        prices = [100, 102, 104, 106, 108, 110, 112]
        volumes = [1_000_000] * 7
        result = analyze_orderflow(prices, volumes)
        self.assertIsNotNone(result)
        self.assertGreater(result.buy_pressure, 0.7)
        self.assertLess(result.sell_pressure, 0.3)
        self.assertGreater(result.cumulative_delta, 0)

    def test_sell_pressure(self):
        """روند نزولی با حجم باید فشار فروش بدهد."""
        prices = [112, 110, 108, 106, 104, 102, 100]
        volumes = [1_000_000] * 7
        result = analyze_orderflow(prices, volumes)
        self.assertIsNotNone(result)
        self.assertGreater(result.sell_pressure, 0.7)
        self.assertLess(result.buy_pressure, 0.3)

    def test_insufficient_data(self):
        """داده کم باید None."""
        prices = [100, 101]
        volumes = [1000, 2000]
        result = analyze_orderflow(prices, volumes)
        self.assertIsNone(result)


class TestVolumeProfile(unittest.TestCase):
    """تست‌های تحلیل والیوم پروفایل."""

    def test_poc_calculation(self):
        """POC باید در محدوده قیمت باشد."""
        # قیمت‌های متغیر
        prices = [100, 101, 102, 100, 101, 100, 102, 101] * 3
        volumes = [100_000] * len(prices)
        result = analyze_volume_profile(prices, volumes, bins=10)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.poc_price, min(prices))
        self.assertLessEqual(result.poc_price, max(prices))
        self.assertGreater(result.value_area_pct, 0)

    def test_value_area(self):
        """Value Area باید معتبر باشد."""
        prices = list(range(100, 130))
        volumes = [1_000_000] * len(prices)
        result = analyze_volume_profile(prices, volumes, bins=10)
        self.assertIsNotNone(result)
        self.assertLessEqual(result.val, result.vah)
        self.assertGreater(result.value_area_pct, 0.5)

    def test_profile_shape(self):
        """شکل پروفایل باید یکی از مقادیر معتبر باشد."""
        prices = list(range(100, 130))
        volumes = [1_000_000] * len(prices)
        result = analyze_volume_profile(prices, volumes, bins=10)
        self.assertIsNotNone(result)
        self.assertIn(result.profile_shape, ("normal", "p_shape", "b_shape", "d_shape"))

    def test_insufficient_data(self):
        """داده کم باید None."""
        prices = [100, 101]
        volumes = [1000, 2000]
        result = analyze_volume_profile(prices, volumes)
        self.assertIsNone(result)


class TestComputeAdvancedAnalysis(unittest.TestCase):
    """تست تابع ترکیبی compute_advanced_analysis."""

    def test_full_pack(self):
        """بسته کامل تحلیل‌های پیشرفته."""
        prices = list(range(100, 150))
        volumes = [1_000_000 + i * 10_000 for i in range(50)]
        highs = [p + 5 for p in prices]
        lows = [p - 5 for p in prices]

        pack = compute_advanced_analysis(prices, volumes, highs, lows)
        self.assertIsNotNone(pack.liquidity)
        self.assertIsNotNone(pack.sweep)
        self.assertIsNotNone(pack.orderflow)
        self.assertIsNotNone(pack.volume_profile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
