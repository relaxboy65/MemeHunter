# 🐸 MemeHunter V2.1.0

> **ربات حرفه‌ای پیداکننده و تحلیل‌گر میم‌کوین با معماری 7-لایه**
>
> **نسخه فعلی**: V2.1.0  
> **تاریخ انتشار**: 2026-09-21

[![CI V2.1.0](https://github.com/YOUR_USERNAME/MemeHunter/actions/workflows/daily-scan.yml/badge.svg?branch=main)](https://github.com/YOUR_USERNAME/MemeHunter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-V2.1.0-green.svg)](./VERSION)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 🎯 معرفی

MemeHunter یک ربات حرفه‌ای برای کشف، تحلیل و معامله میم‌کوین‌ها است که در 8 ماه گذشته از یک اسکریپت ساده به یک سیستم معاملاتی 7-لایه‌ی کامل ارتقا یافته است.

### ✨ ویژگی‌های کلیدی V2.1.0

- 🎯 **معماری 7-لایه حرفه‌ای**: Regime → Filter → Signal → Risk → Portfolio → Execution → Monitor
- 📊 **بیش از 15 تحلیل تخصصی**: تکنیکال، Smart Money، Wyckoff، Funding/OI، Sentiment
- 🛡️ **مدیریت ریسک پیشرفته**: Kelly Criterion، Volatility Targeting، Monte Carlo
- 🔬 **رفع overfitting**: Walk-Forward Optimization با Purge و Embargo
- 💰 **هزینه‌های واقعی**: Slippage، Commission، Spread برای همه تریدها
- 🤖 **تله‌گرام خودکار**: نوتیفیکیشن با ایموجی و ساختار فاخر
- 📈 **داشبورد HTML**: گزارش‌های تعاملی
- 🔄 **CI/CD کامل**: Lint + Test + Version + Build + Scan در GitHub Actions

---

## 📋 فهرست مطالب

- [🎯 معرفی](#-معرفی)
- [📦 نصب سریع](#-نصب-سریع)
- [🚀 استفاده](#-استفاده)
- [🏗️ معماری 7-لایه](#️-معماری-7-لایه)
- [📊 ماژول‌ها](#-ماژول‌ها)
- [⚙️ تنظیمات](#️-تنظیمات)
- [🧪 بک‌تست](#-بک‌تست)
- [🤖 تلگرام](#-تلگرام)
- [🔄 GitHub Actions](#-github-actions)
- [📈 مدیریت نسخه](#-مدیریت-نسخه)
- [⚠️ سلب مسئولیت](#️-سلب-مسئولیت)

---

## 📦 نصب سریع

```bash
# استخراج
unzip MemeHunter-V2.1.0.zip -d ~/memehunter
cd ~/memehunter

# نصب وابستگی‌ها
pip install -r requirements.txt

# تنظیم تلگرام (اختیاری)
cp .env.example .env
# ویرایش .env و پر کردن توکن‌ها

# اجرای اولیه
python main.py --limit 5 --format detailed
```

---

## 🚀 استفاده

### اسکن معمولی

```bash
python main.py --limit 10 --format detailed --save
```

### اسکن کامل با داده واقعی Binance

```bash
python main.py --real-data --advanced --limit 15 --format detailed --save --telegram
```

### بک‌تست با Walk-Forward و Monte Carlo

```bash
python main.py --backtest --save
```

### داشبورد HTML

```bash
python main.py --format html --save --real-data --advanced
```

### گزینه‌های کامل خط فرمان

| گزینه | توضیح |
|------|-------|
| `--format` | `table`، `detailed`، `json`، `csv`، `html` |
| `--limit` | حداکثر تعداد کوین (پیش‌فرض: 30) |
| `--save` | ذخیره گزارش در فایل |
| `--telegram` | ارسال به تلگرام |
| `--telegram-preview` | پیش‌نمایش پیام تلگرام |
| `--advanced` | تحلیل پیشرفته (SMC، Wyckoff، ...) |
| `--real-data` | داده واقعی از Binance |
| `--enable-advanced-impact` | تأثیر تحلیل پیشرفته روی امتیاز |
| `--backtest` | اجرای بک‌تست |
| `--volume-alert` | هشدار حجم غیرعادی |
| `--paper-trading` | گزارش Paper Trading |
| `--verbose` | لاگ‌های جزئی‌تر |

---

## 🏗️ معماری 7-لایه

سیستم MemeHunter V2.1.0 از 7 لایه تشکیل شده است که هر کدام مسئولیت مشخصی دارد:

```
┌─────────────────────────────────────────┐
│  Layer 1: Market Regime Detection       │  ← ADX + Hurst + Bollinger Width
│  ↓ trending? ranging? volatile?         │
├─────────────────────────────────────────┤
│  Layer 2: Filter (آیا معامله کنیم؟)      │  ← Sentiment + Funding/OI
│  ↓ bullish/bearish bias                  │
├─────────────────────────────────────────┤
│  Layer 3: Signal Generation              │  ← SMC + Technical + Smart Money
│  ↓ entry point                           │
├─────────────────────────────────────────┤
│  Layer 4: Risk Management                │  ← Kelly + Vol Targeting
│  ↓ position size, SL/TP                  │
├─────────────────────────────────────────┤
│  Layer 5: Portfolio Context              │  ← Correlation, Diversification
│  ↓ چند کوین؟ چه وزنی؟                    │
├─────────────────────────────────────────┤
│  Layer 6: Execution                      │  ← Cost Model, Slippage
│  ↓ order placement                       │
├─────────────────────────────────────────┤
│  Layer 7: Monitoring & Adaptation        │  ← Walk-Forward + Monte Carlo
│  ↓ آیا استراتژی هنوز کار می‌کند؟         │
└─────────────────────────────────────────┘
```

---

## 📊 ماژول‌ها

### ماژول‌های V2.1.0 (جدید)

| ماژول | توضیح |
|------|-------|
| `src/walk_forward.py` | Walk-Forward Optimization با Purge/Embargo |
| `src/cost_model.py` | محاسبه slippage، commission، spread |
| `src/monte_carlo.py` | شبیه‌سازی Monte Carlo (10K سناریو) |
| `src/regime_detector.py` | تشخیص فاز بازار (ADX، Hurst، BB Width) |
| `src/funding_oi.py` | Funding Rate + Open Interest از Binance Futures |
| `src/smc_detector.py` | Smart Money Concepts (OB، FVG، BOS) |
| `src/wyckoff.py` | Wyckoff Method + Volume Spread Analysis |
| `src/kelly_sizing.py` | Kelly Criterion + Volatility Targeting |
| `src/sentiment.py` | Fear & Greed Index (contrarian) |
| `src/portfolio.py` | Correlation + Risk Parity |

### ماژول‌های موجود (V1.x)

| ماژول | توضیح |
|------|-------|
| `src/indicators.py` | 7 اندیکاتور تکنیکال (RSI، MACD، MA، ATR، Bollinger، Volume، Momentum) |
| `src/advanced_analysis.py` | Liquidity، Sweep، OrderFlow، Volume Profile |
| `src/binance_provider.py` | داده واقعی Binance (aggTrades، depth) |
| `src/backtest_pnl.py` | بک‌تست با مدیریت سرمایه |
| `src/paper_trading.py` | Paper Trading با SL/TP |
| `src/volume_alert.py` | هشدار حجم غیرعادی |
| `src/html_reporter.py` | داشبورد HTML |

---

## ⚙️ تنظیمات

### فایل `.env`

```bash
# تلگرام
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=@your_channel

# CoinGecko (اختیاری)
COINGECKO_API_KEY=CG-xxxxxxxxxxxx
```

### تنظیمات پیشرفته

در `src/config.py`:

```python
# آستانه‌های سیگنال
BUY_THRESHOLD: 0.55    # امتیاز ≥ 0.55 = خرید
SELL_THRESHOLD: 0.40    # امتیاز ≤ 0.40 = فروش

# Walk-Forward
WF_TRAIN_SIZE: 5        # 5 روز train
WF_TEST_SIZE: 3         # 3 روز test
WF_EMBARGO_SIZE: 1      # 1 روز embargo

# Monte Carlo
MC_ITERATIONS: 10000    # 10K شبیه‌سازی

# Kelly
KELLY_FRACTION: 0.25    # Quarter Kelly
KELLY_MAX_POSITION: 0.40  # Max 40% per position

# Paper Trading
PAPER_TRADING_POSITION_SIZE: 0.40   # 40% سرمایه
PAPER_TRADING_STOP_LOSS: 0.08       # 8% SL
PAPER_TRADING_TAKE_PROFIT: 0.40    # 40% TP
```

---

## 🧪 بک‌تست

### اجرای بک‌تست ساده

```bash
python main.py --backtest
```

### شاخص‌های محاسبه‌شده

| شاخص | توضیح |
|------|-------|
| Total Return % | بازده کل |
| Win Rate | درصد تریدهای سودده |
| Profit Factor | نسبت سود به زیان |
| Sharpe Ratio | بازده ریسک‌تعدیل‌شده |
| Max Drawdown % | حداکثر افت سرمایه |
| Expectancy | میانگین سود هر ترید |

### Walk-Forward Analysis

برای تست robustness استراتژی (جلوگیری از overfitting):

```python
from src.walk_forward import run_walk_forward_analysis, format_walk_forward_report

report = run_walk_forward_analysis(records, train_size=5, test_size=3)
print(format_walk_forward_report(report))
```

### Monte Carlo Simulation

برای محاسبه احتمال ruin:

```python
from src.monte_carlo import run_monte_carlo, format_monte_carlo_report

returns = [5.0, -3.0, 8.0, -2.0, 6.0]  # بازده هر ترید
result = run_monte_carlo(returns, initial_capital=10000, iterations=10000)
print(format_monte_carlo_report(result))
```

---

## 🤖 تلگرام

### تنظیم

1. ربات [@BotFather](https://t.me/BotFather) را در تلگرام پیدا کنید
2. `/newbot` بفرستید و یک ربات بسازید
3. توکن را در `.env` قرار دهید:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   ```
4. Chat ID کانال یا چت خود را بگیرید
5. در `.env` قرار دهید:
   ```
   TELEGRAM_CHAT_ID=@your_channel
   ```

### ارسال

```bash
python main.py --telegram --limit 10 --advanced --real-data
```

---

## 🔄 GitHub Actions

### Workflow V2.1.0

فایل `.github/workflows/daily-scan.yml` شامل 5 job است:

| Job | توضیح |
|-----|-------|
| 🔍 Lint | بررسی کیفیت کد با pycodestyle |
| 🧪 Tests | اجرای همه تست‌های واحد |
| 🏷️ Version Check | بررسی فرمت VERSION و هماهنگی با CHANGELOG و README |
| 📦 Build | ساخت فایل ZIP release |
| 🤖 Scheduled Scan | اسکن دوره‌ای هر 6 ساعت |

### اجرای دستی

در صفحه GitHub Actions می‌توانید با پارامترهای زیر اجرا کنید:

- `limit`: تعداد کوین (پیش‌فرض: 15)
- `advanced`: تحلیل پیشرفته (پیش‌فرض: true)
- `send_telegram`: ارسال به تلگرام (پیش‌فرض: true)

### Secrets مورد نیاز

در Settings → Secrets ریپو:

- `TELEGRAM_BOT_TOKEN` (برای ارسال تلگرام)
- `TELEGRAM_CHAT_ID` (برای ارسال تلگرام)
- `COINGECKO_API_KEY` (اختیاری، برای رفع rate limit)

---

## 📈 مدیریت نسخه

### 📜 قانون طلایی (بالاترین اولویت)

> **همیشه فقط فایل زیپ 3 نسخه نهایی را نگه دار و هیچ چیز دیگری را نگه ندار.**

این قانون **همیشه و در همه جا** باید رعایت شود. اسکریپت `scripts/enforce_law.py` این قانون را اعمال می‌کند:

```bash
# بررسی وضعیت
python scripts/enforce_law.py --check

# اعمال قانون (حذف نسخه‌های اضافی)
python scripts/enforce_law.py

# فقط نمایش (dry-run)
python scripts/enforce_law.py --dry-run
```

این قانون در GitHub Actions workflow V2.1.0 به‌صورت خودکار بعد از هر build اجرا می‌شود.

### Semantic Versioning V{Major}.{Minor}.{Patch}

| عدد | توضیح |
|-----|-------|
| Major (2) | تغییرات بزرگ معماری |
| Minor (0) | ویژگی‌های جدید سازگار |
| Patch (0) | رفع باگ |

### فایل‌های دخیل در نسخه

| فایل | توضیح |
|------|-------|
| `VERSION` | فایل متنی شامل نسخه فعلی |
| `CHANGELOG.md` | تاریخچه تغییرات |
| `README.md` | نسخه در هدر |
| `.github/workflows/daily-scan.yml` | نسخه در نام workflow |

### ساخت نسخه جدید

```bash
python scripts/release.py patch   # V2.1.0 → V2.0.1
python scripts/release.py minor   # V2.1.0 → V2.1.0
python scripts/release.py major   # V2.1.0 → V3.0.0
```

---

## 📂 ساختار پروژه

```
MemeHunter/
├── main.py                       # نقطه ورود CLI
├── VERSION                       # V2.1.0
├── CHANGELOG.md                  # تاریخچه
├── RELEASE_RULES.md              # قوانین پروژه
├── requirements.txt
├── README.md
├── .env.example                  # الگوی تنظیمات
├── .gitignore
├── .github/
│   └── workflows/
│       └── daily-scan.yml        # CI V2.1.0
├── data/                         # داده‌ها (90 روز نگهداری)
│   ├── activity.log
│   ├── coins_database.csv        # 40 ستون
│   └── cache/
├── reports/                      # خروجی گزارش‌ها
├── scripts/
│   └── release.py                # مدیریت نسخه
├── tests/                        # 131 تست واحد
│   ├── test_indicators.py
│   ├── test_analyzer.py
│   ├── test_binance_provider.py
│   ├── test_v2_modules.py        # V2.0 تست‌ها
│   └── ...
└── src/
    ├── __init__.py
    ├── config.py                 # تنظیمات
    ├── version.py                # مدیریت نسخه
    ├── logging_setup.py          # لاگ چرخشی 90 روز
    ├── storage.py                # دیتابیس CSV
    ├── rate_limiter.py           # Token Bucket
    ├── coin_service.py           # CoinGecko
    ├── binance_provider.py        # Binance واقعی
    ├── kucoin_provider.py        # KuCoin
    ├── dex_provider.py           # DexScreener + GeckoTerminal
    ├── indicators.py             # 7 اندیکاتور تکنیکال
    ├── advanced_analysis.py      # 4 تحلیل پیشرفته
    ├── analyzer.py               # ترکیب همه
    ├── # V2.0 ماژول‌های جدید:
    ├── walk_forward.py           # Walk-Forward Optimization
    ├── cost_model.py             # هزینه‌های واقعی
    ├── monte_carlo.py            # Monte Carlo
    ├── regime_detector.py        # تشخیص فاز بازار
    ├── funding_oi.py             # Funding + OI
    ├── smc_detector.py           # Smart Money Concepts
    ├── wyckoff.py                # Wyckoff/VSA
    ├── kelly_sizing.py           # Kelly Criterion
    ├── sentiment.py              # Fear/Greed
    ├── portfolio.py              # Portfolio Optimization
    ├── backtest.py               # بک‌تست
    ├── backtest_pnl.py           # بک‌تست با P&L
    ├── paper_trading.py          # Paper Trading
    ├── volume_alert.py           # هشدار حجم
    ├── reporter.py               # قالب‌بندی متنی
    ├── html_reporter.py          # داشبورد HTML
    ├── notifier.py               # تلگرام
    └── websocket_stream.py       # WebSocket real-time
```

---

## 📊 آمار پروژه

| شاخص | مقدار |
|------|-------|
| **نسخه فعلی** | V2.1.0 |
| **تعداد ماژول‌های Python** | 27 |
| **تعداد تست‌های واحد** | 131 |
| **تعداد خطوط کد** | ~4500 |
| **منابع داده** | 5 (CoinGecko، Binance، KuCoin، DexScreener، GeckoTerminal) |
| **سیاست نگهداری داده** | 90 روز |
| **حداکثر نسخه‌های نگهداری‌شده** | 3 |

---

## ⚠️ سلب مسئولیت

این پروژه **صرفاً ابزار آموزشی** است و **توصیه مالی** محسوب نمی‌شود.

### ریسک‌های کلیدی

1. **میم‌کوین‌ها بسیار پرنوسان هستند** - ممکن است 100% سرمایه از دست برود
2. **بک‌تست گذشته ضامن آینده نیست** - حتی بهترین استراتژی‌ها ممکن است در بازار واقعی شکست بخورند
3. **overfitting خطرناک است** - همیشه Walk-Forward و Monte Carlo را بررسی کنید
4. **هزینه‌های معامله بالا** - slippage میم‌کوین‌ها می‌تواند 1-3% باشد
5. **نقدینگی محدود** - ممکن است نتوانید در زمان مورد نظر بفروشید

### توصیه‌های ایمنی

- ✅ همیشه با **Paper Trading** شروع کنید
- ✅ با سرمایه کم ($100-500) تست کنید
- ✅ همیشه **DYOR** (Do Your Own Research) کنید
- ✅ فقط با پولی که حاضر به از دست دادنش هستید معامله کنید
- ❌ هرگز با پول قرض معامله نکنید
- ❌ به سیگنال‌های ربات به‌عنوان "قطعی" اعتماد نکنید

---

## 📜 لایسنس

MIT License - استفاده آزاد برای اهداف آموزشی.

---

## 🤝 مشارکت

PR ها welcome هستند! لطفاً قبل از submit:
1. تست‌ها را اجرا کنید: `python -m unittest discover tests`
2. Lint را چک کنید: `pycodestyle --max-line-length=120 src/ main.py`
3. CHANGELOG را به‌روزرسانی کنید

---

**MemeHunter V2.1.0** - ساخته شده با ❤️ برای جامعه کریپتو
