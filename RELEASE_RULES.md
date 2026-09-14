# قوانین و مقررات پروژه MemeHunter

این قوانین **اولویت اول** پروژه هستند و در هر تغییر باید رعایت شوند.

---

## 1. نام پروژه

- **نام رسمی**: MemeHunter
- **slug (برای نام فایل‌ها و زیپ)**: memehunter
- در همه فایل‌ها، README، Actions و زیپ از این نام استفاده می‌شود.

---

## 2. فولدر `data/` و نگهداری داده

یک فولدر `data/` در ریشه پروژه باید وجود داشته باشد که شامل:

| فایل | توضیح | سیاست نگهداری |
|------|-------|---------------|
| `activity.log` | لاگ فعالیت پروژه (تاریخچه اجراها، خطاها، هشدارها) | **حداقل 90 روز** |
| `activity.log.YYYY-MM-DD` | فایل‌های لاگ چرخشی روزانه | 90 فایل (یک فایل در روز) |
| `coins_database.csv` | دیتابیس ارزهای روز با تمام اندیکاتورها و سیگنال‌ها | **حداقل 90 روز** (رکوردهای قدیمی‌تر خودکار حذف می‌شوند) |

### ساختار `coins_database.csv`

ستون‌ها: `scan_date`, `scan_timestamp`, `coin_id`, `symbol`, `name`, `current_price_usd`, `market_cap_usd`, `volume_24h_usd`, `change_24h_pct`, `change_7d_pct`, `rsi`, `macd_hist`, `ma_short`, `ma_long`, `ma_bullish`, `volume_surge_ratio`, `price_momentum_pct`, `score`, `signal`, `confidence`

---

## 3. نسخه‌بندی معنایی (Semantic Versioning V1.2.3)

فرمت: `V{Major}.{Minor}.{Patch}` (حرف V بزرگ الزامی است)

| عدد | نام | چه زمانی افزایش یابد |
|-----|-----|----------------------|
| اول (Major) | تغییر بزرگ | بازنویسی کامل، تغییرات شکستن رابط (Breaking Changes) |
| دوم (Minor) | تغییر متوسط | افزودن ویژگی‌های جدید سازگار با نسخه قبلی |
| سوم (Patch) | رفع خطا | باگ‌فیکس، بهبودهای کوچک، اصلاح مستندات |

### مثال‌ها

- رفع باگ در اندیکاتور RSI: `V1.0.0 → V1.0.1` (patch)
- افزودن منبع داده DexScreener: `V1.0.1 → V1.1.0` (minor)
- بازنویسی کامل ماژول تحلیل: `V1.1.0 → V2.0.0` (major)

### فایل‌های دخیل در نسخه‌بندی

| فایل | توضیح |
|------|-------|
| `VERSION` | فایل متنی شامل نسخه فعلی (مثل `V1.3.0`) |
| `CHANGELOG.md` | تاریخچه تغییرات هر نسخه |
| `README.md` | شامل نسخه در هدر و عنوان |
| `.github/workflows/daily-scan.yml` | شامل نسخه در نام و توضیحات (CI: lint + test + نسخه) |

### ستون‌های دیتابیس CSV (V1.3.1)

دیتابیس `data/coins_database.csv` اکنون شامل **39 ستون** است:

| دسته | ستون‌ها |
|------|---------|
| **پایه** (V0.1.0) | scan_date, scan_timestamp, coin_id, symbol, name, current_price_usd, market_cap_usd, volume_24h_usd, change_24h_pct, change_7d_pct |
| **اندیکاتورهای اصلی** (V0.1.0) | rsi, macd_hist, ma_short, ma_long, ma_bullish, volume_surge_ratio, price_momentum_pct |
| **نتیجه** (V0.1.0) | score, signal, confidence |
| **اندیکاتورهای پیشرفته** (V1.1.0) | atr, atr_percent, bollinger_percent_b, bollinger_squeeze |
| **تحلیل پیشرفته** (V1.3.0) | liquidity_score, liquidity_is_real, liquidity_spread, liquidity_imbalance, sweep_detected, sweep_type, orderflow_buy_pressure, orderflow_sell_pressure, orderflow_is_real, large_swap_count, large_buys, large_sells, mtf_confluence_score, mtf_aligned_count, data_sources |

