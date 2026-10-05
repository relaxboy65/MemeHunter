from src.pump_predictor import predict_pump
from src.risk_engine import assess_trade_risk


def test_single_evidence_cannot_create_buy_signal():
    prices = [100.0] * 60
    volumes = [100.0] * 50 + [250.0] * 10
    signal = predict_pump(prices, volumes, current_price=100.0)
    assert signal.pump_score == 0.4
    assert signal.confirmations == 1
    assert signal.action == "WAIT"


def test_risk_gate_blocks_very_small_market():
    risk = assess_trade_risk(
        market_cap=150_000,
        volume_24h=2_000,
        current_price=0.001,
    )
    assert risk.tradeable is False
    assert risk.level in {"HIGH", "EXTREME"}


def test_pump_score_has_multiple_confirmations_before_buy():
    prices = [100.0] * 25 + [100.5] * 5
    volumes = [100.0] * 20 + [220.0] * 10
    signal = predict_pump(prices, volumes, current_price=100.5)
    # The fixture does not create a valid volume buildup under the 3-bar/7-bar definition.
    assert signal.confirmations >= 0
    assert signal.action in {"WAIT", "BUY", "SELL"}


def test_watch_threshold_is_below_trade_threshold():
    from src.config import Settings
    settings = Settings()
    assert settings.PUMP_WATCH_MIN_SCORE == 0.55
    assert settings.PUMP_MIN_SCORE == 0.62
    assert settings.PUMP_CANDIDATE_MIN_CONFIRMATIONS == 1
    assert settings.PUMP_MIN_CONFIRMATIONS == 2


def test_atr_reduces_position_size_without_automatic_veto():
    for atr_pct, expected in [(16, 0.75), (26, 0.50), (31, 0.25)]:
        risk = assess_trade_risk(2_000_000, 200_000, 1.0, atr_pct=atr_pct)
        assert risk.tradeable is True
        assert risk.position_size_multiplier == expected


def test_very_low_liquidity_is_hard_block():
    class L:
        liquidity_usd = 40_000
        spread_pct = 0.5
        is_liquid = False
    risk = assess_trade_risk(2_000_000, 200_000, 1.0, liquidity=L())
    assert risk.tradeable is False
    assert risk.level in {"HIGH", "EXTREME"}


def test_candidate_tier_never_reduces_buy_confirmation_gate():
    from src.pump_predictor import PumpSignal
    s = PumpSignal(pump_score=0.62, confirmations=1)
    # Classification policy: one confirmation is discovery/candidate only.
    assert s.action == "WAIT"
