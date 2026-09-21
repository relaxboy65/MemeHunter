"""
backtest_pnl.py
بک‌تست واقعی با محاسبه سود/زیان و شاخص‌های عملکرد.

این ماژول به‌جای فقط شمارش win rate، شبیه‌سازی کامل معاملات را
با مدیریت سرمایه و محاسبه شاخص‌های حرفه‌ای انجام می‌دهد.
"""
from __future__ import annotations

import csv
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from .config import settings


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class BacktestTrade:
    """یک ترید در شبیه‌سازی."""
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    hold_days: int
    position_size_usd: float
    quantity: float
    pnl_usd: float
    pnl_pct: float
    signal_score: float
    exit_reason: str  # 'take_profit', 'stop_loss', 'time_exit', 'signal_exit'


@dataclass
class BacktestPerformance:
    """شاخص‌های عملکرد کامل."""
    # آمار پایه
    initial_capital: float = 10000.0
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    # شاخص‌های حرفه‌ای
    win_rate: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0  # gross profit / gross loss
    expectancy: float = 0.0     # میانگین بازده مورد انتظار هر ترید
    sharpe_ratio: float = 0.0   # شاخص شارپ سالانه
    max_drawdown_pct: float = 0.0
    # جزئیات
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    avg_hold_days: float = 0.0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[str, float]] = field(default_factory=list)  # (date, capital)


