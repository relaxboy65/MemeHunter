# 🐸 MemeHunter - ربات پیداکننده میم‌کوین

**نسخه فعلی**: V1.3.1

رباتی که با پایتون اجرا می‌شود، میم‌کوین‌های داغ بازار را از API رایگان **CoinGecko** پیدا می‌کند، چندین اندیکاتور تکنیکال را روی آن‌ها اعمال می‌کند و سیگنال **خرید / فروش / نگه‌داری** صادر می‌کند. داده‌ها در دیتابیس CSV ذخیره و نتایج می‌توانند به کانال تلگرام ارسال شوند.

> **هشدار ریسک**: این پروژه صرفاً ابزار آموزشی است و هیچ‌گونه توصیه مالی محسوب نمی‌شود. میم‌کوین‌ها بسیار پرنوسان و پرریسک هستند. فقط با پولی سرمایه‌گذاری کنید که حاضر به از دست دادن آن هستید.

---

## ✨ امکانات

### 🔍 کشف و فیلتر میم‌کوین
- کشف خودکار از بین 180+ کوین با استفاده از **دسته‌بندی‌های CoinGecko** (meme-token، dog-themed، cat-themed، pump-fun)
- فیلتر پشتیبان با کلمات کلیدی (doge, shib, pepe, floki, ...)
- فیلتر مالی: مارکت‌کپ < 5 میلیارد دلار، حجم 24h > 1 میلیون دلار
- حذف خودکار استیبل‌کوین‌ها

### 📊 اندیکاتورهای تکنیکال (7 فاکتور)
- **RSI** با روش هموارسازی ویلدر (استاندارد صنعتی)
- **MACD** نرمال‌سازی شده با ATR
- **Moving Average** (کوتاه و بلندمدت)
- **Volume Surge** (افزایش حجم)
- **Price Momentum** (مومنتوم قیمت)
- **ATR** (Average True Range) - نوسان بازار
- **Bollinger Bands** - تشخیص اشباع و squeeze

### 🚀 تحلیل‌های پیشرفته (V1.3.1)
- **لیکوییدیتی (Liquidity)**: تحلیل نقدشوندگی و تخمین اسپرد
- **سوییپ (Sweep)**: تشخیص سوییپ لیکوییدیتی (شکست سقف/کف و بازگشت)
- **اردرفلو (Order Flow)**: فشار خرید/فروش، دلتای تجمعی، جذب سفارش
- **والیوم پروفایل (Volume Profile)**: POC، Value Area، شکل پروفایل (P/B/D)

### 🎯 امتیازدهی و سیگنال
- امتیازدهی **7 فاکتوری** با وزن قابل تنظیم
- آستانه‌های قابل تنظیم: ≥0.65 خرید، ≤0.35 فروش
- دلایل شفاف به زبان فارسی برای هر سیگنال
- میزان اطمینان هر سیگنال

### 📤 خروجی‌های متنوع
- جدول ترمینال، گزارش مفصل، JSON، CSV
- **داشبورد HTML** مدرن با طراحی responsive و نوار امتیاز رنگی
- پیش‌نمایش پیام تلگرام با ایموجی و خلاصه سریع

### 💾 داده و نگهداری
- دیتابیس CSV با 24 ستون (شامل ATR و Bollinger)
- نگهداری خودکار 90 روز برای دیتابیس و لاگ
- **کش (cache)** فایل برای کاهش درخواست‌های API (TTL 1 ساعت)

### 🤖 خودکارسازی و نوتیفیکیشن
- ارسال خودکار به **تلگرام** با ایموجی و خلاصه
- اجرای خودکار با **GitHub Actions** هر 6 ساعت
- پشتیبانی از **python-dotenv** برای متغیرهای محیطی
- پشتیبانی اختیاری از **کلید API CoinGecko**

