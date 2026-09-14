"""
config.py
تنظیمات اصلی پروژه MemeHunter - ربات پیداکننده میم‌کوین
Configuration for the MemeHunter bot.

V1.4.0 - KuCoin به‌عنوان اولویت اول OHLCV / Liquidity / OrderFlow
V1.3.0 - اضافه شدن منابع داده واقعی (Binance، DexScreener، GeckoTerminal)
         و برچسب «پروکسی/تقریبی» برای تحلیل‌های پیشرفته.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# نام رسمی پروژه (طبق قانون پروژه - قابل تغییر نیست)
PROJECT_NAME = "MemeHunter"
PROJECT_SLUG = "memehunter"


# --------------------------------------------------------------------------- #
# بارگذاری پویای نسخه از فایل VERSION
# --------------------------------------------------------------------------- #
def _load_version_from_file() -> str:
    """
    خواندن نسخه از فایل VERSION در ریشه پروژه.
    در صورت بروز خطا، V0.0.0 برمی‌گرداند.
    """
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if not version_file.exists():
        return "V0.0.0"
    try:
        for line in version_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.startswith("V"):
                return line
    except Exception:
        pass
    return "V0.0.0"


# نسخه فعلی پروژه (از فایل VERSION خوانده می‌شود - پویا)
PROJECT_VERSION: str = _load_version_from_file()


@dataclass
class Settings:
    # === شناسه پروژه ===
    PROJECT_NAME: str = PROJECT_NAME
    PROJECT_SLUG: str = PROJECT_SLUG
    PROJECT_VERSION: str = PROJECT_VERSION

    # === CoinGecko API (منبع اصلی داده مارکت‌کپ و دسته‌بندی) ===
    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
    COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")
    COINGECKO_API_KEY_HEADER: str = "x-cg-demo-api-key"

    # === KuCoin Public API (اولویت ۱ برای OHLCV / Liquidity / OrderFlow) - V1.4.0 ===
    # کاملاً رایگان - بدون نیاز به کلید API - محدودیت عمومی بالا
    KUCOIN_BASE_URL: str = "https://api.kucoin.com"
    ENABLE_KUCOIN: bool = True
    # عمق order book (20 یا 100)
    KUCOIN_DEPTH_LIMIT: int = 20
    # آستانه حجم دلاری ترید بزرگ
    KUCOIN_LARGE_TRADE_USD: float = 50_000.0
    # اولویت استفاده از KuCoin برای تاریخچه به‌جای CoinGecko
    PREFER_KUCOIN_HISTORY: bool = True

    # === Binance Public API (پشتیبان OrderFlow/Liquidity) - V1.3.0 ===
    # کاملاً رایگان - بدون نیاز به کلید API
    BINANCE_SPOT_URL: str = "https://data-api.binance.vision"  # V1.3.3: کمتر geo-block
    BINANCE_FUTURES_URL: str = "https://fapi.binance.com"
    # فعال‌سازی لایه Binance برای کوین‌های لیست‌شده در CEX
    ENABLE_BINANCE: bool = True
    # تعداد aggTrades برای محاسبه CVD (limit=1000)
    BINANCE_AGGTRADES_LIMIT: int = 1000
    # عمق order book برای محاسبه اسپرد/لیکوییدیتی واقعی
    BINANCE_DEPTH_LIMIT: int = 100
    # آستانه حجم دلاری برای تشخیص «سواپ بزرگ» (smart money proxy)
    BINANCE_LARGE_TRADE_USD: float = 50_000.0

    # === DexScreener API (منبع داده میم‌کوین‌های DEX) - V1.3.0 ===
    DEXSCREENER_BASE_URL: str = "https://api.dexscreener.com"
    ENABLE_DEXSCREENER: bool = True

    # === GeckoTerminal API (منبع OHLCV تاریخی DEX) - V1.3.0 ===
    GECKOTERMINAL_BASE_URL: str = "https://api.geckoterminal.com/api/v2"
    ENABLE_GECKOTERMINAL: bool = False  # به‌صورت پیش‌فرض خاموش (rate limit پایین)

    # === API تخصصی OrderFlow با کلید کاربر (اختیاری) - V1.3.0 ===
    # کاربر می‌تواند کلید سرویس‌های تخصصی مثل Kaiko یا Amberdata وارد کند
    ORDERFLOW_API_KEY: str = os.getenv("ORDERFLOW_API_KEY", "")
    ORDERFLOW_API_URL: str = os.getenv("ORDERFLOW_API_URL", "")

    TOP_N_COINS: int = 100
    MAX_MARKET_CAP_USD: float = 5_000_000_000
    MIN_24H_VOLUME_USD: float = 1_000_000
    HISTORY_DAYS: int = 30

    # === فیلتر میم‌کوین ===
    USE_COINGECKO_CATEGORIES: bool = True
    MEME_CATEGORIES: tuple = (
        "meme-token",
        "dog-themed-coins",
        "cat-themed-coins",
        "pump-fun",
    )

    # === وزن فاکتورها (مجموع = 1.0) ===
    # V1.3.1 - مستندسازی کامل + نرمال‌سازی هوشمند
    # === وزن‌های اصلی (7 فاکتور پایه) ===
    WEIGHT_RSI: float = 0.14
    WEIGHT_MACD: float = 0.14
    WEIGHT_VOLUME_SURGE: float = 0.14
    WEIGHT_PRICE_MOMENTUM: float = 0.14
    WEIGHT_MA_TREND: float = 0.14
    # === وزن‌های اندیکاتورهای پیشرفته ===
    WEIGHT_ATR: float = 0.10
    WEIGHT_BOLLINGER: float = 0.10
    # === وزن‌های تحلیل پیشرفته (اختیاری، قابل خاموش کردن) ===
    # V1.3.1 - WEIGHT_MTF_CONFLUENCE اکنون پیش‌فرض 0.05 (نه 0)
    # وقتی --enable-advanced-impact فعال باشد، تأثیر واقعی دارد
    WEIGHT_LIQUIDITY: float = 0.05
    WEIGHT_ORDERFLOW: float = 0.05
    WEIGHT_MTF_CONFLUENCE: float = 0.05  # V1.3.1 - تغییر از 0 به 0.05
    # توجه: مجموع وزن‌ها می‌تواند > 1.0 باشد چون وزن‌های پیشرفته فقط
    # وقتی --enable-advanced-impact روشن است اعمال می‌شوند
    # در آن حالت، نرمال‌سازی خودکار انجام می‌شود

    # === سوییچ‌های فعال‌سازی ===
    ENABLE_ATR: bool = True
    ENABLE_BOLLINGER: bool = True
    ENABLE_LIQUIDITY: bool = True
    ENABLE_SWEEP: bool = True
    ENABLE_ORDERFLOW: bool = True
    ENABLE_VOLUME_PROFILE: bool = True
    # تأثیر اختیاری سیگنال‌های پیشرفته روی امتیاز - V1.3.0
    ENABLE_ADVANCED_IMPACT: bool = False  # به‌صورت پیش‌فرض خاموش (محافظه‌کارانه)
    # آستانه اطمینان برای اعمال تحلیل پیشرفته
    ADVANCED_MIN_CONFIDENCE: float = 0.5

    # === برچسب‌های شفافیت - V1.3.0 ===
    # برچسب «پروکسی/تقریبی» برای تحلیل‌های پیشرفته
    # این برچسب‌ها در تمام خروجی‌ها (HTML، تلگرام، لاگ) نمایش داده می‌شوند
    PROXY_LABELS: dict = field(default_factory=lambda: {
        "liquidity_cg": "پروکسی (CoinGecko volume-based)",
        "liquidity_kucoin": "واقعی (KuCoin depth)",
        "liquidity_binance": "واقعی (Binance depth)",
        "sweep": "پروکسی (OHLC-based)",
        "orderflow_cg": "پروکسی (price-direction heuristic)",
        "orderflow_kucoin": "واقعی (KuCoin trades CVD)",
        "orderflow_binance": "واقعی (Binance aggTrades CVD)",
        "smart_money": "پروکسی (large trades heuristic)",
        "volume_profile": "پروکسی (price-binned)",
        "history_kucoin": "واقعی (KuCoin candles)",
        "history_coingecko": "CoinGecko market_chart",
    })

    # === چند بازه زمانی (Multi-timeframe) ===
    ENABLE_MULTI_TIMEFRAME: bool = True
    TIMEFRAMES: tuple = ("1d", "4h")  # روزانه + 4 ساعته
    # آستانه confluence: حداقل چند بازه باید هم‌جهت باشند
    MTF_CONFLUENCE_MIN: int = 2

    # === هشدار حجم غیرعادی ===
    VOLUME_ANOMALY_THRESHOLD: float = 3.0
    VOLUME_ANOMALY_WINDOW: int = 30

    # === Paper Trading - V1.3.0 ===
    ENABLE_PAPER_TRADING: bool = True
    PAPER_TRADING_INITIAL_CAPITAL: float = 10_000.0  # دلار
    PAPER_TRADING_POSITION_SIZE: float = 0.10  # 10% سرمایه برای هر پوزیشن
    PAPER_TRADING_MAX_POSITIONS: int = 5
    PAPER_TRADING_STOP_LOSS: float = 0.10  # 10% حد ضرر
    PAPER_TRADING_TAKE_PROFIT: float = 0.20  # 20% حد سود

    # === بک‌تست با فاصله اطمینان - V1.3.0 ===
    BACKTEST_CONFIDENCE_LEVEL: float = 0.95  # 95% فاصله اطمینان

    BUY_THRESHOLD: float = 0.65
    SELL_THRESHOLD: float = 0.35

    OUTPUT_FORMAT: str = "table"
    OUTPUT_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")

    STABLECOIN_SYMBOLS: tuple = ("USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "GUSD", "FRAX", "USTC", "USDD", "FDUSD")

    MEME_KEYWORDS: tuple = (
        "doge", "shib", "pepe", "floki", "elon", "moon", "safe", "baby",
        "inu", "cat", "frog", "wojak", "chad", "giga", "meme", "pump",
        "bonk", "wif", "bome", "myro", "slerf"
    )

    REQUEST_DELAY: float = 2.5
    REQUEST_TIMEOUT: int = 20
    MAX_RETRIES: int = 5

    # === محدودیت نرخ پیشرفته (Token Bucket) ===
    ENABLE_RATE_LIMITER: bool = True
    RATE_LIMIT_CAPACITY: int = 10
    RATE_LIMIT_REFILL_RATE: float = 0.5

    # === کش (cache) ===
    ENABLE_CACHE: bool = True
    CACHE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
    CACHE_TTL_SECONDS: int = 3600

    # === تنظیمات تلگرام ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_IMPORTANT_ONLY: bool = True

    @property
    def request_headers(self) -> dict:
        # User-Agent پویا با نسخه واقعی پروژه
        headers = {
            "Accept": "application/json",
            "User-Agent": f"{PROJECT_SLUG}/{PROJECT_VERSION} (educational project)"
        }
        if self.COINGECKO_API_KEY:
            headers[self.COINGECKO_API_KEY_HEADER] = self.COINGECKO_API_KEY
        return headers

    @property
    def binance_headers(self) -> dict:
        """هدرهای Binance - بدون نیاز به کلید API."""
        return {
            "Accept": "application/json",
            "User-Agent": f"{PROJECT_SLUG}/{PROJECT_VERSION} (public data)",
        }

    def get_proxy_label(self, key: str) -> str:
        """دریافت برچسب پروکسی/واقعی برای یک تحلیل."""
        return self.PROXY_LABELS.get(key, "نامشخص")


settings = Settings()
