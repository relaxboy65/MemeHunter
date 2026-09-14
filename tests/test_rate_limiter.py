"""
test_rate_limiter.py
تست‌های واحد برای محدودیت نرخ پیشرفته.

V1.2.0
"""
import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.rate_limiter import TokenBucketRateLimiter


class TestRateLimiter(unittest.TestCase):
    """تست‌های rate limiter."""

    def test_initial_capacity(self):
        """در ابتدا bucket باید پر باشد."""
        rl = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
        status = rl.status()
        self.assertEqual(status["capacity"], 5)
        self.assertEqual(status["tokens_available"], 5)

    def test_acquire_tokens(self):
        """دریافت token باید کار کند."""
        rl = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
        for _ in range(3):
            self.assertTrue(rl.acquire(timeout=1))

    def test_refill(self):
        """token ها باید پر شوند."""
        rl = TokenBucketRateLimiter(capacity=2, refill_rate=10.0)
        # استفاده از همه token ها
        rl.acquire(timeout=1)
        rl.acquire(timeout=1)
        # صبر برای refill
        time.sleep(0.3)
        # حالا باید دوباره token در دسترس باشد
        self.assertTrue(rl.acquire(timeout=1))

    def test_disabled(self):
        """وقتی غیرفعال باشد، همیشه باید True برگرداند."""
        from src.config import settings
        original = settings.ENABLE_RATE_LIMITER
        try:
            settings.ENABLE_RATE_LIMITER = False
            rl = TokenBucketRateLimiter(capacity=1, refill_rate=0.1)
            # حتی بعد از مصرف، باید True برگرداند
            for _ in range(10):
                self.assertTrue(rl.acquire(timeout=0.1))
        finally:
            settings.ENABLE_RATE_LIMITER = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