### ⚙️ امکانات پیشرفته
- **بک‌تست** سیگنال‌های گذشته (نرخ موفقیت 7 و 14 روز)
- **هشدار حجم غیرعادی** با z-score آماری
- **محدودیت نرخ پیشرفته** (Token Bucket)
- **پشتیبانی از چند بازه زمانی** (روزانه، 4 ساعته، ساعتی)
- **لایه داده واقعی Binance** (V1.3.1): aggTrades برای CVD واقعی + depth برای اسپرد واقعی
- **Paper Trading** (V1.3.1): ثبت سیگنال و ارزیابی نتیجه بدون ریسک واقعی
- 96 تست واحد (همه موفق)

### 🔖 مدیریت نسخه
- نسخه‌بندی معنایی V1.3.1
- ساخت خودکار فایل زیپ با هر انتشار
- نگهداری حداکثر 3 نسخه اخیر
- CHANGELOG کامل با تاریخچه همه نسخه‌ها

### ⚠️ شفافیت محدودیت‌ها (V1.3.1)

این پروژه با شفافیت کامل درباره منابع داده عمل می‌کند:

| تحلیل | منبع داده | برچسب |
|------|----------|-------|
| **OrderFlow** | Binance aggTrades (اگر کوین لیست‌شده باشد) | ✅ واقعی (CVD واقعی) |
| **OrderFlow** | جهت قیمت CoinGecko (پشتیبان) | 🔮 پروکسی (price-direction) |
| **Liquidity** | Binance depth (اگر کوین لیست‌شده باشد) | ✅ واقعی (اسپرد واقعی) |
| **Liquidity** | حجم CoinGecko (پشتیبان) | 🔮 پروکسی (volume-based) |
| **Sweep** | OHLC از CoinGecko | 🔮 پروکسی (OHLC-based) |
| **Smart Money** | تریدهای بزرگ Binance | 🔮 پروکسی (large trades) |
| **Volume Profile** | قیمت‌های CoinGecko | 🔮 پروکسی (price-binned) |
| **Multi-Timeframe** | Binance klines (اگر کوین لیست‌شده باشد) | ✅ واقعی |

**نکته**: برای کوین‌های فقط DEX (بدون لیست در Binance)، تمام تحلیل‌های پیشرفته به‌صورت پروکسی اجرا می‌شوند.

---

## 📋 قوانین پروژه

این پروژه قوانین مشخصی دارد که در [`RELEASE_RULES.md`](./RELEASE_RULES.md) به‌طور کامل توضیح داده شده است. خلاصه:

1. **نام پروژه**: MemeHunter
2. **فولدر `data/`**: شامل لاگ فعالیت و دیتابیس CSV با نگهداری 90 روز
3. **نسخه‌بندی**: V1.3.1 (Major.Minor.Patch)
4. **ساخت زیپ**: با هر تغییر نسخه، فایل زیپ در `releases/` ساخته می‌شود
5. **نگهداری نسخه**: حداکثر 3 نسخه اخیر در `releases/` نگهداری می‌شود

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

- Python نسخه 3.9 یا بالاتر
- اتصال اینترنت

### مراحل نصب

```bash
# 1. کلون کردن مخزن
git clone https://github.com/YOUR_USERNAME/MemeHunter.git
cd MemeHunter

# 2. ساخت محیط مجازی (پیشنهادی)
python -m venv venv
source venv/bin/activate   # لینوکس/مک
# venv\Scripts\activate    # ویندوز

# 3. نصب وابستگی‌ها
pip install -r requirements.txt
```

---

## 💻 استفاده

### اجرای سریع

```bash
python main.py
```

### گزینه‌های خط فرمان

| گزینه | توضیح | مثال |
|------|-------|------|
| `--format` | قالب خروجی | `table`, `detailed`, `json`, `csv`, `html` |
| `--limit` | حداکثر تعداد کوین | `--limit 20` |
| `--save` | ذخیره گزارش در فایل | `--save` |
| `--telegram` | ارسال به تلگرام (نیاز به تنظیم متغیرها) | `--telegram` |
| `--telegram-preview` | پیش‌نمایش پیام تلگرام | `--telegram-preview` |
| `--advanced` | فعال‌سازی تحلیل‌های پیشرفته (لیکوییدیتی، سوییپ، ...) | `--advanced` |
| `--backtest` | اجرای بک‌تست سیگنال‌های گذشته | `--backtest` |
| `--volume-alert` | فقط هشدار حجم غیرعادی | `--volume-alert` |
| `--verbose` | لاگ‌های جزئی‌تر | `--verbose` |

