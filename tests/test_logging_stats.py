# -*- coding: utf-8 -*-
"""V1.3.3 - تست آمار API بدون KeyError برای skipped."""
import unittest
from src import logging_setup as ls


class TestApiStatsSkipped(unittest.TestCase):
    def test_skipped_status_no_keyerror(self):
        # پاکسازی نسبی
        ls._run_stats["api_stats"].clear()
        ls.record_api_call("binance", "skipped", "SHIB not listed")
        ls.record_api_call("binance", "rate_limited", "test")
        ls.record_api_call("binance", "success", "ok")
        summary = ls.get_run_summary()
        stats = summary["api_stats"]["binance"]
        self.assertGreaterEqual(stats.get("skipped", 0), 1)
        self.assertGreaterEqual(stats.get("success", 0), 1)
        self.assertGreaterEqual(stats.get("rate_limited", 0), 1)


if __name__ == "__main__":
    unittest.main()
