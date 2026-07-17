# 🚀 AI Startup Intelligence Agent

An autonomous **multi-agent system** that gathers startup intelligence from
news, blogs, press releases, and directories; detects funding, product,
hiring, partnership, and acquisition signals; de-duplicates them across
sources; predicts each startup's **growth stage**; and generates AI-powered
**investment insights** — all presented through an interactive dashboard.

Runs out of the box on bundled sample data (no API keys required), and is
built to be pointed at live sources when you're ready.

---

## Architecture — Multi-Agent Workflow

```
                ┌─────────────────────┐
                │   CollectorAgent    │  Scrapes/loads startup directories,
                │  (data collection)  │  tech news, blogs, press releases
                └──────────┬──────────┘
                           ▼
                ┌─────────────────────┐
                │  ExtractionAgent    │  Detects: funding, product launch,
                │  (signal detection) │  hiring, partnership, acquisition,
                └──────────┬──────────┘  leadership change, layoffs
                           ▼
                ┌─────────────────────┐
                │    DedupAgent       │  Fuzzy-matches & merges duplicate
                │ (dedup + consolidate)│  reports of the same event across
                └──────────┬──────────┘  sources
                           ▼
                ┌─────────────────────┐
                │ StagePredictorAgent │  Predicts growth stage:
                │  (growth stage ML)  │  Pre-seed → Seed → Early Growth →
                └──────────┬──────────┘  Late Stage → Acquired/Exited
                           ▼
                ┌─────────────────────┐
                │   InsightAgent      │  Momentum/risk scoring +
                │ (investment insight)│  opportunities/risks/recommendation
                └──────────┬──────────┘  (optional Claude-powered narrative)
                           ▼
        ┌─────────────────────────────────────┐
        │  Structured Dataset (JSON/CSV)       │
        │  Executive Report (Markdown/PDF/XLSX)│
        │  Interactive Streamlit Dashboard      │
        └─────────────────────────────────────┘
```

Each agent is a separate, independently testable module under `agents/`.
`agents/orchestrator.py` coordinates the full run.

---

## Features

| Requirement | Where it lives |
|---|---|
| Scrape startup directories, tech news, blogs, press releases | `agents/collector_agent.py` (seed data + optional live RSS/HTML fetch) |
| Detect funding, launches, hiring, partnerships, acquisitions | `agents/extraction_agent.py` (regex/keyword signal detection) |
| Remove duplicates & consolidate multi-source data | `agents/dedup_agent.py` (fuzzy title/date matching) |
| Predict growth stage | `agents/stage_predictor_agent.py` (explainable rule-based classifier) |
| AI-powered investment insights (opportunities/risks/trends) | `agents/insight_agent.py` (rule-based, optional Claude LLM narrative) |
| Interactive dashboard | `dashboard/app.py` (Streamlit) |
| Structured dataset | `output/startup_dataset.json`, `.csv`, `signals_dataset.csv` |
| Executive report | `output/executive_report.md` |
| **Bonus:** real-time monitoring/alerts | Dashboard "Run pipeline now" refresh + watchlist alerts tab |
| **Bonus:** startup comparison dashboard | Dashboard "Compare" tab (radar chart + side-by-side table) |
| **Bonus:** investment watchlist | Dashboard "Watchlist" tab, persisted to `output/watchlist.json` |
| **Bonus:** PDF/Excel export | `output/executive_report.pdf`, `output/startup_intelligence.xlsx` |

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <this-repo-url>
cd startup-intel-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full multi-agent pipeline (uses bundled sample data)
python main.py

# 4. Launch the interactive dashboard
streamlit run dashboard/app.py
```

That's it — step 3 populates `output/` with the structured dataset and
executive report; step 4 opens the dashboard at `http://localhost:8501`.

### Running on live data (optional)

```bash
python main.py --live \
  --feeds "https://techcrunch.com/feed/" "https://www.google.com/alerts/feeds/your-alert-id" \
  --pages "https://example-startup.com/blog"
```

`--live` additionally pulls from any RSS feeds / HTML pages you pass in,
alongside the bundled seed dataset. If `feedparser` / `requests` /
`beautifulsoup4` aren't installed, live collection is skipped gracefully and
the pipeline still runs on seed data.

### Optional: AI-enhanced insight narratives

