"""
Orchestrator
------------
Coordinates the full multi-agent workflow:

  CollectorAgent -> ExtractionAgent -> DedupAgent -> StagePredictorAgent
  -> InsightAgent -> (structured dataset + executive report)

This is the single entry point used by main.py and by the dashboard.
"""
import json
from typing import Dict, List

import config
from agents.collector_agent import CollectorAgent
from agents.extraction_agent import ExtractionAgent
from agents.dedup_agent import DedupAgent
from agents.stage_predictor_agent import StagePredictorAgent
from agents.insight_agent import InsightAgent


class Orchestrator:
    def __init__(self):
        with open(config.STARTUP_SEED_FILE, "r", encoding="utf-8") as f:
            self.startup_profiles = json.load(f)
        known_names = [p["name"] for p in self.startup_profiles]

        self.collector = CollectorAgent(known_startups=known_names)
        self.extractor = ExtractionAgent()
        self.deduper = DedupAgent()
        self.stage_predictor = StagePredictorAgent()
        self.insight_agent = InsightAgent()

    def run(self, fetch_live: bool = False, feed_urls=None, page_urls=None) -> Dict:
        # 1. Collect
        raw_items = self.collector.collect_all(fetch_live=fetch_live, feed_urls=feed_urls, page_urls=page_urls)

        # 2. Extract structured signals
        signals = self.extractor.process(raw_items)

        # 3. Deduplicate / consolidate
        consolidated_signals = self.deduper.process(signals)

        # 4. Predict stage + generate insights per startup
        startups_output: List[Dict] = []
        for profile in self.startup_profiles:
            name = profile["name"]
            startup_signals = [s for s in consolidated_signals if s["startup"] == name]
            startup_signals.sort(key=lambda s: s["date"])

            stage_info = self.stage_predictor.predict(profile, startup_signals)
            insights = self.insight_agent.generate(name, startup_signals, stage_info)

            startups_output.append({
                **profile,
                "signals": startup_signals,
                "signal_count": len(startup_signals),
                "stage": stage_info,
                "insights": insights,
            })

        result = {
            "startups": startups_output,
            "raw_article_count": len(raw_items),
            "signal_count_before_dedup": len(signals),
            "signal_count_after_dedup": len(consolidated_signals),
        }
        return result

    def save_outputs(self, result: Dict):
        import csv

        # Full structured dataset (JSON)
        with open(config.DATASET_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        # Flat CSV: one row per startup (profile + stage + insight scores)
        with open(config.DATASET_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "name", "sector", "headquarters", "founded_year", "employee_estimate",
                "predicted_stage", "stage_confidence", "total_funding_musd",
                "latest_funding_stage", "momentum_score", "risk_score", "recommendation",
                "signal_count",
            ])
            for s in result["startups"]:
                writer.writerow([
                    s["name"], s["sector"], s["headquarters"], s["founded_year"],
                    s["employee_estimate"], s["stage"]["predicted_stage"],
                    s["stage"]["confidence"], s["stage"]["total_funding_musd"],
                    s["stage"]["latest_funding_stage"], s["insights"]["momentum_score"],
                    s["insights"]["risk_score"], s["insights"]["recommendation"],
                    s["signal_count"],
                ])

        # Flat CSV: one row per individual signal (for the dashboard / analysts)
        with open(config.SIGNALS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["startup", "signal_type", "date", "title", "summary",
                              "sources", "source_count", "funding_amount_musd", "funding_stage"])
            for s in result["startups"]:
                for sig in s["signals"]:
                    writer.writerow([
                        s["name"], sig["signal_type"], sig["date"], sig["title"],
                        sig.get("summary", ""), "; ".join(sig.get("sources", [])),
                        sig.get("source_count", 1), sig.get("funding_amount_musd", ""),
                        sig.get("funding_stage", ""),
                    ])

        print(f"[Orchestrator] Saved dataset -> {config.DATASET_JSON}, "
              f"{config.DATASET_CSV}, {config.SIGNALS_CSV}")
