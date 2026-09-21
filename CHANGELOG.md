# 📜 CHANGELOG - MemeHunter

---

## [V2.1.0] - 2026-09-21

### ادغام بهترین‌ها
- پایه: **V2.0.0** (معماری حرفه‌ای، Walk-Forward، Cost Model، Monte Carlo، Regime، Funding/OI، Kelly، SMC/Wyckoff، Portfolio، 131 تست)
- از **V1.5.0/V1.6.0**: لاگ GitHub Actions
  - `MH_RUN_START` / `MH_RUN_END`
  - `RUN_REPORT` خوانا
  - `GITHUB_STEP_SUMMARY` در UI اکشن
  - مرحله Actions log digest
- ورک‌فلو: `MemeHunter CI V2.1.0` + commit دیتابیس به `data/` + Artifact فقط لاگ

### حفظ‌شده از V2.0.0
- BUY_THRESHOLD=0.55
- ماژول‌های پیشرفته و enforce_law

---

## [V2.0.0] - 2026-09-21 - Major (معماری 7-لایه حرفه‌ای + قانون طلایی)

> 🎯 بزرگترین ارتقا تاریخ پروژه - تبدیل از ربات ساده به سیستم معاملاتی حرفه‌ای 7-لایه

### 📜 قانون طلایی (جدید)

> **همیشه فقط فایل زیپ 3 نسخه نهایی را نگه دار و هیچ چیز دیگری را نگه ندار.**

این قانون به‌عنوان بالاترین اولویت پروژه اضافه شد:
- اسکریپت `scripts/enforce_law.py` برای اعمال خودکار
- در GitHub Actions به‌صورت خودکار اجرا می‌شود
- در RELEASE_RULES.md به‌عنوان بخش 0 ثبت شد
- در README مستندسازی شد

### ✨ ویژگی‌های جدید V2.0.0

#### 1. Walk-Forward Optimization (رفع overfitting)
- **ماژول جدید `src/walk_forward.py`**
- Anchored Walk-Forward با پنجره train/test
- Purge و Embargo (روش López de Prado)
- گزارش robustness استراتژی

#### 2. Cost Model (هزینه‌های واقعی)
- **ماژول جدید `src/cost_model.py`**
- محاسبه slippage بر اساس نقدینگی
- Commission واقعی (0.10% spot، 0.04% futures)
- Spread تخمینی از حجم
- اعمال هزینه‌ها بر بازده خام

#### 3. Monte Carlo Simulation
- **ماژول جدید `src/monte_carlo.py`**
- 10,000 شبیه‌سازی shuffle
- محاسبه Risk of Ruin
- Probabilistic Sharpe Ratio
- توزیع بازده نهایی (percentile 5 و 95)

#### 4. Regime Detection
- **ماژول جدید `src/regime_detector.py`**
- ADX (Average Directional Index)
- Hurst Exponent (R/S method)
- Bollinger Width Percentile
- تشخیص 6 فاز: Trending Up/Down، Ranging، Volatile، Quiet، Choppy
- تصمیم «آیا معامله کنیم؟»

#### 5. Funding Rate + Open Interest
- **ماژول جدید `src/funding_oi.py`**
- داده رایگان از Binance Futures (بدون کلید)
- تشخیص short squeeze (funding خیلی منفی)
- تشخیص long squeeze (funding خیلی مثبت)
- تشخیص volatility coming (OI افزایش + قیمت ثابت)

#### 6. Smart Money Concepts (SMC)
- **ماژول جدید `src/smc_detector.py`**
- Order Block detection (bullish/bearish)
- Fair Value Gap (FVG) - imbalance سه کندلی
- Break of Structure (BOS)
- Change of Character (CHoCH)
- Swing points با fractal

#### 7. Wyckoff / Volume Spread Analysis
- **ماژول جدید `src/wyckoff.py`**
- تشخیص phase (accumulation/distribution/markup/markdown)
- Spring detection (تست کف با حجم کم)
- Upthrust detection (تست سقف با حجم کم)
- Effort vs Result analysis

#### 8. Kelly Criterion + Volatility Targeting
- **ماژول جدید `src/kelly_sizing.py`**
- فرمول Kelly: f* = (b·p - q) / b
- Quarter Kelly برای محافظه‌کاری
- Volatility Targeting (target 5% volatility)
- ترکیب Kelly و Vol Targeting

#### 9. Sentiment Analysis (Contrarian)
- **ماژول جدید `src/sentiment.py`**
- Fear & Greed Index از alternative.me (رایگان)
- استفاده به‌عنوان contrary indicator
- Extreme Fear → سیگنال خرید
- Extreme Greed → سیگنال فروش

