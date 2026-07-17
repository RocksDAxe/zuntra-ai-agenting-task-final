"""
Basic tests for the AI Startup Intelligence Agent pipeline.
Run with:  python -m pytest tests/ -v   (or simply: python tests/test_pipeline.py)
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.extraction_agent import ExtractionAgent
from agents.dedup_agent import DedupAgent
from agents.stage_predictor_agent import StagePredictorAgent
from agents.orchestrator import Orchestrator


def test_extraction_detects_funding():
    agent = ExtractionAgent()
    text = "Acme Corp raises $10 million Series A led by ExampleVC"
    types = agent.detect_signal_types(text)
    assert "funding" in types


def test_extraction_amount_parsing():
    agent = ExtractionAgent()
    assert agent.extract_funding_amount("raised $10 million") == 10.0
    assert agent.extract_funding_amount("raised $1.2 billion") == 1200.0
    assert agent.extract_funding_amount("no funding mentioned") == 0.0


def test_dedup_merges_similar_articles():
    signals = [
        {"startup": "Acme", "signal_type": "funding", "date": "2026-01-01",
         "title": "Acme raises $10M Series A", "summary": "Acme raised ten million", "sources": []},
        {"startup": "Acme", "signal_type": "funding", "date": "2026-01-02",
         "title": "Acme closes $10M Series A round", "summary": "Acme raised ten million dollars",
         "sources": []},
    ]
    for s in signals:
        s["source"] = "TestSource" + s["date"]
        s["url"] = "http://example.com"
    deduper = DedupAgent()
    result = deduper.process(signals)
    assert len(result) == 1
    assert result[0]["source_count"] == 2


def test_stage_predictor_acquirer_not_flagged_as_acquired():
    predictor = StagePredictorAgent()
    profile = {"name": "PayFlux", "employee_estimate": 300}
    signals = [{
        "startup": "PayFlux", "signal_type": "acquisition", "date": "2026-01-01",
        "title": "PayFlux acquires ClearRail", "summary": "PayFlux acquires a small compliance startup",
    }]
    result = predictor.predict(profile, signals)
    assert result["predicted_stage"] != "Acquired / Exited"


def test_stage_predictor_target_flagged_as_acquired():
    predictor = StagePredictorAgent()
    profile = {"name": "Verdant Foods", "employee_estimate": 90}
    signals = [{
        "startup": "Verdant Foods", "signal_type": "acquisition", "date": "2026-01-01",
        "title": "Verdant Foods acquired by BigCo", "summary": "Verdant Foods was acquired by BigCo",
    }]
    result = predictor.predict(profile, signals)
    assert result["predicted_stage"] == "Acquired / Exited"


def test_end_to_end_orchestrator_runs():
    orchestrator = Orchestrator()
    result = orchestrator.run(fetch_live=False)
    assert len(result["startups"]) > 0
    assert result["signal_count_after_dedup"] <= result["signal_count_before_dedup"]
    for s in result["startups"]:
        assert "stage" in s and "insights" in s


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__} -> {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
