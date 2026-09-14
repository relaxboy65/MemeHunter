"""
html_reporter.py
تولید گزارش HTML ساده داشبورد - V1.2.0.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .analyzer import AnalysisResult, Signal
from .config import settings


def format_html(results: List[AnalysisResult],
                backtest_report: Optional[str] = None,
                paper_trading_stats: Optional[dict] = None) -> str:
    """
    ساخت گزارش HTML کامل - V1.3.1.

    V1.3.1: اضافه شدن بخش Paper Trading و روند عملکرد.
    """
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

    buy_count = sum(1 for r in results if r.signal == Signal.BUY)
    sell_count = sum(1 for r in results if r.signal == Signal.SELL)
    hold_count = sum(1 for r in results if r.signal == Signal.HOLD)
    real_count = sum(1 for r in results if "واقعی" in (r.data_sources or ""))
    proxy_count = sum(1 for r in results if "پروکسی" in (r.data_sources or ""))

    # ساخت کارت‌های کوین
    cards_html = ""
    for r in sorted_results:
        signal_class = r.signal.value
        cards_html += _build_card_html(r, signal_class)

    # خلاصه بک‌تست
    backtest_html = ""
    if backtest_report:
        safe = backtest_report.replace("<", "&lt;").replace(">", "&gt;")
        backtest_html = f"""
        <section class="backtest">
            <h2>📊 عملکرد سیگنال‌های گذشته</h2>
            <pre>{safe}</pre>
        </section>
        """

    # V1.3.1 - بخش Paper Trading
    paper_html = ""
    if paper_trading_stats and paper_trading_stats.get("total_positions", 0) > 0:
        wr = paper_trading_stats.get('win_rate', 0)
        pnl = paper_trading_stats.get('total_pnl_usd', 0)
        wr_color = "#00ff88" if wr >= 60 else ("#ff4757" if wr < 40 else "#ffa502")
        pnl_color = "#00ff88" if pnl >= 0 else "#ff4757"
        paper_html = f"""
        <section class="paper-trading">
            <h2>💹 Paper Trading</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="value">{paper_trading_stats.get('open_positions', 0)}</div>
                    <div class="label">پوزیشن باز</div>
                </div>
                <div class="stat-card">
                    <div class="value">{paper_trading_stats.get('closed_positions', 0)}</div>
                    <div class="label">پوزیشن بسته</div>
                </div>
                <div class="stat-card">
                    <div class="value" style="color: {wr_color}">{wr:.1f}%</div>
                    <div class="label">نرخ موفقیت</div>
                </div>
                <div class="stat-card">
                    <div class="value" style="color: {pnl_color}">${pnl:+.2f}</div>
                    <div class="label">کل PnL</div>
                </div>
            </div>
            <div class="best-worst">
                <div>بهترین: {paper_trading_stats.get('best_trade_pct', 0):+.2f}%</div>
                <div>بدترین: {paper_trading_stats.get('worst_trade_pct', 0):+.2f}%</div>
            </div>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MemeHunter V{settings.PROJECT_VERSION} - گزارش میم‌کوین</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 30px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        header h1 {{
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        header .version {{ color: #888; font-size: 1.1em; }}
        header .timestamp {{ color: #aaa; margin-top: 10px; }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.07);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .stat-card .value {{ font-size: 2em; font-weight: bold; }}
        .stat-card .label {{ color: #888; margin-top: 5px; }}
        .stat-buy .value {{ color: #00ff88; }}
        .stat-sell .value {{ color: #ff4757; }}
        .stat-hold .value {{ color: #ffa502; }}
        .stat-total .value {{ color: #00d4ff; }}
        .stat-real .value {{ color: #00ff88; }}
        .stat-proxy .value {{ color: #a55eea; }}

        .data-sources {{
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .data-sources .real {{ color: #00ff88; font-weight: bold; }}
        .data-sources .proxy {{ color: #a55eea; font-weight: bold; }}

        .coins-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .coin-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #888;
            transition: transform 0.2s;
        }}
        .coin-card:hover {{ transform: translateY(-3px); }}
        .coin-card.خرید {{ border-left-color: #00ff88; }}
        .coin-card.فروش {{ border-left-color: #ff4757; }}
        .coin-card.نگه‌داری {{ border-left-color: #ffa502; }}
        .coin-card .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .coin-card .name {{ font-size: 1.3em; font-weight: bold; }}
        .coin-card .symbol {{ color: #888; }}
        .coin-card .signal-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .signal-badge.خرید {{ background: rgba(0, 255, 136, 0.2); color: #00ff88; }}
        .signal-badge.فروش {{ background: rgba(255, 71, 87, 0.2); color: #ff4757; }}
        .signal-badge.نگه‌داری {{ background: rgba(255, 165, 2, 0.2); color: #ffa502; }}
        .coin-card .price {{ font-size: 1.5em; margin: 10px 0; }}
        .coin-card .changes {{ color: #aaa; margin-bottom: 15px; }}
        .coin-card .changes .up {{ color: #00ff88; }}
        .coin-card .changes .down {{ color: #ff4757; }}
        .coin-card .score-bar {{
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            margin: 15px 0;
            overflow: hidden;
        }}
        .coin-card .score-bar .fill {{
            height: 100%;
            background: linear-gradient(90deg, #ff4757, #ffa502, #00ff88);
        }}
        .coin-card .data-source-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin: 5px 2px;
        }}
        .data-source-tag.real {{ background: rgba(0, 255, 136, 0.2); color: #00ff88; }}
        .data-source-tag.proxy {{ background: rgba(165, 94, 234, 0.2); color: #a55eea; }}
        .coin-card .reasons {{ margin-top: 15px; }}
        .coin-card .reasons li {{
            list-style: none;
            padding: 3px 0;
            color: #ccc;
            font-size: 0.9em;
        }}
        .coin-card .reasons li::before {{ content: "• "; color: #00d4ff; }}

        .backtest, .paper-trading {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-top: 30px;
        }}
        .backtest h2, .paper-trading h2 {{ margin-bottom: 15px; color: #00d4ff; }}
        .backtest pre {{
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: monospace;
            color: #ddd;
            white-space: pre-wrap;
        }}
        .paper-trading .best-worst {{
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }}

        footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #888;
            font-size: 0.9em;
        }}
        footer .warning {{
            color: #ffa502;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>MemeHunter</h1>
            <div class="version">نسخه {settings.PROJECT_VERSION} - ربات پیداکننده میم‌کوین</div>
            <div class="timestamp">تاریخ گزارش: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </header>

        <div class="stats">
            <div class="stat-card stat-buy">
                <div class="value">{buy_count}</div>
                <div class="label">🟢 خرید</div>
            </div>
            <div class="stat-card stat-sell">
                <div class="value">{sell_count}</div>
                <div class="label">🔴 فروش</div>
            </div>
            <div class="stat-card stat-hold">
                <div class="value">{hold_count}</div>
                <div class="label">🟡 نگه‌داری</div>
            </div>
            <div class="stat-card stat-total">
                <div class="value">{len(results)}</div>
                <div class="label">📊 کل کوین‌ها</div>
            </div>
            <div class="stat-card stat-real">
                <div class="value">{real_count}</div>
                <div class="label">✅ داده واقعی</div>
            </div>
            <div class="stat-card stat-proxy">
                <div class="value">{proxy_count}</div>
                <div class="label">🔮 فقط پروکسی</div>
            </div>
        </div>

        <div class="data-sources">
            <span class="real">✅ {real_count} کوین با داده واقعی</span>
            <span style="color: #888;"> | </span>
            <span class="proxy">🔮 {proxy_count} کوین فقط پروکسی</span>
        </div>

        <h2 style="margin-bottom: 20px; color: #00d4ff;">سیگنال‌ها</h2>
        <div class="coins-grid">
            {cards_html}
        </div>

        {paper_html}

        {backtest_html}

        <footer>
            <div>این گزارش توسط MemeHunter {settings.PROJECT_VERSION} تولید شده است.</div>
            <div class="warning">⚠ هشدار: این سیگنال‌ها صرفاً آموزشی هستند و توصیه مالی نیستند.</div>
            <div style="margin-top: 10px; color: #666;">DYOR - Do Your Own Research</div>
        </footer>
    </div>
</body>
</html>
"""
    return html


def _build_card_html(r: AnalysisResult, signal_class: str) -> str:
    """ساخت HTML یک کارت کوین - V1.3.1 با برچسب منبع داده."""
    # رنگ‌بندی تغییرات
    change_24_class = "up" if r.change_24h_pct >= 0 else "down"
    change_7d_class = "up" if r.change_7d_pct >= 0 else "down"

    # قیمت
    if r.current_price < 1:
        price_str = f"${r.current_price:.6f}"
    else:
        price_str = f"${r.current_price:.2f}"

    # V1.3.1 - برچسب منبع داده
    data_source_tags = ""
    adv = getattr(r, "advanced", {}) or {}
    if adv.get("liquidity_is_real"):
        data_source_tags += '<span class="data-source-tag real">Liquidity واقعی</span>'
    elif adv.get("liquidity_score") is not None:
        data_source_tags += '<span class="data-source-tag proxy">Liquidity پروکسی</span>'
    if adv.get("orderflow_is_real"):
        data_source_tags += '<span class="data-source-tag real">OrderFlow واقعی</span>'
    elif adv.get("buy_pressure") is not None:
        data_source_tags += '<span class="data-source-tag proxy">OrderFlow پروکسی</span>'

    # لیست دلایل
    reasons_html = ""
    if r.reasons:
        reasons_html = "<ul class='reasons'>"
        for reason in r.reasons[:5]:
            safe_reason = reason.replace("<", "&lt;").replace(">", "&gt;")
            reasons_html += f"<li>{safe_reason}</li>"
        reasons_html += "</ul>"

    # نوار امتیاز
    score_percent = int(r.score * 100)

    # V1.3.1 - خلاصه منابع داده
    sources_html = ""
    if r.data_sources:
        sources_html = f'<div class="data-sources"><small>{r.data_sources}</small></div>'

    return f"""
            <div class="coin-card {signal_class}">
                <div class="header">
                    <div>
                        <div class="name">{r.name}</div>
                        <div class="symbol">{r.symbol}</div>
                    </div>
                    <div class="signal-badge {signal_class}">{signal_class}</div>
                </div>
                <div class="price">{price_str}</div>
                <div class="changes">
                    24h: <span class="{change_24_class}">{r.change_24h_pct:+.2f}%</span> |
                    7d: <span class="{change_7d_class}">{r.change_7d_pct:+.2f}%</span>
                </div>
                <div class="score-bar"><div class="fill" style="width: {score_percent}%"></div></div>
                <div style="color: #888;">امتیاز: {r.score:.3f} | اطمینان: {r.confidence*100:.1f}%</div>
                <div style="margin: 8px 0;">{data_source_tags}</div>
                {sources_html}
                {reasons_html}
            </div>
    """


def save_html_report(html_content: str) -> str:
    """ذخیره گزارش HTML در پوشه reports/."""
    reports_dir = Path(settings.OUTPUT_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memehunter_report_{timestamp}.html"
    path = reports_dir / filename
    path.write_text(html_content, encoding="utf-8")
    return str(path)