#### 10. Portfolio Optimization
- **ماژول جدید `src/portfolio.py`**
- Correlation matrix بین میم‌کوین‌ها
- Risk Parity weighting (inverse variance)
- Diversification Ratio
- توصیه تعداد کوین بهینه

#### 11. GitHub Actions V2.0.0
- **5 Job کامل**: Lint → Test → Version Check → Build → Scheduled Scan
- بررسی هماهنگی VERSION با CHANGELOG و README
- ساخت خودکار ZIP release
- اجرای Monte Carlo در CI
- Commit خودکار CSV database

#### 12. تست‌های واحد بیشتر
- اضافه شدن 25 تست جدید (از 106 به 131 تست)
- تست کامل برای همه ماژول‌های V2.0
- همه 131 تست موفق

### 🔧 بهبودها

#### آستانه‌های واقع‌بینانه
- BUY_THRESHOLD: 0.50 → 0.55 (جلوگیری از overfitting)
- SELL_THRESHOLD: 0.35 → 0.40

#### تنظیمات جدید
- Walk-Forward: WF_TRAIN_SIZE، WF_TEST_SIZE، WF_EMBARGO_SIZE
- Monte Carlo: MC_ITERATIONS (10K)، MC_RUIN_THRESHOLD
- Kelly: KELLY_FRACTION (0.25)، KELLY_MAX_POSITION (0.40)
- Regime: REGIME_ADX_TRENDING، REGIME_HURST_TRENDING
- Funding/OI: FUNDING_EXTREME_NEGATIVE، OI_VOLATILITY_THRESHOLD

#### مستندسازی کامل
- README V2.0.0 حرفه‌ای با badges و جدول کامل
- CHANGELOG ساختاریافته
- RELEASE_RULES به‌روزرسانی شده

### 📊 آمار

- **تعداد ماژول‌های Python**: 27 (افزایش از 20)
- **تعداد تست‌های واحد**: 131 (افزایش از 106)
- **تعداد خطوط کد**: ~4500 (افزایش از ~3500)
- **ماژول‌های جدید**: 10 ماژول V2.0

### 📌 نکات مهم ارتقا

- این نسخه با V1.5.0 سازگار است
- دیتابیس قبلی CSV نیازی به تغییر ندارد
- برای استفاده کامل: `python main.py --advanced --real-data --enable-advanced-impact`
- برای بک‌تست robust: `python main.py --backtest` (اکنون با Walk-Forward)

---

## [V1.5.0] - 2026-09-21 - Minor (بهینه‌سازی پارامترها)

### ✨ ویژگی‌ها
- بهینه‌سازی BUY_THRESHOLD از 0.65 به 0.50
- Position Size از 10% به 40%
- SL/TP: 8%/40%
- نرمال‌سازی وزن‌ها به 1.00

### 🐛 رفع باگ‌ها
- رفع باگ max_drawdown
- رفع تست paper trading

---

## [V1.4.6] - 2026-09-14 - Patch

### 💾 یکپارچه‌سازی message_id در دیتابیس
- فایل `telegram_messages.csv` حذف شد
- ستون جدید `telegram_message_id` در `data/coins_database.csv`

---

## [V1.4.0] - 2026-09-14 - Minor

### ✨ ویژگی‌ها
- لایه داده واقعی Binance
- Paper Trading
- برچسب «پروکسی/واقعی»
- CI کامل در GitHub Actions

---

## [V1.3.0] - 2026-09-14 - Minor

### ✨ ویژگی‌ها
- ماژول `binance_provider.py`
- ماژول `paper_trading.py`
- تأثیر اختیاری تحلیل پیشرفته

---

## [V1.2.0] - 2026-09-14 - Minor

### ✨ ویژگی‌ها
- 4 تحلیل پیشرفته: Liquidity، Sweep، OrderFlow، Volume Profile
- بک‌تست سیگنال‌ها
- هشدار حجم غیرعادی
- داشبورد HTML
- Token Bucket Rate Limiter

---

## [V1.1.0] - 2026-09-14 - Minor

### ✨ ویژگی‌ها
- ATR (Average True Range)
- Bollinger Bands
- کش (cache) فایل
- دسته‌بندی CoinGecko

---

## [V1.0.0] - 2026-09-14 - Major

### 🎉 اولین نسخه پایدار
- 7 اندیکاتور تکنیکال
- امتیازدهی چندفاکتوری
- دیتابیس CSV با نگهداری 90 روز
- لاگ چرخشی روزانه
- GitHub Actions
- نسخه‌بندی معنایی