**توجه**: `liquidity_is_real` و `orderflow_is_real` برچسب منبع داده هستند:
- `True` = داده واقعی از Binance API
- `False` = پروکسی (CoinGecko heuristics)

### منابع داده پشتیبانی‌شده (V1.3.0)

| منبع | نوع داده | نیاز به کلید؟ | محدودیت نرخ |
|------|---------|---------------|-------------|
| **CoinGecko** | مارکت‌کپ، دسته‌بندی، قیمت تاریخی | اختیاری (Demo key) | 30/min رایگان |
| **Binance Public** | aggTrades (CVD واقعی)، depth (اسپرد/عمق)، klines | ❌ لازم نیست | 1200 وزن/min |
| **DexScreener** | نقدینگی pool DEX، حجم، buys/sells | ❌ لازم نیست | 300/min |
| **GeckoTerminal** | OHLCV تاریخی DEX | ❌ لازم نیست | 30/min |
| **API تخصصی OrderFlow** | داده tick-by-tick تخصصی | ✅ لازم (اختیاری) | بسته به سرویس |

---

## 4. ساخت زیپ نسخه با هر انتشار

با هر بار انتشار نسخه (patch/minor/major):

1. فایل `VERSION` به‌روزرسانی شود
2. `README.md` و فایل workflow با نسخه جدید به‌روزرسانی شوند
3. در `CHANGELOG.md` ثبت شود
4. فایل زیپ در مسیر `releases/MemeHunter-V1.2.3.zip` ساخته شود

**نام فایل زیپ**: `MemeHunter-V{Major}.{Minor}.{Patch}.zip`

### محتوای زیپ

تمام فایل‌های پروژه به‌جز موارد زیر:
- `__pycache__/`, `*.pyc`, `*.pyo`
- `.git/`, `.gitignore` (خود فایل نگه‌داری می‌شود)
- `releases/` (جلوگیری از نسخه‌بندی تودرتو)
- `venv/`, `env/`, `.venv/`, `.env/`
- `data/` (شامل لاگ و دیتابیس CSV، چون داده زمان‌مند است)
- `*.log`

---

## 5. نگهداری حداکثر 3 نسخه

در پوشه `releases/`:

- **حداکثر 3 نسخه اخیر** نگهداری می‌شود
- نسخه‌های قدیمی‌تر به‌طور خودکار با هر انتشار حذف می‌شوند
- ترتیب بر اساس تاریخ ساخت فایل زیپ (mtime) است
- این کار از شلوغی فولدر جلوگیری می‌کند

### مرتب‌سازی

```text
releases/
├── MemeHunter-V1.0.2.zip   (جدیدترین)
├── MemeHunter-V1.0.1.zip
└── MemeHunter-V1.0.0.zip   (قدیمی‌ترین قابل نگهداری)
# V0.9.x و قدیمی‌تر خودکار حذف می‌شوند
```

---

## 6. دستورات مدیریت نسخه

```bash
# انتشار نسخه جدید
python scripts/release.py patch          # رفع خطا
python scripts/release.py minor          # ویژگی جدید
python scripts/release.py major          # تغییر بزرگ

# اطلاعات
python scripts/release.py current        # نسخه فعلی
python scripts/release.py list           # لیست نسخه‌های موجود

# نگهداری
python scripts/release.py cleanup        # حذف نسخه‌های قدیمی
```

---

## 7. اولویت رعایت

این قوانین **اولویت اول** هستند:
- در هر تغییر کد، ابتدا این قوانین رعایت شوند
- قبل از commit، فایل VERSION به‌روز باشد
- لاگ و دیتابیس به‌صورت خودکار در هر اجرا چرخش و پاکسازی می‌شوند
- هرگز نسخه‌ای بدون ساخت زیپ منتشر نشود
