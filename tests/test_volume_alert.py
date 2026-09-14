"""
test_volume_alert.py
تست‌های واحد برای هشدار حجم غیرعادی.

V1.2.0
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.volume_alert import detect_volume_anomaly, format_volume_alerts


class TestVolumeAnomaly(unittest.TestCase):
    """تست‌های هشدار حجم."""

    def test_anomaly_detected(self):
        """حجم غیرعادی باید تشخیص داده شود."""
        # حجم نرمال 30 روز
        volumes = [1_000_000] * 30
        # امروز حجم 5 برابر
        volumes.append(5_000_000)
        result = detect_volume_anomaly(
            volumes=volumes,
            coin_id="test",
            symbol="TEST",
            name="Test Coin",
            lookback=30,
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.is_anomaly)
        self.assertGreaterEqual(result.volume_ratio, 3.0)
        self.assertIn(result.severity, ("high", "extreme"))

    def test_no_anomaly(self):
        """حجم نرمال نباید هشدار بدهد."""
        volumes = [1_000_000] * 31
        result = detect_volume_anomaly(
            volumes=volumes,
            coin_id="test",
            symbol="TEST",
            name="Test Coin",
            lookback=30,
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.is_anomaly)

    def test_insufficient_data(self):
        """داده کم باید None."""
        volumes = [1_000_000] * 5
        result = detect_volume_anomaly(
            volumes=volumes,
            coin_id="test",
            symbol="TEST",
            name="Test",
            lookback=30,
        )
        self.assertIsNone(result)

    def test_severity_levels(self):
        """سطوح مختلف شدت باید درست تشخیص داده شوند."""
        # حجم 10 برابر = extreme
        volumes = [1_000_000] * 30 + [10_000_000]
        result = detect_volume_anomaly(volumes, "t", "T", "Test", 30)
        self.assertEqual(result.severity, "extreme")

        # حجم 5 برابر = high
        volumes = [1_000_000] * 30 + [5_000_000]
        result = detect_volume_anomaly(volumes, "t", "T", "Test", 30)
        self.assertEqual(result.severity, "high")


class TestFormatVolumeAlerts(unittest.TestCase):
    """تست قالب‌بندی هشدارها."""

    def test_empty_alerts(self):
        """بدون هشدار باید پیام مناسب بدهد."""
        result = format_volume_alerts([])
        self.assertIn("پیدا نشد", result)

    def test_with_alerts(self):
        """با هشدار باید قالب‌بندی شود."""
        volumes = [1_000_000] * 30 + [5_000_000]
        alert = detect_volume_anomaly(volumes, "test", "TEST", "Test Coin", 30)
        result = format_volume_alerts([alert])
        self.assertIn("TEST", result)
        self.assertIn("هشدار", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
