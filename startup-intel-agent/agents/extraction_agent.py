"""
ExtractionAgent
---------------
Turns raw articles into structured SIGNALS by detecting event type
(funding / product_launch / hiring / partnership / acquisition /
leadership_change / layoffs) using keyword + regex rules, and pulling out
extra structured fields where possible (funding amount, funding stage).
"""
import re
from typing import Dict, List

import config


class ExtractionAgent:
    def __init__(self):
        self.compiled_rules = {
            signal_type: [re.compile(pat, re.IGNORECASE) for pat in patterns]
            for signal_type, patterns in config.SIGNAL_KEYWORDS.items()
        }

    def detect_signal_types(self, text: str) -> List[str]:
        matched = []
        for signal_type, patterns in self.compiled_rules.items():
            if any(p.search(text) for p in patterns):
                matched.append(signal_type)
        return matched or ["general_update"]

    @staticmethod
    def extract_funding_amount(text: str) -> float:
        """Returns amount in USD millions, or 0 if not found."""
        match = re.search(r"\$\s?([\d,.]+)\s?(million|billion|m|b)\b", text, re.IGNORECASE)
        if not match:
            return 0.0
        value = float(match.group(1).replace(",", ""))
        unit = match.group(2).lower()
        return value * 1000 if unit.startswith("b") else value

    @staticmethod
    def extract_funding_stage(text: str) -> str:
        text_lower = text.lower()
        for stage in ["series e", "series d", "series c", "series b", "series a",
                      "seed round", "seed", "pre-seed"]:
            if stage in text_lower:
                return stage.replace(" round", "")
        return ""

    def process(self, raw_items: List[Dict]) -> List[Dict]:
        """Converts raw articles into one-or-more structured signal records."""
        signals = []
        for item in raw_items:
            combined_text = f"{item.get('title', '')} {item.get('text', '')}"
            signal_types = self.detect_signal_types(combined_text)
            for signal_type in signal_types:
                signal = {
                    "startup": item.get("startup", "Unknown"),
                    "signal_type": signal_type,
                    "date": item.get("date"),
                    "source": item.get("source"),
                    "source_type": item.get("source_type"),
                    "title": item.get("title"),
                    "summary": item.get("text", "")[:400],
                    "url": item.get("url"),
                }
                if signal_type == "funding":
                    signal["funding_amount_musd"] = self.extract_funding_amount(combined_text)
                    signal["funding_stage"] = self.extract_funding_stage(combined_text)
                signals.append(signal)
        print(f"[ExtractionAgent] Extracted {len(signals)} structured signals from "
              f"{len(raw_items)} raw articles.")
        return signals
