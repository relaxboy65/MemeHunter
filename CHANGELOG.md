# 📜 CHANGELOG - MemeHunter

---

## [V2.8.0] - 2026-10-05 - Minor (رفع 4 باگ بحرانی + اصلاح کامل)

> 🎯 حل 4 مشکلی که در لاگ واقعی GitHub Actions پیدا شد

### 🐛 رفع باگ‌های بحرانی

#### باگ 1: ریپلای تلگرام ارسال نمی‌شد
- **مشکل**: position_tracker قبل از تلگرام اجرا می‌شد → `msg_id=` خالی
- **راه‌حل**: تلگرام اول اجرا شود، سپس position_tracker با message_id موجود

#### باگ 2: WAIT (صبر) به تلگرام ارسال می‌شد
- **مشکل**: همه 30 کوین به تلگرام ارسال می‌شد → rate limit 429 (37s تاخیر)
- **راه‌حل**: فقط BUY و SELL ارسال شود (2-3 پیام به‌جای 30)

#### باگ 3: HOLD در خروجی‌ها
- **مشکل**: `Signal.WAIT: "HOLD"` در reporter/notifier/logging
- **راه‌حل**: همه به `WAIT` تغییر یافت

#### باگ 4: زمان طولانی
- **مشکل**: 30 پیام تلگرام → 37s rate limit → 4.8 دقیقه کل
- **راه‌حل**: کاهش به 2-3 پیام → زمان کل ~2 دقیقه

### 🔧 اصلاحات فنی

#### 1. ترتیب اجرای جدید در main.py
```
1. اسکن کوین‌ها
2. تلگرام: فقط BUY/SEND → message_id روی results
3. Position Tracker: با message_id موجود
4. ذخیره CSV
```

#### 2. پاک‌سازی کامل HOLD
- `notifier.py`: `Signal.WAIT: "WAIT"`
- `logging_setup.py`: `WAIT={wait}` به‌جای `HOLD={hold}`
- `reporter.py`: `Signal.WAIT: "WAIT"`
- `profitable_strategy.py`: `WAIT = "صبر"`
- `pump_predictor.py`: کامنت‌ها اصلاح شد
- `tests/`: همه تست‌ها به‌روز شد

### 📊 بهبود زمان

| | V2.7.1 | V2.8.0 |
|---|--------|--------|
| پیام‌های تلگرام | 30 | 2-3 |
| Rate limit 429 | 11 خطا | 0 |
| زمان کل | 4.8 دقیقه | ~2 دقیقه |

### 📝 README
- بازنویسی کامل با ساختار ساده
- توضیح معماری 6 لایه
- راهنمای تلگرام با ریپلای

---

## [V2.7.1] - 2026-10-05 - Patch (کاهش زمان اجرا)

### 🔧 تغییرات
- REQUEST_DELAY: 0.6 → 0.3
- INTER_COIN_DELAY_FAST: 0.15 → 0.05
- LIMIT: 50 → 30

---

## [V2.7.0] - 2026-10-05 - Minor (رفع باگ نرمال‌سازی pump_score)

### 🐛 رفع باگ
- NameError در notifier.py (`holds` → `waits`)
- نرمال‌سازی pump_score اصلاح شد
- آستانه BUY: 0.45 → 0.20

---

## [V2.6.0] - 2026-10-05 - Minor (ادغام pump_predictor + position_tracker)

### ✨ ویژگی‌ها
- pump_predictor سیگنال اصلی شد
- HOLD حذف شد → WAIT
- position_tracker در main.py ادغام شد
- send_reply در TelegramNotifier

---

## [V2.5.0] - 2026-10-05 - Minor (سیستم ردیابی پوزیشن)

### ✨ ویژگی‌ها
- ماژول position_tracker.py
- پیام ریپلای تلگرام

---

## [V2.4.0] - 2026-10-05 - Minor (کشف هوشمند میم‌کوین)

### ✨ ویژگی‌ها
- ماژول meme_discovery.py
- کشف trending + pumping + accumulating

---

## [V2.0.0] - 2026-09-21 - Major (معماری 7-لایه)

### ✨ ویژگی‌ها
- Walk-Forward، Monte Carlo، Cost Model
- Regime Detection، Funding/OI
- SMC، Wyckoff، Kelly، Sentiment، Portfolio
- قانون طلایی (enforce_law.py)