### مثال‌ها

```bash
# گزارش مفصل و ذخیره در فایل
python main.py --format detailed --save

# پیش‌نمایش پیام تلگرام
python main.py --limit 5 --telegram-preview

# خروجی JSON برای اتصال به ابزار دیگر
python main.py --format json --save

# داشبورد HTML (V1.3.1)
python main.py --format html --save

# اسکن با تحلیل‌های پیشرفته (V1.3.1)
python main.py --advanced --limit 10 --format detailed

# بک‌تست سیگنال‌های گذشته (V1.3.1)
python main.py --backtest

# فقط هشدار حجم غیرعادی (V1.3.1)
python main.py --volume-alert --limit 50
```

---

## 📂 ساختار پروژه

```
MemeHunter/
├── main.py                       # نقطه ورود CLI
├── VERSION                       # نسخه فعلی (V1.3.1)
├── CHANGELOG.md                  # تاریخچه تغییرات نسخه‌ها
├── RELEASE_RULES.md              # قوانین پروژه
├── requirements.txt
├── README.md
├── LICENSE
├── .env.example                  # الگوی متغیرهای محیطی
├── .gitignore
├── .github/
│   └── workflows/
│       └── daily-scan.yml        # GitHub Actions
├── data/                         # پوشه داده (نگهداری 90 روز)
│   ├── activity.log              # لاگ فعالیت
│   ├── coins_database.csv        # دیتابیس ارزهای روز (24 ستون)
│   └── cache/                    # کش API (TTL 1 ساعت)
├── reports/                      # خروجی گزارش‌ها
├── releases/                     # فایل‌های زیپ (حداکثر 3 نسخه)
│   └── MemeHunter-V1.3.1.zip
├── scripts/
│   └── release.py                # اسکریپت مدیریت نسخه
├── tests/                         # 70 تست واحد
│   ├── test_indicators.py
│   ├── test_analyzer.py
│   ├── test_coin_service.py
│   ├── test_advanced_analysis.py  # V1.3.1
│   ├── test_rate_limiter.py       # V1.3.1
│   ├── test_backtest.py           # V1.3.1
│   └── test_volume_alert.py       # V1.3.1
└── src/
    ├── __init__.py
    ├── config.py                 # تنظیمات (نسخه پویا، وزن‌ها، ...)
    ├── version.py                # مدیریت نسخه‌بندی
    ├── logging_setup.py          # لاگ‌نویسی چرخشی 90 روزه
    ├── storage.py                # دیتابیس CSV
    ├── coin_service.py           # اتصال به CoinGecko + کش
    ├── rate_limiter.py           # V1.3.1 - Token Bucket
    ├── indicators.py             # RSI، MACD، MA، ATR، Bollinger
    ├── advanced_analysis.py      # V1.3.1 - لیکوییدیتی/سوییپ/اردرفلو/والیوم پروفایل
    ├── analyzer.py               # ترکیب و صدور سیگنال (7 فاکتور)
    ├── backtest.py                # V1.3.1 - بک‌تست سیگنال‌ها
    ├── volume_alert.py            # V1.3.1 - هشدار حجم غیرعادی
    ├── reporter.py               # قالب‌بندی خروجی متنی
    ├── html_reporter.py          # V1.3.1 - داشبورد HTML
    └── notifier.py               # نوتیفیکیشن تلگرام با ایموجی
```

---

## 🔖 مدیریت نسخه

برای انتشار نسخه جدید از اسکریپت `scripts/release.py` استفاده کنید:

```bash
# رفع خطا
python scripts/release.py patch          # V1.3.1 → V1.3.1

# ویژگی جدید
python scripts/release.py minor          # V1.3.1 → V1.3.1

# تغییر بزرگ
python scripts/release.py major          # V1.3.1 → V1.3.1

# مشاهده نسخه فعلی
python scripts/release.py current

# لیست نسخه‌های منتشر شده
python scripts/release.py list

# پاکسازی نسخه‌های قدیمی
python scripts/release.py cleanup
```

