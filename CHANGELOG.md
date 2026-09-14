# 📜 CHANGELOG - MemeHunter

> تاریخچه کامل تمام نسخه‌های منتشر شده پروژه **MemeHunter** - ربات پیداکننده میم‌کوین و صدور سیگنال خرید/فروش.

---

## [V1.4.2] - 2026-09-14

### 📨 تلگرام
- **تفکیک پیام‌ها**: خلاصه + بخش خرید + بخش فروش + نگه‌داری‌های برتر به‌صورت پیام‌های جداگانه ارسال می‌شوند
- **ذخیره کامل message_idها**: ستون `message_ids` در `telegram_messages.csv` برای ریپلای روی هر بخش در چک نتیجه
- حذف هشدار ریسک و هشتگ‌های پروژه (`#MemeHunter` و مشابه) از متن پیام
- فقط هشتگ نماد کوین (`#SHIB` و ...) باقی مانده

### 💾 ماندگاری داده (۹۰ روز)
- ورک‌فلو قبل از اسکن، آخرین آرتیفکت `memehunter-persistent-data` را بازیابی می‌کند
- پس از اسکن، `data/` دوباره با نام ثابت آپلود می‌شود تا CSV و لاگ در اجرای بعدی انباشته شوند
- `coins_database.csv` و `telegram_messages.csv` در `.gitignore` قرار گرفتند (قانون: هیچ دیتایی به گیت‌هاب پوش نشود)

### 🔧 سایر
- نسخه ورک‌فلو و VERSION به V1.4.2

---

## [V1.4.1] - 2026-09-14

### ⚡ سرعت
- fail-fast برای تاریخچه CoinGecko (حداکثر ۲ retry، sleep حداکثر ۴ث) تا دیگر ~۸۰ث معطل rate-limit نشود
- تأخیر بین کوین‌ها: ۰.۱۵ث (KuCoin) / ۰.۵ث (سایر)
- REQUEST_TIMEOUT و MAX_RETRIES کاهش یافت
- MTF sleep کوتاه‌تر

### 📨 تلگرام
- خلاصه واضح: چند خرید / فروش / نگه‌داری
- تفکیک بخش‌های 🟢 BUY / 🔴 SELL / 🟡 HOLD
- هشتگ `#SYMBOL #BUY #MemeHunter`
- لینک CoinGecko + TradingView + KuCoin
- ذخیره `message_id` در `data/telegram_messages.csv` برای ریپلای بعدی

---

## [V1.4.0] - 2026-09-14

### ✨ ویژگی جدید (Minor)
- **KuCoin به‌عنوان اولویت اول داده واقعی**:
  - OHLCV / تاریخچه قیمت از KuCoin candles (کاهش شدید rate-limit کوین‌جکو)
  - Order Flow واقعی از recent trades کوکوین
  - Liquidity واقعی از order book depth کوکوین
  - Multi-Timeframe از KuCoin
- CoinGecko فقط برای کشف میم‌کوین + fallback تاریخچه
- Binance به‌عنوان ثانویه

### 📊 تحلیل
- OrderFlow / Liquidity / Sweep با منبع واقعی KuCoin
- نمایش منبع داده در گزارش و تلگرام (واقعی vs پروکسی)

---

## [V1.3.3] - 2026-09-14

### 🐛 رفع خطا
- KeyError('skipped') در آمار API هنگام 451/عدم دسترسی Binance
- fail-fast برای HTTP 451 روی Binance (بدون ۵ بار retry)
- fallback نرم به CoinGecko وقتی داده واقعی در دسترس نیست

---

## [V1.3.2] - 2026-09-14

### 🐛 رفع خطا
- IndexError در ATR هنگام طول ناهماهنگ highs/lows/closes از CoinGecko
- نرمال‌سازی طول با `min(n)` + early return

---

## [V1.3.1] - 2026-09-13

### 🔧 پایدارسازی
- تست‌های بیشتر، آماده‌سازی برای گیت‌هاب

---

## [V1.3.0] - 2026-09-13

### ✨ ویژگی
- Order Flow / Liquidity / Sweep / Smart Money proxy
- لاگ ساختاریافته PHASE_JSON / RUN_SUMMARY_JSON
