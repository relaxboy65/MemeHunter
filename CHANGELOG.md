# 📜 CHANGELOG - MemeHunter

---

## [V1.4.6] - 2026-09-14

### 💾 یکپارچه‌سازی message_id در دیتابیس
- فایل `telegram_messages.csv` **حذف شد**
- ستون جدید `telegram_message_id` در `data/coins_database.csv`
- ترتیب اجرا: ارسال تلگرام → ست شدن message_id روی هر ارز → ذخیره در همان CSV
- برای ریپلای نتیجه بعدی از همین ستون استفاده می‌شود

### 🔧 ورک‌فلو
- نام: `MemeHunter CI V1.4.6`
- فقط `coins_database.csv` به ریپو commit می‌شود

---

## [V1.4.5] - 2026-09-14

### دیتابیس داخل ریپو
- CSV در data/ ریپو + commit پس از اسکن
- Artifact فقط لاگ

---

## [V1.4.4] - 2026-09-14

### تأیید ذخیره روی دیسک