این اسکریپت به‌طور خودکار:
1. نسخه را در فایل `VERSION` به‌روزرسانی می‌کند
2. `README.md` و `daily-scan.yml` را با نسخه جدید به‌روزرسانی می‌کند
3. در `CHANGELOG.md` ثبت می‌کند
4. فایل زیپ در `releases/MemeHunter-V{X.Y.Z}.zip` می‌سازد
5. نسخه‌های قدیمی‌تر از 3 نسخه اخیر را حذف می‌کند

---

## 🧠 نحوه کارکرد

### 1. فیلتر میم‌کوین
ربات ابتدا 100 کوین برتر بازار را از CoinGecko می‌گیرد و با فیلترهای زیر میم‌کوین‌ها را تشخیص می‌دهد:
- کلمات کلیدی: doge، shib، pepe، floki، elon، moon، inu، bonk، wif، ...
- استثنا: استیبل‌کوین‌ها (USDT، USDC، DAI، ...) فیلتر می‌شوند
- شرط مالی: مارکت‌کپ < 5 میلیارد دلار و حجم 24h > 1 میلیون دلار

### 2. محاسبه اندیکاتورها

| اندیکاتور | دوره | کاربرد |
|----------|------|--------|
| RSI | 14 روز | اشباع خرید/فروش |
| MACD | 12/26/9 | روند و فشار خرید/فروش |
| MA | 7/21 روز | روند کوتاه و بلندمدت |
| Volume Surge | 14 روز | توجه بازار |
| Price Momentum | 7 روز | نوسان اخیر |

### 3. امتیازدهی
```
Score = 0.25 × RSI + 0.25 × MACD + 0.25 × Volume + 0.25 × Momentum
```

| امتیاز | سیگنال |
|------|--------|
| ≥ 0.65 | خرید |
| 0.35 - 0.65 | نگه‌داری |
| ≤ 0.35 | فروش / خروج |

---

## 🤖 تنظیم تلگرام

1. با [@BotFather](https://t.me/BotFather) یک ربات بسازید و Token بگیرید
2. Chat ID کانال یا چت خود را بگیرید (از [@userinfobot](https://t.me/userinfobot))
3. متغیرهای محیطی را تنظیم کنید:

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="@your_channel"
python main.py --telegram
```

---

## 🤖 اجرای خودکار با GitHub Actions

فایل `.github/workflows/daily-scan.yml` هر 6 ساعت یک‌بار اجرا می‌شود و گزارش را در `reports/` ذخیره می‌کند. برای تغییر زمان‌بندی، فایل را ویرایش کنید.

برای اجرای تلگرام خودکار در GitHub Actions، در Settings → Secrets ریپو، `TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID` را اضافه کنید.

---

## ❓ سوالات متداول

**آیا برای استفاده نیاز به کلید API دارم؟**  
خیر. از CoinGecko API رایگان استفاده می‌شود. برای حداکثر کارایی، یک کلید رایگان از [coingecko.com/api](https://www.coingecko.com/api) بگیرید.

**دیتابیس CSV کجاست؟**  
در `data/coins_database.csv` ذخیره می‌شود و رکوردهای قدیمی‌تر از 90 روز به‌طور خودکار حذف می‌شوند.

**لاگ فعالیت کجاست؟**  
در `data/activity.log` ذخیره می‌شود و روزانه چرخش می‌کند (90 روز نگهداری).

**چطور نسخه جدید منتشر کنم؟**  
```bash
python scripts/release.py patch   # یا minor / major
```

---

## 📜 لایسنس

MIT License - استفاده آزاد برای اهداف آموزشی و شخصی.

## ⚠️ سلب مسئولیت

این پروژه صرفاً جنبه آموزشی دارد و هیچ‌گونه توصیه مالی نیست. نویسنده هیچ مسئولیتی در قبال زیان‌های احتمالی ناشی از استفاده از این ابزار ندارد. همیشه قبل از هر سرمایه‌گذاری، تحقیق شخصی (DYOR) انجام دهید.
