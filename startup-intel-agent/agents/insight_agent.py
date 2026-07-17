"""
InsightAgent
------------
Generates investment-facing insights per startup:
  - Momentum score (0-100): weighted count/recency of positive signals
  - Risk score (0-100): weighted count of negative signals
  - Recommendation label: Strong Buy Signal / Watch / Caution / Avoid
  - Human-readable opportunities, risks, and rationale

Rule-based by default (deterministic, explainable, no API key needed).
If ANTHROPIC_API_KEY is set, uses Claude to turn the structured signals into
richer narrative insights; falls back to rule-based text if the call fails.
"""
from datetime import datetime
from typing import Dict, List

import config

POSITIVE_WEIGHTS = {
    "funding": 35, "partnership": 20, "product_launch": 20, "hiring": 15,
}
NEGATIVE_WEIGHTS = {"layoffs": 35, "leadership_change": 15}


class InsightAgent:
    def __init__(self):
        self.use_llm = config.USE_LLM_INSIGHTS
        self._client = None
        if self.use_llm:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            except Exception as e:  # noqa: BLE001
                print(f"[InsightAgent] Anthropic client unavailable, falling back to rules: {e}")
                self.use_llm = False

    # -- scoring --------------------------------------------------------------
    def _score(self, signals: List[Dict]) -> Dict:
        momentum, risk = 0, 0
        for s in signals:
            momentum += POSITIVE_WEIGHTS.get(s["signal_type"], 0) * min(s.get("source_count", 1), 3) / 3
            risk += NEGATIVE_WEIGHTS.get(s["signal_type"], 0)
        return {
            "momentum_score": min(round(momentum), 100),
            "risk_score": min(round(risk), 100),
        }

    def _recommendation(self, momentum: int, risk: int, stage_info: Dict) -> str:
        if stage_info["predicted_stage"] == "Acquired / Exited":
            return "Exited — No Longer Investable"
        if stage_info["predicted_stage"] == "Distressed / Restructuring" or risk >= 40:
            return "Caution — Elevated Risk"
        if momentum >= 60 and risk < 20:
            return "Strong Buy Signal"
        if momentum >= 30:
            return "Watch — Emerging Momentum"
        return "Insufficient Signal"

    # -- rule-based narrative ---------------------------------------------------
    def _rule_based_narrative(self, name: str, signals: List[Dict], stage_info: Dict,
                               scores: Dict) -> Dict:
        opportunities, risks = [], []
        for s in signals:
            if s["signal_type"] == "funding":
                amt = s.get("funding_amount_musd", 0)
                opportunities.append(
                    f"Raised ${amt:.0f}M ({s.get('funding_stage', 'undisclosed stage')}) "
                    f"reported by {s.get('source_count', 1)} source(s) on {s['date']}."
                )
            elif s["signal_type"] == "partnership":
                opportunities.append(f"New partnership: {s['title']}")
            elif s["signal_type"] == "product_launch":
                opportunities.append(f"Product launch: {s['title']}")
            elif s["signal_type"] == "hiring":
                opportunities.append(f"Active hiring signal: {s['title']}")
            elif s["signal_type"] == "layoffs":
                risks.append(f"Layoffs reported: {s['title']}")
            elif s["signal_type"] == "leadership_change":
                risks.append(f"Leadership change: {s['title']}")
            elif s["signal_type"] == "acquisition":
                risks.append(f"Acquisition activity: {s['title']}") if "acquired" in s["title"].lower() \
                    else opportunities.append(f"Acquisition activity: {s['title']}")

        rationale = (
            f"{name} is assessed at the '{stage_info['predicted_stage']}' stage "
            f"(confidence {stage_info['confidence']:.0%}) with a momentum score of "
            f"{scores['momentum_score']}/100 and risk score of {scores['risk_score']}/100, "
            f"based on {len(signals)} consolidated signal(s)."
        )
        return {
            "opportunities": opportunities or ["No significant positive signals detected in this period."],
            "risks": risks or ["No significant risk signals detected in this period."],
            "rationale": rationale,
        }

    # -- optional LLM narrative -------------------------------------------------
    def _llm_narrative(self, name: str, signals: List[Dict], stage_info: Dict, scores: Dict) -> Dict:
        signal_summary = "\n".join(
            f"- [{s['signal_type']}] {s['title']} ({s['date']}, {s.get('source_count', 1)} sources)"
            for s in signals
        )
        prompt = f"""You are an investment analyst. Based on the following consolidated
signals for the startup "{name}" (predicted stage: {stage_info['predicted_stage']},
momentum score: {scores['momentum_score']}/100, risk score: {scores['risk_score']}/100),
write a JSON object with keys "opportunities" (list of short strings), "risks"
(list of short strings), and "rationale" (2-3 sentence paragraph). Respond with
ONLY the JSON object, no other text.

Signals:
{signal_summary}
"""
        try:
            response = self._client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            import json
            cleaned = text.strip().strip("`").replace("json\n", "", 1)
            return json.loads(cleaned)
        except Exception as e:  # noqa: BLE001
            print(f"[InsightAgent] LLM narrative failed for {name}, using rule-based fallback: {e}")
            return self._rule_based_narrative(name, signals, stage_info, scores)

    # -- public API ---------------------------------------------------------
    def generate(self, name: str, signals: List[Dict], stage_info: Dict) -> Dict:
        scores = self._score(signals)
        recommendation = self._recommendation(scores["momentum_score"], scores["risk_score"], stage_info)
        narrative = (self._llm_narrative(name, signals, stage_info, scores)
                     if self.use_llm else self._rule_based_narrative(name, signals, stage_info, scores))
        return {
            **scores,
            "recommendation": recommendation,
            "generated_at": datetime.utcnow().isoformat(),
            **narrative,
        }
