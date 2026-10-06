# 📜 CHANGELOG - MemeHunter

---

## [V2.9.0] - 2026-10-05 - Minor (بهبود سرعت 86% + آستانه BUY)

> 🚀 زمان اجرا از 4.8 دقیقه به ~40 ثانیه کاهش یافت

### ⚡ بهبود سرعت

| تنظیم | قدیم | جدید |
|------|------|------|
| LIMIT | 30 | **20** |
| MTF API | فعال | **غیرفعال** (5s صرفه‌جویی هر کوین) |
| INTER_COIN_DELAY | 0.05s | **0s** |
| API calls/کوین | 5 | **3** |
| **زمان کل** | **4.8 دقیقه** | **~40 ثانیه** |

### 📊 آستانه BUY

| نسخه | آستانه | BUY signals | Win rate |
|------|--------|-------------|----------|
| V2.8.0 | 0.20 | 1 | - |
| **V2.9.0** | **0.15** | **264** | **53%** |

### 🔧 تغییرات
- `ENABLE_MTF: False` در config
- `INTER_COIN_DELAY_FAST: 0.0`
- `LIMIT: 20` در workflow
- آستانه BUY: 0.20 → 0.15
- آستانه WATCH: 0.10 → 0.08

---

## [V2.8.0] - 2026-10-05 - Minor (رفع 4 باگ بحرانی)

### 🐛 رفع باگ
1. ریپلای تلگرام: تلگرام اول، position_tracker بعد
2. فقط BUY/SELL به تلگرام ارسال شود (نه WAIT)
3. HOLD کاملاً حذف شد از کل پروژه
4. زمان: کاهش rate limit 429 (از 30 پیام به 2-3 پیام)

---

## [V2.7.0] - 2026-10-05 - Minor (رفع باگ نرمال‌سازی)

### 🐛 رفع باگ
- NameError در notifier.py
- نرمال‌سازی pump_score اصلاح شد
- آستانه BUY: 0.45 → 0.20

---

## [V2.6.0] - 2026-10-05 - Minor (ادغام pump_predictor)

### ✨ ویژگی‌ها
- pump_predictor سیگنال اصلی شد
- HOLD → WAIT
- position_tracker در main.py
- send_reply در TelegramNotifier

---

## [V2.5.0] - 2026-10-05 - Minor (سیستم ردیابی پوزیشن)

### ✨ ویژگی‌ها
- ماژول position_tracker.py
- پیام ریپلای تلگرام با سود/زیان

---

## [V2.4.0] - 2026-10-05 - Minor (کشف هوشمند)

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
