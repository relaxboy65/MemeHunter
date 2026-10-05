# Changelog

## V2.3.1
- Added sensitive discovery tiers: WATCH/CANDIDATE/STRONG/EXTREME.
- Kept BUY gated at 2 confirmations + `PUMP_MIN_SCORE` (0.62).
- Added always-on liquidity risk bands (<$50K block, <$100K caution, <$250K reduced sizing).
- Added ATR risk sizing: 15%/25%/30% bands without automatically vetoing high-volatility setups.
- Added position/liquidity exposure checks.
- Exposed risk tier, ATR and position-size multiplier in JSON reports.

# 📜 CHANGELOG - MemeHunter

---

## [V2.6.1] - 2026-10-05 - Patch (رفع باگ NameError)

### 🐛 رفع باگ بحرانی
- **مشکل**: `NameError: name 'ind' is not defined` در خط 408 main.py
- **علت**: متغیر `ind` به‌جای `indicators` استفاده شده بود
- **راه‌حل**: استفاده از `indicators.volume_surge_ratio` و `indicators.rsi` (از IndicatorPack)

### 📝 جزئیات
در V2.6.0، ادغام pump_predictor در main.py این باگ را ایجاد کرد:
```python
# اشتباه:
volume_surge = ind.get("volume_surge_ratio")
rsi_val = ind.get("rsi")

# اصلاح:
volume_surge = indicators.volume_surge_ratio
rsi_val = indicators.rsi
```

---

## [V2.6.0] - 2026-10-05 - Minor (اصلاح 5 باگ جدی)

> 🎯 حل 5 مشکلی که در لاگ‌های واقعی پیدا شد

### 🐛 رفع باگ‌های جدی

#### باگ 1: pump_predictor استفاده نمی‌شد
- **مشکل**: در V2.5.0، pump_predictor فقط اطلاعات اضافه بود، سیگنال اصلی از analyzer می‌آمد
- **لاگ نشان داد**: `pump_score mentions: 0`
- **راه‌حل**: pump_predictor اکنون **سیگنال اصلی** است (BUY/SELL/WAIT)

#### باگ 2: HOLD هنوز وجود داشت
- **مشکل**: 87 سیگنال "نگه‌داری" در لاگ
- **راه‌حل**: Signal enum تغییر کرد: `HOLD → WAIT`
- تمام ارجاعات در کل پروژه جایگزین شدند

#### باگ 3: position_tracker کار نمی‌کرد
- **مشکل**: ماژول ساخته شده بود ولی در main.py ادغام نشده بود
- **لاگ نشان داد**: `Position tracker: تعداد: 0`
- **راه‌حل**: position_tracker اکنون در main.py ادغام شد
  - BUY → ثبت پوزیشن
  - SELL/SL/TP → بستن پوزیشن + محاسبه سود
  - ریپلای تلگرام به پیام BUY اصلی

#### باگ 4: زمان اجرا طولانی (7.7 دقیقه)
- **مشکل**: 224 API calls + 64 rate limit hits
- **راه‌حل**: کاهش API calls با استفاده از داده موجود

#### باگ 5: تلگرام ریپلای ارسال نمی‌شد
- **مشکل**: متد send_reply وجود نداشت
- **راه‌حل**: متد send_reply به TelegramNotifier اضافه شد

### ✨ ویژگی‌های جدید

#### 1. ادغام کامل pump_predictor در main.py
- سیگنال اصلی اکنون از pump_predictor می‌آید
- فقط BUY / SELL / WAIT (بدون HOLD)
- در حال پامپ → WAIT با هشدار "خرید دیر است"

#### 2. ادغام کامل position_tracker در main.py
- ثبت خودکار پوزیشن BUY
- بررسی SL/TP در هر اسکن
- بستن با سیگنال SELL
- محاسبه سود/زیان
- ریپلای تلگرام با نتیجه

#### 3. متد send_reply در TelegramNotifier
- ارسال ریپلای به پیام BUY اصلی
- شامل: ارز، قیمت ورود/خروج، مدت نگهداری، سود/زیان

### 📊 نتایج بک‌تست (24 پوزیشن)
- **کل پوزیشن‌ها**: 24
- **بسته شده**: 13
- **نرخ موفقیت**: 46.2%
- **کل سود/زیان**: +$329.32
- **میانگین بازده**: +2.53%
- **بهترین ترید**: PEPE +26.14%
- **بدترین ترید**: AI -11.75%

### 📝 پیام ریپلای نمونه
```
🟢 نتیجه سیگنال خرید

💰 ارز: PEPE (PEPE)
📥 ورود: $0.000004 (2026-09-27)
📤 خروج: $0.000005 (2026-09-28)
⏱ مدت نگهداری: 1.5 روز
📊 سود/زیان: +26.14% ($+261.42)
🔒 دلیل خروج: signal_sell
✅ ترید موفق!
```

### 🧪 تست‌ها
- 131 تست واحد (همه موفق)
- Signal enum تغییر کرد: HOLD → WAIT
- تست‌ها به‌روزرسانی شدند

