"""
test_coin_service.py
تست‌های واحد برای فیلتر میم‌کوین و کش.
Unit tests for meme-coin filter and cache.
"""
import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.coin_service import CoinGeckoClient, FileCache


class TestMemeFilter(unittest.TestCase):
    """تست فیلتر میم‌کوین."""

    def test_keyword_doge(self):
        """کوین با کلمه کلیدی doge باید میم‌کوین باشد."""
        coin = {"symbol": "DOGE", "name": "Dogecoin", "market_cap": 1000000000}
        self.assertTrue(CoinGeckoClient.is_likely_meme(coin))

    def test_keyword_pepe(self):
        """کوین با کلمه کلیدی pepe باید میم‌کوین باشد."""
        coin = {"symbol": "PEPE", "name": "Pepe Coin", "market_cap": 500000000}
        self.assertTrue(CoinGeckoClient.is_likely_meme(coin))

    def test_stablecoin_filtered(self):
        """استیبل‌کوین نباید میم‌کوین باشد."""
        coin = {"symbol": "USDT", "name": "Tether", "market_cap": 100000000000}
        self.assertFalse(CoinGeckoClient.is_likely_meme(coin))

    def test_usdc_filtered(self):
        """USDC نباید میم‌کوین باشد."""
        coin = {"symbol": "USDC", "name": "USD Coin", "market_cap": 50000000000}
        self.assertFalse(CoinGeckoClient.is_likely_meme(coin))

    def test_high_volatility_low_cap(self):
        """کوین با مارکت‌کپ پایین و نوسان بالا باید میم‌کوین باشد."""
        coin = {
            "symbol": "XYZ",
            "name": "Random Coin",
            "market_cap": 500_000_000,
            "price_change_percentage_24h": 50,  # نوسان 50%
        }
        self.assertTrue(CoinGeckoClient.is_likely_meme(coin))

    def test_low_volatility_high_cap(self):
        """کوین با مارکت‌کپ بالا و نوسان پایین نباید میم‌کوین باشد."""
        coin = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "market_cap": 1_000_000_000_000,
            "price_change_percentage_24h": 2,
        }
        self.assertFalse(CoinGeckoClient.is_likely_meme(coin))


class TestFileCache(unittest.TestCase):
    """تست کش فایل."""

    def setUp(self):
        """راه‌اندازی کش موقت برای هر تست."""
        self.tmpdir = tempfile.mkdtemp()
        self.cache = FileCache(self.tmpdir, ttl_seconds=3600)

    def test_set_and_get(self):
        """ذخیره و دریافت از کش باید کار کند."""
        self.cache.set({"test": "data"}, "key1", "key2")
        result = self.cache.get("key1", "key2")
        self.assertIsNotNone(result)
        self.assertEqual(result["test"], "data")

    def test_miss(self):
        """گرفتن کلید ناموجود باید None برگرداند."""
        result = self.cache.get("nonexistent")
        self.assertIsNone(result)

    def test_expiry(self):
        """داده منقضی شده نباید برگردانده شود."""
        # ساخت کش با TTL = 0 (همیشه منقضی)
        cache = FileCache(self.tmpdir, ttl_seconds=0)
        import time
        cache.set({"x": 1}, "key")
        time.sleep(0.1)  # کمی صبر
        result = cache.get("key")
        self.assertIsNone(result)

    def test_clear(self):
        """پاکسازی کش باید همه فایل‌ها را حذف کند."""
        self.cache.set({"a": 1}, "k1")
        self.cache.set({"b": 2}, "k2")
        deleted = self.cache.clear()
        self.assertEqual(deleted, 2)
        self.assertIsNone(self.cache.get("k1"))
        self.assertIsNone(self.cache.get("k2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