def run_backtest_pnl(csv_path: Path,
                     initial_capital: float = 10000.0,
                     position_size_pct: float = 0.10,
                     stop_loss_pct: float = 0.08,
                     take_profit_pct: float = 0.15,
                     max_hold_days: int = 7,
                     buy_threshold: float = 0.55,
                     sell_threshold: float = 0.40) -> BacktestPerformance:
    """
    اجرای بک‌تست کامل با مدیریت سرمایه.

    استراتژی:
    - وقتی score ≥ buy_threshold، خرید با position_size_pct از سرمایه
    - Stop loss در -stop_loss_pct
    - Take profit در +take_profit_pct
    - Time exit در max_hold_days
    - اگر signal SELL شد، خروج فوری
    """
    if not csv_path.exists():
        logger.warning("CSV file not found: %s", csv_path)
        return BacktestPerformance(initial_capital=initial_capital, final_capital=initial_capital)

    # Load and group data by symbol
    by_symbol: Dict[str, List[dict]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row.get("scan_timestamp", 0))
                symbol = row.get("symbol", "")
                price = float(row.get("current_price_usd", 0))
                score = float(row.get("score", 0)) if row.get("score") else 0
                if price <= 0 or not symbol:
                    continue
                by_symbol.setdefault(symbol, []).append({
                    'ts': ts,
                    'date': row.get('scan_date', ''),
                    'price': price,
                    'score': score,
                    'signal': row.get('signal', ''),
                    'rsi': float(row['rsi']) if row.get('rsi') else None,
                })
            except (ValueError, TypeError, KeyError):
                continue

    # Sort each symbol by timestamp
    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda x: x['ts'])

    # Get all unique timestamps sorted
    all_timestamps = sorted(set(r['ts'] for records in by_symbol.values() for r in records))

    # Simulate trading
    capital = initial_capital
    open_positions: Dict[str, Dict] = {}  # symbol -> position
    trades: List[BacktestTrade] = []
    equity_curve: List[Tuple[str, float]] = []

    # Track for max drawdown
    peak_capital = initial_capital
    max_drawdown = 0.0

    # Daily returns for Sharpe ratio
    daily_returns: List[float] = []

    prev_capital = initial_capital

    for ts in all_timestamps:
        date_str = ''
        # Check exit conditions for open positions
        for symbol in list(open_positions.keys()):
            position = open_positions[symbol]
            records = by_symbol.get(symbol, [])

            # Find current price for this timestamp
            current = None
            for r in records:
                if r['ts'] == ts:
                    current = r
                    date_str = r['date']
                    break
                if r['ts'] > ts:
                    break

            if current is None:
                continue

            current_price = current['price']
            entry_price = position['entry_price']
            hold_days = (ts - position['entry_ts']) // 86400

            # Check exit conditions
            exit_reason = None
            pnl_pct = (current_price - entry_price) / entry_price * 100

            if pnl_pct <= -stop_loss_pct * 100:
                exit_reason = 'stop_loss'
            elif pnl_pct >= take_profit_pct * 100:
                exit_reason = 'take_profit'
            elif hold_days >= max_hold_days:
                exit_reason = 'time_exit'
            elif current['score'] <= sell_threshold and current['signal'] in ('فروش', 'SELL'):
                exit_reason = 'signal_exit'

            if exit_reason:
                # Close position
                pnl_usd = position['quantity'] * (current_price - entry_price)
                capital += position['position_size_usd'] + pnl_usd
                trades.append(BacktestTrade(
                    symbol=symbol,
                    entry_date=position['entry_date'],
                    entry_price=entry_price,
                    exit_date=current['date'],
                    exit_price=current_price,
                    hold_days=hold_days,
                    position_size_usd=position['position_size_usd'],
                    quantity=position['quantity'],
                    pnl_usd=pnl_usd,
                    pnl_pct=pnl_pct,
                    signal_score=position['entry_score'],
                    exit_reason=exit_reason,
                ))
                del open_positions[symbol]

        # Check entry conditions
        for symbol, records in by_symbol.items():
            if symbol in open_positions:
                continue  # already have position
            if len(open_positions) >= 5:  # max 5 positions
                break

            # Find current record
            current = None
            for r in records:
                if r['ts'] == ts:
                    current = r
                    date_str = r['date']
                    break
                if r['ts'] > ts:
                    break
            if current is None:
                continue

            if current['score'] >= buy_threshold:
                # Open position
                position_size = capital * position_size_pct
                if position_size < 10:  # min $10
                    continue
                quantity = position_size / current['price']
                open_positions[symbol] = {
                    'entry_date': current['date'],
                    'entry_ts': ts,
                    'entry_price': current['price'],
                    'entry_score': current['score'],
                    'position_size_usd': position_size,
                    'quantity': quantity,
                }
                capital -= position_size
                break  # one position per timestamp

        # Track equity
        total_equity = capital
        for pos_sym, pos in open_positions.items():
            # Use entry price for simplicity (mark-to-market would be better)
            records = by_symbol.get(pos_sym, [])
            current_price = pos['entry_price']  # fallback
            for r in records:
                if r['ts'] == ts:
                    current_price = r['price']
                    break
            total_equity += pos['quantity'] * current_price

        equity_curve.append((date_str or 'unknown', total_equity))

        # Daily return
        if prev_capital > 0:
            daily_return = (total_equity - prev_capital) / prev_capital
            daily_returns.append(daily_return)
        prev_capital = total_equity

        # Max drawdown - only when we have real equity (not 0)
        if total_equity > 0:
            if total_equity > peak_capital:
                peak_capital = total_equity
            drawdown = (peak_capital - total_equity) / peak_capital * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    # Close remaining positions at last known prices
    for symbol, pos in list(open_positions.items()):
        records = by_symbol.get(symbol, [])
        if records:
            last_price = records[-1]['price']
            pnl_usd = pos['quantity'] * (last_price - pos['entry_price'])
            pnl_pct = (last_price - pos['entry_price']) / pos['entry_price'] * 100
            capital += pos['position_size_usd'] + pnl_usd
            trades.append(BacktestTrade(
                symbol=symbol,
                entry_date=pos['entry_date'],
                entry_price=pos['entry_price'],
                exit_date=records[-1]['date'],
                exit_price=last_price,
                hold_days=(records[-1]['ts'] - pos['entry_ts']) // 86400,
                position_size_usd=pos['position_size_usd'],
                quantity=pos['quantity'],
                pnl_usd=pnl_usd,
                pnl_pct=pnl_pct,
                signal_score=pos['entry_score'],
                exit_reason='end_of_data',
            ))
        del open_positions[symbol]

    # Calculate performance metrics
    perf = BacktestPerformance(
        initial_capital=initial_capital,
        final_capital=capital,
        total_return_pct=(capital - initial_capital) / initial_capital * 100,
        total_trades=len(trades),
        trades=trades,
        equity_curve=equity_curve,
        max_drawdown_pct=max_drawdown,
    )

    winning = [t for t in trades if t.pnl_usd > 0]
    losing = [t for t in trades if t.pnl_usd <= 0]

    perf.winning_trades = len(winning)
    perf.losing_trades = len(losing)
    perf.win_rate = len(winning) / len(trades) * 100 if trades else 0
    perf.avg_win_pct = sum(t.pnl_pct for t in winning) / len(winning) if winning else 0
    perf.avg_loss_pct = sum(t.pnl_pct for t in losing) / len(losing) if losing else 0

    gross_profit = sum(t.pnl_usd for t in winning)
    gross_loss = abs(sum(t.pnl_usd for t in losing))
    perf.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Expectancy: average P&L per trade
    total_pnl = sum(t.pnl_usd for t in trades)
    perf.expectancy = total_pnl / len(trades) if trades else 0

    if trades:
        perf.best_trade_pct = max(t.pnl_pct for t in trades)
        perf.worst_trade_pct = min(t.pnl_pct for t in trades)
        perf.avg_hold_days = sum(t.hold_days for t in trades) / len(trades)

    # Sharpe Ratio (annualized, assuming daily data)
    if len(daily_returns) > 1:
        avg_return = statistics.mean(daily_returns)
        std_return = statistics.stdev(daily_returns)
        if std_return > 0:
            # Annualize: sqrt(365) for daily
            perf.sharpe_ratio = (avg_return / std_return) * math.sqrt(365)

    return perf


