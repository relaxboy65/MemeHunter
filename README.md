# 🐸 MemeHunter V2.9.0

> **ربات پیش‌بینی پامپ میم‌کوین — قبل از پامپ بگو بخر، بعد از پامپ بگو بفروش**
>
> **نسخه**: V2.9.0 | **تاریخ**: 2026-10-05

[![CI V2.9.0](https://github.com/YOUR_USERNAME/MemeHunter/actions/workflows/daily-scan.yml/badge.svg)](https://github.com/YOUR_USERNAME/MemeHunter/actions)

---

## 🎯 هدف

ربات MemeHunter ارزهای در حال پامپ را **قبل از وقوع** پیدا می‌کند:

| سیگنال | معنی |
|--------|------|
| **BUY** | قبل از پامپ (در حال انباشت) → ثبت پوزیشن + پیام تلگرام |
| **SELL** | بعد از پامپ (در حال توزیع) → بستن پوزیشن + محاسبه سود + ریپلای تلگرام |
| **WAIT** | در غیر این صورت (شامل "در حال پامپ - خرید دیر است") |

**سیگنال HOLD وجود ندارد.**

---

## 📦 نصب

```bash
unzip MemeHunter-V2.9.0.zip -d ~/memehunter
cd ~/memehunter
pip install -r requirements.txt
cp .env.example .env  # پر کردن توکن تلگرام
```

---

## 🚀 استفاده

```bash
# اسکن کامل (ـ20 کوین در ~40 ثانیه)
python main.py --limit 20 --format detailed --save --advanced --real-data --telegram

# بک‌تست
python main.py --backtest

# داشبورد HTML
python main.py --format html --save
```

---

## ⚡ بهبود سرعت V2.9.0

| تنظیم | V2.8.0 | V2.9.0 |
|------|--------|--------|
| LIMIT | 30 | **20** |
| MTF API | فعال (5s/کوین) | **غیرفعال** |
| INTER_COIN_DELAY | 0.05s | **0s** |
| API calls/کوین | 5 | **3** |
| **زمان کل** | **4.8 دقیقه** | **~40 ثانیه** |

---

## 🏗️ معماری

```
1. کشف میم‌کوین (CoinGecko trending + categories)
2. داده واقعی (KuCoin: orderflow + liquidity)
3. Pump Predictor (5 نشانه pre-pump)
4. Risk Engine (گیت ریسک)
5. Position Tracker (ثبت → بررسی SL/TP → محاسبه سود)
6. تلگرام (فقط BUY/SELL → ریپلای با نتیجه)
```

---

## 📊 نشانه‌های pre-pump

| نشانه | وزن |
|--------|-----|
| Volume buildup | 30% |
| Bollinger Squeeze | 20% |
| Smart money inflow | 25% |
| Short squeeze setup | 15% |
| Spring pattern | 10% |

---

## 🤖 تلگرام

- **فقط BUY و SELL** ارسال می‌شود (نه WAIT)
- وقتی پوزیشن بسته می‌شود، **ریپلای** به پیام BUY اصلی:

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

---

## ⚠️ سلب مسئولیت

این پروژه صرفاً آموزشی است و توصیه مالی نیست. همیشه DYOR کنید.