---

## [V2.5.0] - 2026-10-05 - Minor (سیستم ردیابی پوزیشن + ریپلای تلگرام)

> 🎯 هدف: قبل از پامپ بگو بخر، بعد از پامپ بگو بفروش، سود را محاسبه کن

### ✨ ویژگی‌های جدید

#### 1. ماژول جدید `src/position_tracker.py`
- **ثبت خودکار پوزیشن BUY**: وقتی سیگنال خرید صادر می‌شود
- **بررسی SL/TP**: در هر اسکن، قیمت چک می‌شود
- **بستن با سیگنال SELL**: وقتی سیگنال فروش صادر می‌شود
- **محاسبه سود/زیان**: به‌صورت دلاری و درصد
- **ذخیره `telegram_message_id`**: برای ریپلای به پیام BUY اصلی
- **گزارش آماری**: win rate، کل سود، بهترین/بدترین ترید

#### 2. حذف HOLD از سیگنال‌ها
- **V2.4.0**: BUY/SELL/HOLD/WAIT
- **V2.5.0**: فقط BUY/SELL/WAIT (در حال پامپ → WAIT با هشدار)
- دلیل: HOLD به درد نمی‌خورد چون اگر خرید نکرده باشی، فایده‌ای ندارد

#### 3. پیام ریپلای تلگرام
وقتی پوزیشن بسته می‌شود، این پیام به پیام BUY اصلی ریپلای می‌شود:
```
🟢 نتیجه سیگنال خرید

💰 ارز: PEPE (PEPE)
📥 ورود: $0.000004 (2026-09-27)
📤 خروج: $0.000005 (2026-09-28)
⏱ مدت نگهداری: 1.5 روز
📊 سود/زیان: +26.14% ($+261.42)
🔒 دلیل خروج: signal_sell
✅ ترید موفق!
```

### 📊 نتایج بک‌تست (24 پوزیشن)
- **کل پوزیشن‌ها**: 24
- **بسته شده**: 13
- **باز**: 11
- **نرخ موفقیت**: 46.2%
- **کل سود/زیان**: +$329.32
- **میانگین بازده**: +2.53%
- **بهترین ترید**: PEPE +26.14%
- **بدترین ترید**: AI -11.75%

### 🔄 منطق ساده‌شده
```
BUY   → قبل از پامپ (در حال انباشت) → ثبت پوزیشن
SELL  → بعد از پامپ (در حال توزیع) → بستن پوزیشن + محاسبه سود
WAIT  → در غیر این صورت (شامل در حال پامپ - چون دیر است)
```

---

## [V2.4.0] - 2026-10-05 - Minor (کشف هوشمند + منطق ساده)

> 🎯 حل مشکل تمرکز روی کوین‌های تکراری + منطق ساده‌تر خرید/فروش

### ✨ ویژگی‌های جدید

#### 1. ماژول جدید `src/meme_discovery.py`
- **کشف هوشمند میم‌کوین‌های فعال** به‌جای کوین‌های تکراری
- منابع کشف:
  - **CoinGecko Trending API**: کوین‌های داغ امروز
  - **Volume-desc sort**: میم‌کوین‌ها با بالاترین حجم
  - **Pumping filter**: کوین‌های با تغییر > +5%
  - **Accumulating filter**: حجم بالا + قیمت ثابت
- گزارش ترکیبی با اولویت: pumping > accumulating > trending

#### 2. بازنویسی منطق خرید/فروش
- **منطق ساده و واضح**:
  - SELL: در حال توزیع (بعد از پامپ)
  - HOLD: در حال پامپ (بذار سود بگیرد)
  - BUY: انباشت قابل توجه (قبل از پامپ)
  - WAIT: در غیر این صورت
- آستانه‌های واقع‌بینانه برای داده روزانه

#### 3. استفاده از indicators موجود
- `predict_pump` اکنون پارامترهای جدید می‌پذیرد:
  - `volume_surge_ratio`: از CSV
  - `price_change_24h_pct`: از CSV
  - `rsi`: از CSV
- RSI > 75 → افزایش distribution_score
- RSI < 30 → افزایش pump_score

### 📊 نتایج بک‌تست (887 پیش‌بینی)
- **BUY signals**: 71 مورد، **69% win rate**، **+1.79% بازده**
- **SELL signals**: 26 مورد، 46% دقت
- **HOLD signals**: 25 مورد

### 🔄 مقایسه نسخه‌ها
| نسخه | BUY | Win Rate | Avg Return |
|------|-----|----------|-----------|
| V2.2.0 | 83 | 71% | +1.94% |
| V2.3.0 | 2 | 100% | +2.46% |
| **V2.4.0** | **71** | **69%** | **+1.79%** |

### 📌 مزیت V2.4.0
- کشف کوین‌های جدید (نه تکراری)
- منطق ساده‌تر و قابل فهم
- استفاده از داده موجود در CSV
- تعادل بین دقت و تعداد سیگنال

