"""
StagePredictorAgent
--------------------
Predicts a startup's growth stage from consolidated signals using a
transparent, explainable rule-based model (no black-box ML needed for
this to be genuinely useful — and it's easy to swap in a trained
classifier later using the same feature set).

Stages (ascending): Idea/Pre-seed -> Seed -> Early Growth (Series A/B)
                     -> Scaling (Series C+) -> Late Stage / Pre-Exit
                     -> Acquired / Exited -> Distressed
"""
from typing import Dict, List

FUNDING_STAGE_TO_SCORE = {
    "pre-seed": 1, "seed": 2, "series a": 3, "series b": 4,
    "series c": 5, "series d": 6, "series e": 7,
}


class StagePredictorAgent:
    def predict(self, startup_profile: Dict, signals: List[Dict]) -> Dict:
        funding_signals = [s for s in signals if s["signal_type"] == "funding"]
        acquisition_signals = [s for s in signals if s["signal_type"] == "acquisition"
                                and startup_profile["name"].lower() in
                                (s.get("title", "") + s.get("summary", "")).lower()]
        layoff_signals = [s for s in signals if s["signal_type"] == "layoffs"]
        leadership_signals = [s for s in signals if s["signal_type"] == "leadership_change"]

        # Was this startup itself acquired (the TARGET), as opposed to being the
        # ACQUIRER of someone else? Naively matching "acquired" + startup name
        # mislabels acquirers (e.g. "PayFlux acquires ClearRail" also contains
        # "PayFlux" + "acquired"), so we require a target-side pattern
        # specifically anchored to this startup's name.
        import re as _re
        name_pattern = _re.escape(startup_profile["name"])
        target_patterns = [
            rf"{name_pattern}\W+(?:has been |was )?acquired\s+by",
            rf"acqui(?:res?|sition of)\s+{name_pattern}",  # "X acquires PayFlux" / "acquisition of PayFlux"
        ]
        was_acquired = any(
            any(_re.search(p, (s.get("title", "") + " " + s.get("summary", "")), _re.IGNORECASE)
                for p in target_patterns)
            for s in acquisition_signals
        )

        best_stage_score = 0
        latest_funding_stage = ""
        total_funding = 0.0
        for s in funding_signals:
            total_funding += s.get("funding_amount_musd", 0) or 0
            stage_key = (s.get("funding_stage") or "").replace("-", "-").strip()
            score = FUNDING_STAGE_TO_SCORE.get(stage_key, 0)
            if score > best_stage_score:
                best_stage_score = score
                latest_funding_stage = stage_key

        employee_estimate = startup_profile.get("employee_estimate", 0)

        # --- decision logic -------------------------------------------------
        if was_acquired:
            predicted_stage = "Acquired / Exited"
            confidence = 0.95
        elif len(layoff_signals) >= 1 and len(leadership_signals) >= 1:
            predicted_stage = "Distressed / Restructuring"
            confidence = 0.75
        elif best_stage_score >= 5 or employee_estimate >= 300:
            predicted_stage = "Late Stage / Scaling"
            confidence = 0.8
        elif best_stage_score in (3, 4) or 100 <= employee_estimate < 300:
            predicted_stage = "Early Growth (Series A/B)"
            confidence = 0.8
        elif best_stage_score in (1, 2) or 5 <= employee_estimate < 100:
            predicted_stage = "Seed Stage"
            confidence = 0.75
        elif employee_estimate < 5:
            predicted_stage = "Idea / Pre-Seed"
            confidence = 0.7
        else:
            predicted_stage = "Seed Stage"
            confidence = 0.5

        return {
            "predicted_stage": predicted_stage,
            "confidence": confidence,
            "total_funding_musd": round(total_funding, 1),
            "latest_funding_stage": latest_funding_stage or "unknown",
            "funding_events": len(funding_signals),
            "layoff_events": len(layoff_signals),
            "leadership_change_events": len(leadership_signals),
        }
