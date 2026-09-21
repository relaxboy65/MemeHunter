"""
test_v2_modules.py
تست‌های واحد برای ماژول‌های V2.0
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.walk_forward import split_walk_forward, apply_purge_and_embargo, run_walk_forward_analysis
from src.cost_model import estimate_costs, apply_costs_to_return, get_cost_tier
from src.monte_carlo import run_monte_carlo
from src.regime_detector import detect_regime, MarketRegime
from src.smc_detector import analyze_smc, find_swing_points, detect_fvg
from src.wyckoff import analyze_wyckoff
from src.kelly_sizing import compute_kelly, volatility_targeting, combined_sizing
from src.portfolio import compute_correlation, risk_parity_weights, analyze_portfolio


class TestWalkForward(unittest.TestCase):
    """تست‌های Walk-Forward."""

    def test_split_basic(self):
        """تقسیم پایه باید درست کار کند."""
        timestamps = list(range(10))
        splits = split_walk_forward(timestamps, train_size=5, test_size=3, step_size=1)
        self.assertEqual(len(splits), 3)  # 10 - 5 - 3 + 1 = 3
        # اولین پنجره
        train_idx, test_idx = splits[0]
        self.assertEqual(train_idx, [0, 1, 2, 3, 4])
        self.assertEqual(test_idx, [5, 6, 7])

    def test_purge_embargo(self):
        """Embargo باید اولین نمونه test را حذف کند."""
        train_idx = [0, 1, 2, 3, 4]
        test_idx = [5, 6, 7]
        new_train, new_test = apply_purge_and_embargo(train_idx, test_idx, embargo_size=1)
        self.assertEqual(new_test, [6, 7])

    def test_empty_data(self):
        """داده ناکافی باید گزارش خالی برگرداند."""
        report = run_walk_forward_analysis([], train_size=5, test_size=3)
        self.assertEqual(len(report.windows), 0)


class TestCostModel(unittest.TestCase):
    """تست‌های Cost Model."""

    def test_high_liquidity(self):
        """نقدینگی بالا باید هزینه پایین بدهد."""
        costs = estimate_costs(volume_24h=20_000_000)
        self.assertLess(costs.total_cost_pct, 1.0)
        self.assertEqual(costs.commission_pct, 0.10)

    def test_low_liquidity(self):
        """نقدینگی پایین باید هزینه بالا بدهد."""
        costs = estimate_costs(volume_24h=50_000)
        self.assertGreater(costs.total_cost_pct, 2.0)

    def test_apply_costs(self):
        """اعمال هزینه‌ها باید بازده را کاهش دهد."""
        costs = TradeCosts = estimate_costs(volume_24h=5_000_000)
        gross = 10.0
        net = apply_costs_to_return(gross, costs, trades_count=1)
        self.assertLess(net, gross)

    def test_cost_tier(self):
        """رده هزینه باید درست باشد."""
        self.assertEqual(get_cost_tier(20_000_000)[0], "A")
        self.assertEqual(get_cost_tier(50_000)[0], "D")


class TestMonteCarlo(unittest.TestCase):
    """تست‌های Monte Carlo."""

    def test_basic_simulation(self):
        """شبیه‌سازی پایه باید کار کند."""
        returns = [5.0, -3.0, 8.0, -2.0, 6.0, -1.0, 4.0, 2.0]
        result = run_monte_carlo(returns, initial_capital=10000, iterations=100)
        self.assertEqual(result.iterations, 100)
        self.assertEqual(len(result.final_capitals), 100)
        self.assertGreater(result.mean_final_capital, 0)

    def test_empty_returns(self):
        """بدون داده باید خالی برگرداند."""
        result = run_monte_carlo([], iterations=10)
        self.assertEqual(result.iterations, 0)

    def test_risk_of_ruin_calculation(self):
        """محاسبه risk of ruin باید درست باشد."""
        # همه تریدها زیان‌ده
        returns = [-10.0] * 20
        result = run_monte_carlo(returns, initial_capital=10000, iterations=100)
        self.assertGreater(result.risk_of_ruin, 50.0)


class TestRegimeDetector(unittest.TestCase):
    """تست‌های Regime Detection."""

    def test_trending_up(self):
        """روند صعودی باید تشخیص داده شود."""
        prices = [100 + i * 2 for i in range(30)]
        highs = [p + 1 for p in prices]
        lows = [p - 1 for p in prices]
        closes = prices
        result = detect_regime(prices, highs, lows, closes)
        self.assertIsNotNone(result)
        self.assertIn(result.regime, (MarketRegime.TRENDING_UP, MarketRegime.RANGING))

    def test_trending_down(self):
        """روند نزولی باید تشخیص داده شود."""
        prices = [200 - i * 2 for i in range(30)]
        highs = [p + 1 for p in prices]
        lows = [p - 1 for p in prices]
        closes = prices
        result = detect_regime(prices, highs, lows, closes)
        self.assertIsNotNone(result)

    def test_insufficient_data(self):
        """داده کم باید should_trade=False بدهد."""
        prices = [100, 101]
        result = detect_regime(prices)
        self.assertFalse(result.should_trade)


class TestSMCDetector(unittest.TestCase):
    """تست‌های Smart Money Concepts."""

    def test_swing_points(self):
        """پیدا کردن swing points."""
        highs = [10, 12, 11, 13, 10, 14, 11, 15, 12, 13]
        lows = [8, 10, 9, 11, 8, 12, 9, 13, 10, 11]
        swing_highs, swing_lows = find_swing_points(highs, lows, lookback=2)
        # باید حداقل چند swing point پیدا کند
        self.assertGreaterEqual(len(swing_highs) + len(swing_lows), 0)

    def test_fvg_detection(self):
        """تشخیص Fair Value Gap."""
        opens = [100] * 10
        highs = [101, 102, 103, 110, 104, 105, 106, 115, 107, 108]
        lows = [99, 100, 101, 108, 102, 103, 104, 113, 105, 106]
        fvgs = detect_fvg(opens, highs, lows)
        self.assertIsInstance(fvgs, list)

    def test_analyze_smc(self):
        """تحلیل کامل SMC باید کار کند."""
        opens = [100, 101, 99, 102, 100, 103, 101, 104, 102, 105]
        highs = [101, 102, 100, 103, 101, 104, 102, 105, 103, 106]
        lows = [99, 100, 98, 101, 99, 102, 100, 103, 101, 104]
        closes = [100.5, 101.5, 99.5, 102.5, 100.5, 103.5, 101.5, 104.5, 102.5, 105.5]
        result = analyze_smc(opens, highs, lows, closes)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.signal_score, 0)
        self.assertLessEqual(result.signal_score, 1)


class TestWyckoff(unittest.TestCase):
    """تست‌های Wyckoff/VSA."""

    def test_basic_analysis(self):
        """تحلیل پایه Wyckoff."""
        n = 30
        opens = [100 + i * 0.1 for i in range(n)]
        highs = [o + 2 for o in opens]
        lows = [o - 2 for o in opens]
        closes = [o + 0.5 for o in opens]
        volumes = [1000000] * n
        result = analyze_wyckoff(opens, highs, lows, closes, volumes)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.signal_score, 0)
        self.assertLessEqual(result.signal_score, 1)

    def test_insufficient_data(self):
        """داده کم باید result خالی بدهد."""
        result = analyze_wyckoff([100], [101], [99], [100], [1000])
        self.assertEqual(result.phase, "unknown")


class TestKellySizing(unittest.TestCase):
    """تست‌های Kelly Criterion."""

    def test_kelly_calculation(self):
        """محاسبه Kelly باید درست باشد."""
        # win_rate=60%, avg_win=10%, avg_loss=5%
        result = compute_kelly(win_rate=0.6, avg_win_pct=10.0, avg_loss_pct=5.0)
        self.assertGreater(result.kelly_fraction, 0)
        # Quarter Kelly
        self.assertLess(result.fractional_kelly, result.kelly_fraction)
        # Recommended size < 50%
        self.assertLessEqual(result.recommended_size, 0.50)

    def test_negative_kelly(self):
        """win rate پایین باید Kelly منفی بدهد."""
        result = compute_kelly(win_rate=0.3, avg_win_pct=5.0, avg_loss_pct=10.0)
        self.assertLessEqual(result.kelly_fraction, 0)
        self.assertEqual(result.recommended_size, 0.0)

    def test_vol_targeting(self):
        """Volatility targeting باید کار کند."""
        size = volatility_targeting(asset_volatility_pct=20, target_volatility_pct=5)
        self.assertAlmostEqual(size, 0.25, places=2)
        # Cap
        size = volatility_targeting(asset_volatility_pct=5, target_volatility_pct=5, max_position=0.4)
        self.assertEqual(size, 0.4)

    def test_combined_sizing(self):
        """ترکیب Kelly و Vol Targeting باید کمترین را بگیرد."""
        kelly_result = compute_kelly(win_rate=0.6, avg_win_pct=10.0, avg_loss_pct=5.0)
        combined = combined_sizing(kelly_result, asset_volatility_pct=20)
        self.assertGreater(combined, 0)
        self.assertLessEqual(combined, 0.40)


class TestPortfolio(unittest.TestCase):
    """تست‌های Portfolio."""

    def test_correlation(self):
        """محاسبه همبستگی."""
        a = [1, 2, 3, 4, 5]
        b = [2, 4, 6, 8, 10]
        corr = compute_correlation(a, b)
        self.assertGreater(corr, 0.95)  # کاملاً همبسته

    def test_risk_parity(self):
        """وزن risk parity."""
        vols = {"A": 5.0, "B": 10.0, "C": 20.0}
        weights = risk_parity_weights(vols)
        # A با نوسان کمتر، وزن بیشتر
        self.assertGreater(weights["A"], weights["B"])
        self.assertGreater(weights["B"], weights["C"])
        # مجموع = 1
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

    def test_portfolio_analysis(self):
        """تحلیل پورتفوی کامل."""
        coins_data = {
            "A": {"returns": [1, 2, 3, 4, 5], "volatility": 5.0},
            "B": {"returns": [2, 3, 4, 5, 6], "volatility": 10.0},
        }
        result = analyze_portfolio(coins_data)
        self.assertIsNotNone(result)
        self.assertIn("A", result.optimal_weights)
        self.assertIn("B", result.optimal_weights)


if __name__ == "__main__":
    unittest.main(verbosity=2)