---

## [V2.2.0] - 2026-10-04 - Minor (منطق پیش‌بینانه پامپ)

> 🎯 تحول اساسی: تبدیل ربات از "واکنشی" به "پیش‌بینانه"

### ✨ ویژگی جدید: Pump Predictor

#### ماژول جدید `src/pump_predictor.py`
- تشخیص **pre-pump**: ارزهایی که حجم در حال افزایش است ولی قیمت ثابت
- تشخیص **post-pump**: ارزهایی که رشد کرده‌اند و در حال توزیع هستند
- 6 فاز: انباشت، آماده پامپ، در حال پامپ، توزیع، خستگی، خواب

### 📊 نشانه‌های pre-pump (سیگنال خرید)
1. **Volume buildup**: حجم 1.5-2x میانگین + قیمت ثابت (وزن 30%)
2. **Bollinger Squeeze**: فشار نوسان قبل از انفجار (وزن 20%)
3. **Smart money inflow**: تریدهای بزرگ خرید > فروش (وزن 25%)
4. **Short squeeze setup**: funding منفی + OI افزایش (وزن 15%)
5. **Spring pattern**: تست کف و برگشت با حجم کم (وزن 10%)

### 📊 نشانه‌های post-pump (سیگنال فروش)
1. رشد 20%+ + حجم 2x+ = توزیع قوی
2. رشد 10%+ + حجم 1.5x+ = خستگی بازار
3. Funding rate خیلی مثبت = long squeeze risk

### 🧪 نتایج بک‌تست روی 811 پیش‌بینی
- **سیگنال خرید**: 83 مورد، **71% win rate** (قدیم: 43%)
- **میانگین بازده خرید**: +1.94% در 12-24 ساعت (قدیم: +1.03%)
- **سیگنال فروش**: 6 مورد، **67% دقت** (قیمت بعداً افت کرد)
- **HOLD**: میانگین بازده بعدی -2.24% (درست - بازار در حال خنک شدن)

### 🔄 تغییرات
- آستانه BUY: 0.52 (از V2.1.1 حفظ شد)
- آستانه SELL: 0.43 (از V2.1.1 حفظ شد)
- LIMIT در workflow: 50 (از V2.1.1 حفظ شد)

---

## [V2.1.1] - 2026-10-04 - Patch (رفع باگ تمرکز و عدم تقارن)

### 🐛 رفع باگ‌های جدی

#### باگ 1: تمرکز روی چند کوین خاص
- **مشکل**: `LIMIT=15` در workflow باعث می‌شد فقط 15 کوین اسکن شوند
- **نتیجه**: همیشه همان SHIB, PEPE, TRUMP, ... بررسی می‌شدند
- **راه‌حل**: `LIMIT` از 15 به **50** افزایش یافت
- **اثر**: اکنون 50+ میم‌کوین از دسته‌بندی‌های CoinGecko اسکن می‌شوند

#### باگ 2: عدم تقارن سیگنال‌ها
- **مشکل**: آستانه BUY=0.55 و SELL=0.40 باعث شد 84 خرید، 2 فروش، 843 نگه‌داری
- **دلیل**: آستانه SELL خیلی پایین بود (فقط 0.3% داده‌ها را شامل می‌شد)
- **راه‌حل**: تنظیم آستانه‌ها بر اساس توزیع واقعی امتیازها:
  - `BUY_THRESHOLD`: 0.55 → **0.52** (شامل ~15% داده‌ها)
  - `SELL_THRESHOLD`: 0.40 → **0.43** (شامل ~15% داده‌ها)
- **اثر مورد انتظار**: توزیع متعادل‌تر (~15% خرید، ~15% فروش، ~70% نگه‌داری)

### 📊 تحلیل داده‌های تاریخی (929 رکورد)
- توزیع امتیازها:
  - `<0.40`: 0.3% (فقط 3 رکورد → سیگنال فروش خیلی نادر)
  - `0.40-0.50`: 54.7% (اکثر داده‌ها)
  - `0.50-0.55`: 35.1%
  - `0.55-0.65`: 9.9% (سیگنال خرید)
  - `>0.65`: 0.0%

### 📌 نکات
- این رفع باگ بر اساس تحلیل 929 رکورد واقعی انجام شد
- آستانه‌های جدید باید با داده‌های بیشتر اعتبارسنجی شوند

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

## [V2.3.0] - 2026-10-04 - Major (Pump Hunter)
- Integrated Pump Predictor into the main scan pipeline.
- Fixed Pump Score normalization so missing evidence cannot inflate a score to 1.0.
- Added minimum confirmation gating for BUY pump signals.
- Added tradeability/risk gate based on observable liquidity, spread, volume/market-cap and market-cap risk.
- Added pump/risk fields to AnalysisResult and JSON/detailed reports.
- Added risk-based paper-trading configuration limits.
- Expanded MTF configuration to 1d/4h/1h/15m.
