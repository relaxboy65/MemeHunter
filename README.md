# 🐸 MemeHunter V2.8.0

> **ربات پیش‌بینی پامپ میم‌کوین — قبل از پامپ بگو بخر، بعد از پامپ بگو بفروش**
>
> **نسخه فعلی**: V2.8.0
> **تاریخ**: 2026-10-05

[![CI V2.8.0](https://github.com/YOUR_USERNAME/MemeHunter/actions/workflows/daily-scan.yml/badge.svg?branch=main)](https://github.com/YOUR_USERNAME/MemeHunter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-V2.8.0-green.svg)](./VERSION)

---

## 🎯 هدف

ربات MemeHunter ارزهای در حال پامپ را **قبل از وقوع** پیدا می‌کند:

1. **BUY** → قبل از پامپ (در حال انباشت)
2. **SELL** → بعد از پامپ (در حال توزیع)
3. **WAIT** → در غیر این صورت (شامل "در حال پامپ - خرید دیر است")

**سیگنال HOLD وجود ندارد.** فقط BUY/SELL/WAIT.

---

## 📦 نصب

```bash
unzip MemeHunter-V2.8.0.zip -d ~/memehunter
cd ~/memehunter
pip install -r requirements.txt
cp .env.example .env  # پر کردن توکن تلگرام
```

---

## 🚀 استفاده

```bash
# اسکن کامل
python main.py --limit 30 --format detailed --save --advanced --real-data --telegram

# فقط بک‌تست
python main.py --backtest

# داشبورد HTML
python main.py --format html --save
```

---

## 🏗️ معماری

```
Layer 1: کشف میم‌کوین (CoinGecko trending + categories)
Layer 2: داده واقعی (KuCoin: orderflow + liquidity + MTF)
Layer 3: Pump Predictor (5 نشانه pre-pump)
Layer 4: Risk Engine (gate برای معامله)
Layer 5: Position Tracker (ثبت BUY → بررسی SL/TP → SELL → محاسبه سود)
Layer 6: تلگرام (فقط BUY/SELL ارسال → ریپلای با نتیجه)
```

---

## 📊 نشانه‌های pre-pump (سیگنال خرید)

| نشانه | وزن | منبع |
|--------|-----|------|
| Volume buildup | 30% | حجم در حال افزایش + قیمت ثابت |
| Bollinger Squeeze | 20% | فشار نوسان قبل از انفجار |
| Smart money inflow | 25% | تریدهای بزرگ خرید > فروش |
| Short squeeze setup | 15% | funding منفی + OI افزایش |
| Spring pattern | 10% | تست کف و برگشت با حجم کم |

---

## 📊 نشانه‌های post-pump (سیگنال فروش)

- رشد 20%+ + حجم 2x = توزیع قوی
- رشد 10%+ + حجم 1.5x = خستگی بازار
- Funding rate خیلی مثبت = long squeeze risk

---

## 🤖 تلگرام

- **فقط BUY و SELL** به تلگرام ارسال می‌شود (نه WAIT)
- وقتی پوزیشن بسته می‌شود، **ریپلای** به پیام BUY اصلی ارسال می‌شود:

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

## 📂 ساختار

```
MemeHunter/
├── main.py                  # نقطه ورود
├── VERSION                  # V2.8.0
├── src/
│   ├── pump_predictor.py    # پیش‌بینی پامپ (سیگنال اصلی)
│   ├── position_tracker.py  # ردیابی پوزیشن + محاسبه سود
│   ├── risk_engine.py       # گیت ریسک
│   ├── meme_discovery.py     # کشف میم‌کوین‌های فعال
│   ├── notifier.py          # تلگرام (فقط BUY/SELL + ریپلای)
│   └── ...
├── tests/                   # 131 تست
└── .github/workflows/       # CI V2.8.0
```

---

## ⚠️ سلب مسئولیت

این پروژه صرفاً آموزشی است و توصیه مالی نیست. همیشه DYOR کنید.
