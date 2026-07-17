"""
Central configuration for the AI Startup Intelligence Agent.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RAW_SOURCES_FILE = DATA_DIR / "seed_sources.json"
STARTUP_SEED_FILE = DATA_DIR / "sample_startups.json"

DATASET_JSON = OUTPUT_DIR / "startup_dataset.json"
DATASET_CSV = OUTPUT_DIR / "startup_dataset.csv"
SIGNALS_CSV = OUTPUT_DIR / "signals_dataset.csv"
REPORT_MD = OUTPUT_DIR / "executive_report.md"
REPORT_PDF = OUTPUT_DIR / "executive_report.pdf"
REPORT_XLSX = OUTPUT_DIR / "startup_intelligence.xlsx"
WATCHLIST_FILE = OUTPUT_DIR / "watchlist.json"

# ---------------------------------------------------------------------------
# Optional AI enhancement (falls back to rule-based logic if not configured)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
USE_LLM_INSIGHTS = bool(ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# Signal detection rules (keyword / regex based, no heavy NLP deps required)
# ---------------------------------------------------------------------------
SIGNAL_KEYWORDS = {
    "funding": [
        r"raise[sd]?\s+\$", r"seed round", r"series [a-e]\b", r"funding round",
        r"led by", r"venture capital", r"secures? \$", r"closes? \$",
        r"valuation of", r"pre-seed",
    ],
    "product_launch": [
        r"launch(es|ed)?", r"unveil(s|ed)?", r"introduc(es|ed|ing)",
        r"general availability", r"now available", r"rolls? out",
        r"debuts?", r"announc(es|ed|ing).*(product|platform|app|feature)",
    ],
    "hiring": [
        r"hiring", r"job openings?", r"expand(s|ed|ing)? (its|the)? team",
        r"new roles?", r"headcount grew", r"open positions?", r"is recruiting",
    ],
    "partnership": [
        r"partners? with", r"partnership with", r"collaborat(es|ed|ion)",
        r"joint venture", r"teams? up with", r"strategic alliance",
        r"integration with",
    ],
    "acquisition": [
        r"acquir(es|ed|ing|es)", r"acquired by", r"merge[sd]? with",
        r"acquisition of", r"buys? \b\w+\b for", r"take over",
    ],
    "leadership_change": [
        r"steps? down", r"appoint(s|ed) .* as (ceo|cto|cfo|coo)",
        r"names? .* as new", r"resigns?", r"joins? as (chief|head)",
    ],
    "layoffs": [
        r"lay(s|ing)? off", r"job cuts", r"reduces? headcount",
        r"restructuring", r"workforce reduction",
    ],
}

# Signals that increase momentum / attractiveness score
POSITIVE_SIGNALS = {"funding", "product_launch", "hiring", "partnership"}
# Signals that increase risk score
RISK_SIGNALS = {"layoffs", "leadership_change"}
# Acquisition is neutral-to-exit (handled specially in stage predictor)

FUNDING_STAGE_ORDER = [
    "pre-seed", "seed", "series a", "series b", "series c",
    "series d", "series e", "ipo", "acquired",
]