def format_backtest_pnl(perf: BacktestPerformance) -> str:
    """قالب‌بندی گزارش بک‌تست کامل."""
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("  📊 گزارش بک‌تست با سرمایه واقعی")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  💰 سرمایه اولیه:      ${perf.initial_capital:,.2f}")
    lines.append(f"  💰 سرمایه نهایی:      ${perf.final_capital:,.2f}")
    lines.append(f"  📈 بازده کل:           {perf.total_return_pct:+.2f}%")
    lines.append(f"  📉 حداکثر drawdown:    {perf.max_drawdown_pct:.2f}%")
    lines.append("")
    lines.append(f"  --- آمار تریدها ---")
    lines.append(f"  کل تریدها:             {perf.total_trades}")
    lines.append(f"  سودده:                 {perf.winning_trades} ({perf.win_rate:.1f}%)")
    lines.append(f"  زیان‌ده:               {perf.losing_trades} ({100-perf.win_rate:.1f}%)")
    lines.append("")
    lines.append(f"  --- شاخص‌های حرفه‌ای ---")
    lines.append(f"  📊 Profit Factor:      {perf.profit_factor:.2f}")
    lines.append(f"  💵 Expectancy:         ${perf.expectancy:+.2f} per trade")
    lines.append(f"  📈 Sharpe Ratio:       {perf.sharpe_ratio:.2f} (annualized)")
    lines.append(f"  ⏱️ میانگین نگهداری:    {perf.avg_hold_days:.1f} روز")
    lines.append("")
    lines.append(f"  --- بهترین/بدترین ---")
    lines.append(f"  🟢 بهترین ترید:        {perf.best_trade_pct:+.2f}%")
    lines.append(f"  🔴 بدترین ترید:        {perf.worst_trade_pct:+.2f}%")
    lines.append(f"  📈 میانگین سود:        {perf.avg_win_pct:+.2f}%")
    lines.append(f"  📉 میانگین زیان:       {perf.avg_loss_pct:+.2f}%")
    lines.append("")

    # Verdict
    if perf.total_return_pct > 20 and perf.profit_factor > 1.5:
        verdict = "🟢 عالی - استراتژی سودده است"
    elif perf.total_return_pct > 5 and perf.profit_factor > 1.2:
        verdict = "🟡 متوسط - نیاز به بهبود دارد"
    elif perf.total_return_pct > 0:
        verdict = "🟠 ضعیف - سود کم"
    else:
        verdict = "🔴 زیان‌ده - نیاز به بازنگری اساسی"
    lines.append(f"  {verdict}")
    lines.append("=" * 70)

    # Show top 5 trades
    if perf.trades:
        lines.append("")
        lines.append("  --- 5 ترید برتر (بیشترین سود) ---")
        sorted_trades = sorted(perf.trades, key=lambda t: t.pnl_pct, reverse=True)
        for t in sorted_trades[:5]:
            lines.append(f"  {t.symbol:<8} {t.entry_date[:10]} → {t.exit_date[:10]} "
                        f"({t.hold_days}d) | PnL: {t.pnl_pct:+.2f}% (${t.pnl_usd:+.2f}) | exit: {t.exit_reason}")
        lines.append("")
        lines.append("  --- 5 ترید بدتر (بیشترین زیان) ---")
        for t in sorted_trades[-5:]:
            lines.append(f"  {t.symbol:<8} {t.entry_date[:10]} → {t.exit_date[:10]} "
                        f"({t.hold_days}d) | PnL: {t.pnl_pct:+.2f}% (${t.pnl_usd:+.2f}) | exit: {t.exit_reason}")

    return "\n".join(lines)
