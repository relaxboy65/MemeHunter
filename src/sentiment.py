"""
sentiment.py
تحلیل احساسات بازار - V2.0

منابع رایگان:
- Fear & Greed Index (alternative.me)
- Google Trends (pytrends)

نکته: sentiment معمولاً lagging است، پس به‌عنوان contrary indicator استفاده می‌شود:
- Extreme Greed → سیگنال فروش
- Extreme Fear → سیگنال خرید
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from .config import settings
from .rate_limiter import get_rate_limiter


logger = logging.getLogger(settings.PROJECT_SLUG)


@dataclass
class SentimentResult:
    """نتیجه تحلیل احساسات."""
    fear_greed_value: int = 50          # 0..100
    fear_greed_classification: str = "Neutral"
    # سیگنال contrary
    contrarian_signal: float = 0.5      # 0..1 (high = bullish)
    notes: List[str] = field(default_factory=list)
    source: str = "alternative.me"

    def to_dict(self) -> dict:
        return {
            "fear_greed_value": self.fear_greed_value,
            "fear_greed_classification": self.fear_greed_classification,
            "contrarian_signal": round(self.contrarian_signal, 3),
            "notes": self.notes,
        }


def fetch_fear_greed() -> Optional[SentimentResult]:
    """
    دریافت Fear & Greed Index از alternative.me.
    کاملاً رایگان، بدون نیاز به کلید.
    """
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("data"):
            return None

        item = data["data"][0]
        value = int(item.get("value", 50))
        classification = item.get("value_classification", "Neutral")

        result = SentimentResult(
            fear_greed_value=value,
            fear_greed_classification=classification,
        )

        # Contrarian signal
        if value < 20:  # Extreme Fear
            result.contrarian_signal = 0.85
            result.notes.append(f"Extreme Fear ({value}) - contrarian: سیگنال خرید")
        elif value < 40:
            result.contrarian_signal = 0.65
            result.notes.append(f"Fear ({value}) - contrarian: تمایل به خرید")
        elif value > 80:  # Extreme Greed
            result.contrarian_signal = 0.15
            result.notes.append(f"Extreme Greed ({value}) - contrarian: سیگنال فروش")
        elif value > 60:
            result.contrarian_signal = 0.35
            result.notes.append(f"Greed ({value}) - contrarian: تمایل به فروش")
        else:
            result.notes.append(f"Neutral ({value}) - بدون سیگنال")

        return result

    except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
        logger.debug("Fear/Greed fetch failed: %s", exc)
        return None


def get_sentiment() -> Optional[SentimentResult]:
    """دریافت تحلیل احساسات فعلی."""
    return fetch_fear_greed()
