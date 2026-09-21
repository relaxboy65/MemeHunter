"""
__init__.py
بسته src - ربات پیداکننده میم‌کوین - پروژه MemeHunter.
"""
from .config import settings, PROJECT_NAME, PROJECT_SLUG, PROJECT_VERSION
from .coin_service import CoinGeckoClient, fetch_meme_candidates, enrich_with_history, FileCache
from .binance_provider import BinanceClient, OrderFlowReal, LiquidityReal
from .kucoin_provider import KuCoinClient, KuCoinAvailability
from .dex_provider import DexScreenerClient, GeckoTerminalClient, DexPoolData
from .indicators import (
    compute_indicators, IndicatorPack,
    rsi, macd, ma_trend, volume_surge, price_momentum, atr, bollinger_bands,
)
from .advanced_analysis import (
    compute_advanced_analysis, AdvancedAnalysisPack,
    analyze_liquidity, analyze_sweep, analyze_orderflow, analyze_volume_profile,
    analyze_mtf_confluence, LiquidityResult,
)
from .analyzer import analyze_coin, AnalysisResult, Signal
from .reporter import format_table, format_detailed, format_json, format_csv, save_report
from .html_reporter import format_html, save_html_report
from .notifier import (
    TelegramNotifier,
    format_telegram_message,
    notify_results,
                    get_message_id_for_symbol,
    format_coin_message,
    format_telegram_parts,
)
from .version import Version, read_version, write_version, bump_and_save, current_version_string
from .logging_setup import (
    setup_logging, get_log_path, cleanup_old_logs,
    log_run_summary, log_coin_analysis, log_run_start, log_data_source,
    record_api_call, record_error, start_phase, end_phase,
    reset_run_stats, get_run_summary,
)
from .storage import (
    save_results_to_db,
    cleanup_old_db_records,
    read_recent_records,
    get_db_path,
    get_db_stats,
)
from .rate_limiter import get_rate_limiter, TokenBucketRateLimiter
from .backtest import run_backtest, format_backtest_report, BacktestStats
from .volume_alert import detect_volume_anomaly, format_volume_alerts, VolumeAlert
from .paper_trading import (
    open_position, close_position, check_open_positions,
    get_paper_trading_stats, format_paper_trading_report,
    get_open_positions, PaperPosition,
)
# V2.0 - ماژول‌های جدید حرفه‌ای
from .walk_forward import (
    run_walk_forward_analysis, format_walk_forward_report,
    WalkForwardResult, WalkForwardReport,
)
from .cost_model import estimate_costs, apply_costs_to_return, get_cost_tier, TradeCosts
from .monte_carlo import run_monte_carlo, format_monte_carlo_report, MonteCarloResult
from .regime_detector import detect_regime, format_regime_report, MarketRegime, RegimeResult
from .funding_oi import FundingOIClient, FundingOIResult, format_funding_oi_report
from .smc_detector import analyze_smc, format_smc_report, SMCResult
from .wyckoff import analyze_wyckoff, WyckoffResult
from .kelly_sizing import compute_kelly, volatility_targeting, combined_sizing, KellyResult
from .sentiment import get_sentiment, SentimentResult
from .portfolio import analyze_portfolio, PortfolioResult

__all__ = [
    # config
    "settings",
    "PROJECT_NAME",
    "PROJECT_SLUG",
    "PROJECT_VERSION",
    # coin_service
    "CoinGeckoClient",
    "fetch_meme_candidates",
    "enrich_with_history",
    "FileCache",
    # kucoin
    "KuCoinClient",
    "KuCoinAvailability",
    # binance
    "BinanceClient",
    "OrderFlowReal",
    "LiquidityReal",
    # indicators
    "compute_indicators",
    "IndicatorPack",
    "rsi",
    "macd",
    "ma_trend",
    "volume_surge",
    "price_momentum",
    "atr",
    "bollinger_bands",
    # advanced analysis
    "compute_advanced_analysis",
    "AdvancedAnalysisPack",
    "analyze_liquidity",
    "analyze_sweep",
    "analyze_orderflow",
    "analyze_volume_profile",
    # analyzer
    "analyze_coin",
    "AnalysisResult",
    "Signal",
    # reporter
    "format_table",
    "format_detailed",
    "format_json",
    "format_csv",
    "save_report",
    # html reporter
    "format_html",
    "save_html_report",
    # notifier
    "TelegramNotifier",
    "format_telegram_message",
    "format_telegram_parts",
        "notify_results",
        # version
    "Version",
    "read_version",
    "write_version",
    "bump_and_save",
    "current_version_string",
    # logging
    "setup_logging",
    "get_log_path",
    "cleanup_old_logs",
    # storage
    "save_results_to_db",
    "cleanup_old_db_records",
    "read_recent_records",
    "get_db_path",
    "get_db_stats",
    # rate limiter
    "get_rate_limiter",
    "TokenBucketRateLimiter",
    # backtest
    "run_backtest",
    "format_backtest_report",
    "BacktestStats",
    # volume alert
    "detect_volume_anomaly",
    "format_volume_alerts",
    "VolumeAlert",
]
