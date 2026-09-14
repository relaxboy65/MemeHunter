"""
rate_limiter.py
محدودیت نرخ پیشرفته با الگوریتم Token Bucket - V1.2.0.

این ماژول اطمینان می‌دهد که درخواست‌های API با نرخ مشخصی ارسال می‌شوند
و از rate-limit شدن توسط CoinGecko جلوگیری می‌کند.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


class TokenBucketRateLimiter:
    """
    محدودکننده نرخ با الگوریتم Token Bucket.

    - در ابتدا، bucket پر از token است (تا سقف capacity)
    - هر ثانیه refill_rate token اضافه می‌شود
    - هر درخواست یک token مصرف می‌کند
    - اگر token نباشد، منتظر می‌مانیم تا یکی اضافه شود
    """

    def __init__(self,
                 capacity: Optional[int] = None,
                 refill_rate: Optional[float] = None) -> None:
        self.capacity = capacity if capacity is not None else settings.RATE_LIMIT_CAPACITY
        self.refill_rate = refill_rate if refill_rate is not None else settings.RATE_LIMIT_REFILL_RATE
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """تأمین token های جدید بر اساس زمان گذشته."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        # اضافه کردن token های جدید
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def acquire(self, timeout: float = 60.0) -> bool:
        """
        دریافت یک token. اگر نباشد، تا timeout صبر می‌کند.
        برمی‌گرداند True اگر موفق، False اگر timeout شود.
        """
        if not settings.ENABLE_RATE_LIMITER:
            return True

        start = time.monotonic()
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                # زمان لازم برای رسیدن به 1 token
                needed = 1.0 - self.tokens
                wait_time = needed / self.refill_rate

            elapsed = time.monotonic() - start
            if elapsed + wait_time > timeout:
                logger.warning("Rate limiter timeout after %.1fs", timeout)
                return False

            logger.debug("Rate limiter: waiting %.1fs for token", wait_time)
            time.sleep(min(wait_time, 1.0))  # حداکثر 1 ثانیه در هر مرحله

    def status(self) -> dict:
        """گزارش وضعیت فعلی."""
        with self._lock:
            self._refill()
            return {
                "tokens_available": round(self.tokens, 2),
                "capacity": self.capacity,
                "refill_rate_per_sec": self.refill_rate,
                "tokens_per_minute": self.refill_rate * 60,
            }


# نمونه سراسری (singleton)
_rate_limiter: Optional[TokenBucketRateLimiter] = None


def get_rate_limiter() -> TokenBucketRateLimiter:
    """دریافت نمونه سراسری rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TokenBucketRateLimiter()
    return _rate_limiter