By default, insights are generated with a transparent, deterministic
rule-based engine — no API key needed. To generate richer narrative insights
with Claude instead, set:

```bash
export ANTHROPIC_API_KEY="your-key-here"
python main.py
```

If the key isn't set (or the call fails for any reason), the system falls
back to the rule-based engine automatically — the pipeline never breaks.

---

## Project Structure

```
startup-intel-agent/
├── main.py                      # Pipeline entry point
├── config.py                    # Paths, signal-detection rules, settings
├── requirements.txt
├── agents/
│   ├── collector_agent.py       # Data collection (seed + optional live)
│   ├── extraction_agent.py      # Signal detection & structuring
│   ├── dedup_agent.py           # Deduplication / consolidation
│   ├── stage_predictor_agent.py # Growth-stage prediction
│   ├── insight_agent.py         # Investment insight generation
│   └── orchestrator.py          # Coordinates the full workflow
├── reports/
│   └── report_generator.py      # Executive report: Markdown/PDF/Excel
├── dashboard/
│   └── app.py                   # Streamlit interactive dashboard
├── data/
│   ├── seed_sources.json        # Sample raw articles (news/blog/PR/directory)
│   └── sample_startups.json     # Sample startup profile metadata
├── output/                      # Generated dataset + reports (created on run)
└── tests/
    └── test_pipeline.py         # Unit + end-to-end tests
```

---

## How Signal Detection Works

`ExtractionAgent` classifies each article into one or more categories using
keyword/regex rules defined in `config.py`:

- **funding** — "raises $X", "Series A/B/C", "seed round", "valuation of"...
- **product_launch** — "launches", "unveils", "general availability"...
- **hiring** — "hiring", "job openings", "expands its team"...
- **partnership** — "partners with", "joint venture", "collaboration"...
- **acquisition** — "acquires", "acquired by", "merges with"...
- **leadership_change** / **layoffs** — used as risk signals

This keeps the system fast, dependency-light, and fully explainable — every
detected signal traces back to the exact phrase that triggered it. Swap in
a fine-tuned NER/classification model later without changing the rest of
the pipeline (the `ExtractionAgent.process()` interface stays the same).

## How Deduplication Works

`DedupAgent` groups signals by `(startup, signal_type)`, then within each
group uses `difflib` fuzzy string matching on titles/summaries plus a
3-day date window to decide whether two reports describe the *same*
underlying event. Matches are merged into one record listing every
contributing source — so you can see at a glance that, say, a funding round
was corroborated by TechCrunch, a startup directory, *and* the company's own
blog (higher source-count generally implies a more credible signal).

## How Growth-Stage Prediction Works

`StagePredictorAgent` combines: latest funding round detected, total funding
raised, estimated employee count, and presence of risk signals
(layoffs + leadership change ⇒ "Distressed"; being the acquisition
*target* ⇒ "Acquired/Exited"). This rule-based approach is fully
explainable to an investor and easy to recalibrate — a natural next step is
training a supervised classifier on the same feature set once you have
labeled outcomes.

## How Investment Insights Are Generated

`InsightAgent` computes a **momentum score** (weighted by signal type and
number of corroborating sources) and a **risk score** (weighted by layoffs
and leadership churn), then maps them to a recommendation label:
`Strong Buy Signal`, `Watch`, `Caution`, `Insufficient Signal`, or
`Exited`. Opportunities/risks/rationale are generated per startup; if an
`ANTHROPIC_API_KEY` is configured, this step is upgraded to a Claude-written
narrative instead of the template-based one.

---

## Testing

```bash
python tests/test_pipeline.py
# or
python -m pytest tests/ -v
```

---

## Extending This Project

- **Real scraping**: point `CollectorAgent.collect_live_rss` /
  `collect_live_html` at real tech-news RSS feeds, Crunchbase/AngelList-style
  directory pages, or company blogs.
- **Smarter NER**: swap the regex-based `ExtractionAgent` for a spaCy/LLM
  based named-entity + event extractor for messier, unstructured text.
- **Scheduling**: wrap `python main.py --live` in a cron job / GitHub Action
  for continuous real-time monitoring; the dashboard's "Run pipeline now"
  button already demonstrates on-demand refresh.
- **Persistence**: swap the JSON/CSV output for a proper database
  (Postgres/SQLite) once you're tracking hundreds of startups.

---

## License

MIT — see `LICENSE`.
