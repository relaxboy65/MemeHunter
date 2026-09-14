#!/usr/bin/env python3
"""
main.py
نقطه ورود اصلی پروژه MemeHunter - ربات پیداکننده میم‌کوین و سیگنال خرید/فروش.

V1.3.0 - اضافه شدن لایه داده واقعی Binance، Paper Trading،
         برچسب پروکسی/واقعی، و خلاصه JSON در لاگ.

استفاده:
    python main.py                            # خروجی جدولی
    python main.py --format detailed          # گزارش مفصل
    python main.py --format json              # خروجی JSON
    python main.py --format html              # داشبورد HTML
    python main.py --limit 20                  # فقط 20 کوین
    python main.py --save                      # ذخیره گزارش
    python main.py --telegram                  # ارسال به تلگرام
    python main.py --telegram-preview          # پیش‌نمایش پیام تلگرام
    python main.py --advanced                  # فعال‌سازی تحلیل پیشرفته
    python main.py --real-data                 # فعال‌سازی Binance واقعی
    python main.py --backtest                  # بک‌تست سیگنال‌ها
    python main.py --volume-alert              # هشدار حجم غیرعادی
    python main.py --paper-trading             # گزارش paper trading
    python main.py --enable-advanced-impact    # تأثیر تحلیل پیشرفته روی امتیاز

مثال:
    python main.py --format detailed --save --telegram-preview --advanced --real-data
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Any

import requests

# بارگذاری متغیرهای محیطی از فایل .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src import (
    settings,
    CoinGeckoClient,
    fetch_meme_candidates,
    enrich_with_history,
    compute_indicators,
    compute_advanced_analysis,
    analyze_coin,
    AnalysisResult,
    Signal,
    format_table,
    format_detailed,
    format_json,
    format_csv,
    save_report,
    format_html,
    save_html_report,
    TelegramNotifier,
    format_telegram_message,
    notify_results,
    cleanup_old_telegram_records,
    setup_logging,
    get_log_path,
    cleanup_old_logs,
    save_results_to_db,
    cleanup_old_db_records,
    get_db_path,
    get_db_stats,
    current_version_string,
    run_backtest,
    format_backtest_report,
    detect_volume_anomaly,
    format_volume_alerts,
    VolumeAlert,
    log_run_summary,
    log_coin_analysis,
    log_data_source,
    record_api_call,
    record_error,
    start_phase,
    end_phase,
    reset_run_stats,
    get_run_summary,
)
from src.binance_provider import BinanceClient
from src.kucoin_provider import KuCoinClient
from src.paper_trading import (
    open_position, close_position, check_open_positions,
    get_paper_trading_stats, format_paper_trading_report,
    get_open_positions,
)


# --------------------------------------------------------------------------- #
# logging
# --------------------------------------------------------------------------- #
setup_logging()
logger = logging.getLogger(settings.PROJECT_NAME.lower())


# --------------------------------------------------------------------------- #
# main scan
# --------------------------------------------------------------------------- #
def run_scan(limit: int = 50, advanced: bool = False,
             real_data: bool = False,
             enable_advanced_impact: bool = False,
             real_only: bool = False,
             dex_data: bool = False,
             use_websocket: bool = False) -> List[AnalysisResult]:
    """
    اجرای کامل اسکن: دریافت داده، محاسبه اندیکاتورها و صدور سیگنال.

    V1.3.1:
    - real_only: فقط کوین‌های با داده واقعی Binance نگه داشته می‌شوند
    - dex_data: استفاده از DexScreener برای میم‌های فقط-DEX
    - use_websocket: داده real-time (اگر کتابخانه نصب باشد)
    """
    # فعال‌سازی تأثیر تحلیل پیشرفته
    if enable_advanced_impact:
        settings.ENABLE_ADVANCED_IMPACT = True

    client = CoinGeckoClient()
    # V1.4.0 - KuCoin اولویت اول؛ Binance پشتیبان
    kucoin = KuCoinClient() if (real_data or settings.ENABLE_KUCOIN) else None
    binance = BinanceClient() if (real_data and settings.ENABLE_BINANCE) else None

    # V1.3.1 - WebSocket اختیاری
    ws_manager = None
    if use_websocket:
        try:
            from src.websocket_stream import BinanceWebSocketManager, is_websocket_available
            if is_websocket_available():
                ws_manager = BinanceWebSocketManager()
                logger.info("WebSocket فعال شد")
            else:
                logger.warning("websocket-client نصب نیست. نصب: pip install websocket-client")
        except (ImportError, RuntimeError) as exc:
            logger.warning("WebSocket فعال نشد: %s", exc)

    # V1.3.1 - DexScreener اختیاری
    dex_client = None
    if dex_data:
        try:
            from src.dex_provider import DexScreenerClient
            dex_client = DexScreenerClient()
            logger.info("DexScreener فعال شد")
        except (ImportError, RuntimeError) as exc:
            logger.warning("DexScreener فعال نشد: %s", exc)

    # V1.3.1 - شروع فاز 1
    from src.logging_setup import start_phase, end_phase
    start_phase("fetch_candidates")
    logger.info("=== مرحله 1: دریافت لیست میم‌کوین‌های کاندید (CoinGecko) ===")
    candidates = fetch_meme_candidates(client, limit=limit)
    end_phase("fetch_candidates", {"candidates": len(candidates)})
    if not candidates:
        logger.warning("هیچ میم‌کوینی پیدا نشد.")
        return []

    # V1.3.1 - شروع فاز 2
    start_phase("analyze_coins")
    logger.info("=== مرحله 2: داده تاریخی + اندیکاتور (اولویت KuCoin) ===")
    results: List[AnalysisResult] = []
    kucoin_available_count = 0
    binance_available_count = 0
    history_from_kucoin = 0
    history_from_cg = 0
    errors_count = 0
    real_only_filtered = 0

    for idx, coin in enumerate(candidates, 1):
        coin_id = coin.get("id", "")
        symbol = (coin.get("symbol") or "").upper()
        current_price = coin.get("current_price") or 0.0
        market_cap = coin.get("market_cap") or 0.0
        logger.info("[%d/%d] تحلیل %s (%s)...", idx, len(candidates), symbol, coin_id)
        try:
            # V1.4.0 - اولویت تاریخچه: KuCoin → CoinGecko
            history: Dict[str, Any] = {}
            history_source = "none"
            if kucoin is not None and settings.PREFER_KUCOIN_HISTORY:
                try:
                    kc_hist = kucoin.get_history_ohlcv(symbol, days=settings.HISTORY_DAYS)
                    if kc_hist and len(kc_hist.get("prices", [])) >= 14:
                        history = kc_hist
                        history_source = "kucoin"
                        history_from_kucoin += 1
                        record_api_call("kucoin", "success", f"history {symbol}")
                        logger.info("  تاریخچه از KuCoin (%d روز)", len(history["prices"]))
                except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                    record_api_call("kucoin", "failed", f"history {symbol}: {exc}")
                    logger.debug("  KuCoin history failed: %s", exc)

            if not history or len(history.get("prices", [])) < 14:
                history = enrich_with_history(client, coin_id, days=settings.HISTORY_DAYS)
                history_source = "coingecko"
                history_from_cg += 1
                record_api_call("coingecko", "success", f"history {symbol}")

            prices = history.get("prices", [])
            volumes = history.get("volumes", [])
            highs = history.get("highs", [])
            lows = history.get("lows", [])
            if len(prices) < 14 or len(volumes) < 14:
                logger.warning("  داده ناکافی برای %s (تنها %d روز)", symbol, len(prices))
                continue

            # محاسبه اندیکاتورهای اصلی
            indicators = compute_indicators(prices, volumes, highs=highs, lows=lows)

            # V1.4.0 - داده واقعی: اول KuCoin، بعد Binance
            real_orderflow = None
            real_liquidity = None
            mtf_data = None
            has_real_data = False

            if kucoin is not None:
                start_phase(f"kucoin_check_{symbol}")
                kc_avail = kucoin.is_available(symbol)
                if kc_avail.available:
                    kucoin_available_count += 1
                    has_real_data = True
                    record_api_call("kucoin", "success", f"{symbol} available")
                    end_phase(f"kucoin_check_{symbol}", {"available": True})

                    start_phase(f"kucoin_data_{symbol}")
                    try:
                        real_orderflow = kucoin.compute_orderflow(
                            symbol, current_price, market_cap
                        )
                        if real_orderflow:
                            logger.info("  OrderFlow KuCoin: CVD=%.2f, buy=%.1f%%",
                                        real_orderflow.cvd,
                                        real_orderflow.buy_pressure * 100)
                            record_api_call("kucoin", "success", f"orderflow {symbol}")
                    except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                        record_api_call("kucoin", "failed", f"orderflow {symbol}: {exc}")
                        logger.debug("  KuCoin orderflow failed: %s", exc)

                    try:
                        real_liquidity = kucoin.compute_liquidity(symbol)
                        if real_liquidity:
                            logger.info("  Liquidity KuCoin: spread=%.3f%%, imbalance=%+.2f",
                                        real_liquidity.spread_pct,
                                        real_liquidity.imbalance)
                            record_api_call("kucoin", "success", f"liquidity {symbol}")
                    except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                        record_api_call("kucoin", "failed", f"liquidity {symbol}: {exc}")
                        logger.debug("  KuCoin liquidity failed: %s", exc)

                    if settings.ENABLE_MULTI_TIMEFRAME and not mtf_data:
                        try:
                            mtf_data = kucoin.get_multi_timeframe_data(
                                symbol, settings.TIMEFRAMES
                            )
                            if mtf_data:
                                record_api_call("kucoin", "success", f"mtf {symbol}")
                        except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                            record_api_call("kucoin", "failed", f"mtf {symbol}: {exc}")

                    end_phase(f"kucoin_data_{symbol}", {
                        "orderflow": bool(real_orderflow),
                        "liquidity": bool(real_liquidity),
                        "mtf": bool(mtf_data),
                        "history": history_source,
                    })
                else:
                    record_api_call("kucoin", "skipped", f"{symbol} not listed")
                    end_phase(f"kucoin_check_{symbol}", {"available": False})

            # پشتیبان Binance اگر KuCoin داده نداد
            if binance is not None and (not has_real_data or real_orderflow is None or real_liquidity is None):
                start_phase(f"binance_check_{symbol}")
                availability = binance.is_available(symbol)
                if availability.available:
                    binance_available_count += 1
                    has_real_data = True
                    record_api_call("binance", "success", f"{symbol} available")
                    end_phase(f"binance_check_{symbol}", {"available": True})

                    start_phase(f"binance_data_{symbol}")
                    if real_orderflow is None:
                        try:
                            real_orderflow = binance.compute_orderflow(
                                symbol, current_price, market_cap
                            )
                            if real_orderflow:
                                logger.info("  OrderFlow Binance: CVD=%.2f, buy=%.1f%%",
                                            real_orderflow.cvd,
                                            real_orderflow.buy_pressure * 100)
                                record_api_call("binance", "success", f"orderflow {symbol}")
                        except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                            record_api_call("binance", "failed", f"orderflow {symbol}: {exc}")
                            logger.debug("  Binance orderflow failed: %s", exc)

                    if real_liquidity is None:
                        try:
                            real_liquidity = binance.compute_liquidity(symbol)
                            if real_liquidity:
                                logger.info("  Liquidity Binance: spread=%.3f%%, imbalance=%+.2f",
                                            real_liquidity.spread_pct,
                                            real_liquidity.imbalance)
                                record_api_call("binance", "success", f"liquidity {symbol}")
                        except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                            record_api_call("binance", "failed", f"liquidity {symbol}: {exc}")
                            logger.debug("  Binance liquidity failed: %s", exc)

                    if settings.ENABLE_MULTI_TIMEFRAME and not mtf_data:
                        try:
                            mtf_data = binance.get_multi_timeframe_data(
                                symbol, settings.TIMEFRAMES
                            )
                            record_api_call("binance", "success", f"mtf {symbol}")
                        except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                            record_api_call("binance", "failed", f"mtf {symbol}: {exc}")

                    if ws_manager and idx <= 5:
                        try:
                            ws_manager.start_coin_stream(symbol)
                            record_api_call("websocket", "success", f"stream {symbol}")
                        except (RuntimeError, OSError) as exc:
                            record_api_call("websocket", "failed", f"stream {symbol}: {exc}")

                    end_phase(f"binance_data_{symbol}", {
                        "orderflow": bool(real_orderflow),
                        "liquidity": bool(real_liquidity),
                        "mtf": bool(mtf_data),
                    })
                else:
                    record_api_call("binance", "skipped", f"{symbol} not listed")
                    end_phase(f"binance_check_{symbol}", {"available": False})

            # DexScreener فقط اگر هنوز liquidity واقعی نداریم
            if dex_client and real_liquidity is None:
                try:
                    start_phase(f"dex_data_{symbol}")
                    dex_pool = dex_client.get_best_pool(symbol)
                    if dex_pool:
                        logger.info("  DEX pool: liquidity=$%.0f, vol24h=$%.0f",
                                    dex_pool.liquidity_usd, dex_pool.volume_24h)
                        record_api_call("dexscreener", "success", symbol)
                        from src.advanced_analysis import LiquidityResult
                        real_liquidity = LiquidityResult(
                            avg_volume_30d=dex_pool.volume_24h,
                            liquidity_score=0.7 if dex_pool.liquidity_usd > 1_000_000 else 0.4,
                            is_liquid=dex_pool.liquidity_usd > 100_000,
                            spread_estimate=0.5 if dex_pool.liquidity_usd > 1_000_000 else 2.0,
                            is_real=False,
                            source="DexScreener pool",
                            proxy_label="پروکسی (DexScreener pool)",
                            notes=dex_pool.notes,
                        )
                    end_phase(f"dex_data_{symbol}", {"found": bool(dex_pool)})
                except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                    record_api_call("dexscreener", "failed", f"{symbol}: {exc}")
                    end_phase(f"dex_data_{symbol}", {"error": str(exc)})

            # V1.3.1 - فیلتر --real-only
            if real_only and not has_real_data:
                real_only_filtered += 1
                logger.info("  فیلتر شد (فقط داده واقعی)")
                continue

            # محاسبه تحلیل‌های پیشرفته
            advanced_pack = None
            if advanced or real_data:
                advanced_pack = compute_advanced_analysis(
                    prices, volumes, highs, lows,
                    real_orderflow=real_orderflow,
                    real_liquidity=real_liquidity,
                    mtf_data=mtf_data,
                )

            result = analyze_coin(coin, indicators, advanced_pack=advanced_pack)
            results.append(result)

            log_coin_analysis(symbol, coin_id, result.signal.value,
                              result.score, result.data_sources,
                              is_real_data=has_real_data)

            logger.info("  سیگنال: %s | امتیاز: %.3f | تاریخچه: %s | داده‌ها: %s",
                        result.signal.value, result.score, history_source,
                        result.data_sources or "پایه")
        except (requests.exceptions.RequestException, ValueError, KeyError,
                OSError, RuntimeError) as exc:
            errors_count += 1
            record_error("scan", str(exc), symbol)
            logger.error("  خطا در تحلیل %s: %s", symbol, exc)
        # V1.4.0 - تأخیر کمتر چون KuCoin محدودیت نرم‌تری دارد
        delay = settings.INTER_COIN_DELAY_FAST if history_source == "kucoin" else settings.INTER_COIN_DELAY_SLOW
        time.sleep(delay)

    end_phase("analyze_coins", {
        "processed": len(results),
        "kucoin_available": kucoin_available_count,
        "binance_available": binance_available_count,
        "history_kucoin": history_from_kucoin,
        "history_coingecko": history_from_cg,
        "errors": errors_count,
        "real_only_filtered": real_only_filtered,
    })

    if ws_manager:
        ws_manager.stop_all()
        logger.info("تمام WebSocketها بسته شدند")

    logger.info(
        "=== تحلیل کامل شد. %d کوین | KuCoin=%d | Binance=%d | "
        "تاریخچه KC=%d CG=%d | فیلتر real-only=%d | خطا=%d ===",
        len(results), kucoin_available_count, binance_available_count,
        history_from_kucoin, history_from_cg, real_only_filtered, errors_count,
    )

    log_run_summary({
        "total_coins": len(results),
        "buy_count": sum(1 for r in results if r.signal == Signal.BUY),
        "sell_count": sum(1 for r in results if r.signal == Signal.SELL),
        "hold_count": sum(1 for r in results if r.signal == Signal.HOLD),
        "kucoin_available": kucoin_available_count,
        "binance_available": binance_available_count,
        "history_kucoin": history_from_kucoin,
        "history_coingecko": history_from_cg,
        "real_only_filtered": real_only_filtered,
        "errors": errors_count,
        "advanced_enabled": advanced,
        "real_data_enabled": real_data,
        "dex_data_enabled": dex_data,
        "websocket_enabled": bool(ws_manager),
    })

    return results


def run_volume_alert_scan(limit: int = 50) -> List[VolumeAlert]:
    """اجرای اسکن هشدار حجم غیرعادی."""
    client = CoinGeckoClient()

    logger.info("=== هشدار حجم غیرعادی: شروع اسکن ===")
    candidates = fetch_meme_candidates(client, limit=limit)
    if not candidates:
        return []

    alerts: List[VolumeAlert] = []
    for idx, coin in enumerate(candidates, 1):
        coin_id = coin.get("id", "")
        symbol = (coin.get("symbol") or "").upper()
        logger.info("[%d/%d] بررسی حجم %s...", idx, len(candidates), symbol)
        try:
            history = enrich_with_history(client, coin_id, days=30)
            volumes = history.get("volumes", [])
            if len(volumes) < 31:
                continue

            alert = detect_volume_anomaly(
                volumes=volumes,
                coin_id=coin_id,
                symbol=symbol,
                name=coin.get("name", ""),
                lookback=settings.VOLUME_ANOMALY_WINDOW,
            )
            if alert and alert.is_anomaly:
                alerts.append(alert)
                logger.info("  هشدار! %s حجم %.1fx میانگین",
                            symbol, alert.volume_ratio)
        except (requests.exceptions.RequestException, ValueError, KeyError,
                OSError, RuntimeError) as exc:
            logger.error("  خطا در بررسی %s: %s", symbol, exc)
        time.sleep(settings.REQUEST_DELAY)

    return alerts


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=settings.PROJECT_NAME,
        description=f"{settings.PROJECT_NAME} {settings.PROJECT_VERSION} - ربات میم‌کوین",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--format", "-f",
        choices=["table", "detailed", "json", "csv", "html"],
        default="table",
        help="قالب خروجی (پیش‌فرض: table)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=30,
        help="حداکثر تعداد میم‌کوین (پیش‌فرض: 30)",
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="ذخیره گزارش در فایل",
    )
    parser.add_argument(
        "--telegram", "-t",
        action="store_true",
        help="ارسال به تلگرام",
    )
    parser.add_argument(
        "--telegram-preview",
        action="store_true",
        help="پیش‌نمایش پیام تلگرام",
    )
    parser.add_argument(
        "--advanced", "-a",
        action="store_true",
        help="فعال‌سازی تحلیل‌های پیشرفته (لیکوییدیتی، سوییپ، اردرفلو، والیوم پروفایل)",
    )
    parser.add_argument(
        "--real-data", "-r",
        action="store_true",
        help="استفاده از داده واقعی Binance برای OrderFlow/Liquidity (V1.3.0)",
    )
    parser.add_argument(
        "--enable-advanced-impact",
        action="store_true",
        help="تأثیر تحلیل پیشرفته روی امتیاز نهایی (V1.3.0)",
    )
    parser.add_argument(
        "--real-only", "-R",
        action="store_true",
        help="فقط کوین‌هایی که داده واقعی Binance دارند (حالت محافظه‌کارانه - V1.3.1)",
    )
    parser.add_argument(
        "--use-websocket", "-w",
        action="store_true",
        help="استفاده از WebSocket برای داده real-time (V1.3.1 - نیاز به websocket-client)",
    )
    parser.add_argument(
        "--dex-data",
        action="store_true",
        help="استفاده از DexScreener برای میم‌کوین‌های فقط-DEX (V1.3.1)",
    )
    parser.add_argument(
        "--backtest", "-b",
        action="store_true",
        help="اجرای بک‌تست سیگنال‌های گذشته",
    )
    parser.add_argument(
        "--volume-alert",
        action="store_true",
        help="فقط هشدار حجم غیرعادی",
    )
    parser.add_argument(
        "--paper-trading",
        action="store_true",
        help="گزارش paper trading",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="نمایش لاگ‌های جزئی‌تر",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # V1.3.1 - ریست آمار اجرا
    reset_run_stats()

    version = current_version_string()
    start_time = time.time()
    logger.info("%s شروع به کار کرد - نسخه %s", settings.PROJECT_NAME, version)

    print()
    print("=" * 70)
    print(f"  {settings.PROJECT_NAME} {version}")
    print("  ربات پیداکننده میم‌کوین و سیگنال خرید/فروش")
    print(f"  منابع: CoinGecko" +
          (" + Binance (واقعی)" if args.real_data else "") +
          " | هشدار: فقط آموزشی")
    print("=" * 70)
    print()

    # حالت paper trading
    if args.paper_trading:
        print(format_paper_trading_report())
        open_pos = get_open_positions()
        if open_pos:
            print(f"\nپوزیشن‌های باز ({len(open_pos)}):")
            for p in open_pos:
                print(f"  {p.symbol} @ ${p.entry_price:.6f} "
                      f"(SL=${p.stop_loss:.6f}, TP=${p.take_profit:.6f})")
        return 0

    # حالت volume alert
    if args.volume_alert:
        alerts = run_volume_alert_scan(limit=args.limit)
        output = format_volume_alerts(alerts)
        print(output)
        if args.save:
            path = save_report(output, fmt="txt")
            print(f"\n✓ گزارش ذخیره شد: {path}")
        if args.telegram:
            notifier = TelegramNotifier()
            if notifier.is_configured:
                notifier.send_message(output)  # returns (ok, ids)
        return 0

    # حالت backtest
    if args.backtest:
        stats = run_backtest(days_back=30, hold_days=7)
        output = format_backtest_report(stats)
        print(output)
        if args.save:
            path = save_report(output, fmt="txt")
            print(f"\n✓ گزارش ذخیره شد: {path}")
        return 0

    # حالت اسکن معمولی
    results = run_scan(
        limit=args.limit,
        advanced=args.advanced,
        real_data=args.real_data,
        enable_advanced_impact=args.enable_advanced_impact,
        real_only=args.real_only,
        dex_data=args.dex_data,
        use_websocket=args.use_websocket,
    )
    if not results:
        print("هیچ نتیجه‌ای برای نمایش وجود ندارد.")
        logger.warning("اسکن بدون نتیجه پایان یافت")
        return 1

    # V1.3.0 - بررسی پوزیشن‌های paper trading باز
    if settings.ENABLE_PAPER_TRADING:
        current_prices = {r.symbol: r.current_price for r in results}
        closed_positions = check_open_positions(current_prices)
        if closed_positions:
            print(f"\n✓ {len(closed_positions)} پوزیشن paper trading بسته شد:")
            for pos in closed_positions:
                print(f"  {pos.symbol} {pos.status} PnL: {pos.pnl_pct:+.2f}% ({pos.close_reason})")

        # باز کردن پوزیشن جدید برای سیگنال‌های خرید
        for r in results:
            if r.signal == Signal.BUY and r.confidence > settings.ADVANCED_MIN_CONFIDENCE:
                open_position(r.symbol, r.name, r.current_price, r.score)

    # ذخیره در دیتابیس CSV
    saved_count = save_results_to_db(results)
    logger.info("%d رکورد در دیتابیس CSV ذخیره شد", saved_count)

    # پاکسازی رکوردهای قدیمی‌تر از 90 روز
    deleted = cleanup_old_db_records()
    deleted_tg = cleanup_old_telegram_records()
    if deleted_tg:
        logger.info("%d رکورد قدیمی تلگرام حذف شد", deleted_tg)
    if deleted > 0:
        logger.info("%d رکورد قدیمی حذف شد", deleted)
    deleted_logs = cleanup_old_logs()
    if deleted_logs > 0:
        logger.info("%d فایل لاگ قدیمی حذف شد", deleted_logs)

    # فرمت‌بندی خروجی
    backtest_text = None
    if args.format == "detailed":
        try:
            stats = run_backtest(days_back=30, hold_days=7)
            if stats.total_buy > 0 or stats.total_sell > 0:
                backtest_text = format_backtest_report(stats)
        except (ValueError, OSError) as exc:
            logger.debug("بک‌تست اجرا نشد: %s", exc)

    if args.format == "table":
        output = format_table(results)
    elif args.format == "detailed":
        output = format_detailed(results)
        if backtest_text:
            output += "\n\n" + backtest_text
    elif args.format == "json":
        output = format_json(results)
    elif args.format == "csv":
        output = format_csv(results)
    elif args.format == "html":
        paper_stats = None
        if settings.ENABLE_PAPER_TRADING:
            paper_stats = get_paper_trading_stats()
        output = format_html(results, backtest_report=backtest_text,
                              paper_trading_stats=paper_stats)
    else:
        output = format_table(results)

    if args.save:
        ext = {"table": "txt", "detailed": "txt", "json": "json",
               "csv": "csv", "html": "html"}[args.format]
        if args.format == "html":
            path = save_html_report(output)
        else:
            path = save_report(output, fmt=ext)
        print(f"\n✓ گزارش ذخیره شد: {path}")

    if args.format != "html":
        print(output)
    else:
        print(f"\n✓ داشبورد HTML تولید شد.")

    # پیش‌نمایش / ارسال تلگرام — V1.4.2
    paper_stats = None
    if settings.ENABLE_PAPER_TRADING:
        paper_stats = get_paper_trading_stats()
    run_meta = {
        "duration_seconds": time.time() - start_time,
        "history_kucoin": sum(
            1 for r in results if r.data_sources and "واقعی" in (r.data_sources or "")
        ),
        "history_coingecko": sum(
            1 for r in results if r.data_sources and "واقعی" not in (r.data_sources or "")
        ),
    }
    telegram_message = format_telegram_message(
        results, paper_trading_stats=paper_stats, run_meta=run_meta
    )
    if args.telegram_preview:
        print()
        print("=" * 70)
        print(f"  {settings.PROJECT_NAME} - پیش‌نمایش پیام تلگرام")
        print("=" * 70)
        print()
        print(telegram_message)
        print()
        print("=" * 70)
        print(f"طول پیام: {len(telegram_message)} کاراکتر")
        print("=" * 70)

    # ارسال به تلگرام + ذخیره message_id
    if args.telegram:
        from src.notifier import notify_results as _notify
        ok, msg_ids = _notify(
            results, paper_trading_stats=paper_stats, run_meta=run_meta
        )
        if ok:
            print(f"\n✓ پیام‌های تلگرام ارسال شد — تعداد: {len(msg_ids)} (هر ارز یک پیام جدا)")
            print(f"  message_idها: {msg_ids}")
            print("  مشخصات هر پیام در data/telegram_messages.csv ذخیره شد (برای ریپلای چک نتیجه).")
        else:
            notifier = TelegramNotifier()
            if not notifier.is_configured:
                print("\n✗ تلگرام پیکربندی نشده. تنظیم کنید:")
                print("  export TELEGRAM_BOT_TOKEN='...'")
                print("  export TELEGRAM_CHAT_ID='...'")
            else:
                print("\n✗ ارسال تلگرام ناموفق بود.")

    print("\n⚠  هشدار ریسک: میم‌کوین‌ها بسیار نوسانی هستند. این سیگنال‌ها توصیه مالی نیستند.")

    # اطلاعات نگهداری داده
    print()
    print("-" * 70)
    print(f"  فایل لاگ فعالیت:    {get_log_path()}")
    print(f"  فایل دیتابیس CSV:  {get_db_path()}")
    stats = get_db_stats()
    print(f"  آمار دیتابیس:       {stats['total_records']} رکورد | "
          f"{stats['unique_coins']} کوین منحصر | "
          f"آخرین اسکن: {stats['last_scan'] or '-'}")
    print(f"  سیاست نگهداری:     لاگ و دیتابیس 90 روز نگهداری می‌شوند")

    # V1.3.0 - خلاصه منابع داده
    real_count = sum(1 for r in results if "واقعی" in (r.data_sources or ""))
    proxy_count = sum(1 for r in results if "پروکسی" in (r.data_sources or ""))
    if real_count + proxy_count > 0:
        print(f"  منابع داده:        {real_count} کوین با داده واقعی، "
              f"{proxy_count} با پروکسی")
    print("-" * 70)

    # ثبت زمان اجرا
    duration = time.time() - start_time
    logger.info("%s با موفقیت پایان یافت - نسخه %s - مدت: %.1f ثانیه",
                settings.PROJECT_NAME, version, duration)
    log_run_summary({
        "duration_seconds": round(duration, 2),
        "status": "success",
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
