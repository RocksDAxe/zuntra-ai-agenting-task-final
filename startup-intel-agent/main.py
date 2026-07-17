"""
AI Startup Intelligence Agent — Pipeline Entry Point
=====================================================
Runs the full multi-agent workflow end to end:

  Collect -> Extract -> Dedupe -> Predict Stage -> Generate Insights
  -> Save structured dataset -> Generate executive report (MD/PDF/XLSX)

Usage:
    python main.py                # run on bundled sample data
    python main.py --live         # also attempt live RSS/HTML collection
    streamlit run dashboard/app.py  # launch the interactive dashboard
"""
import argparse
import json

from agents.orchestrator import Orchestrator
from reports.report_generator import ReportGenerator
import config


def main():
    parser = argparse.ArgumentParser(description="AI Startup Intelligence Agent")
    parser.add_argument("--live", action="store_true",
                         help="Attempt to fetch live data from RSS feeds / pages in addition to seed data")
    parser.add_argument("--feeds", nargs="*", default=[],
                         help="RSS/Atom feed URLs to pull from when --live is set")
    parser.add_argument("--pages", nargs="*", default=[],
                         help="HTML page URLs (e.g. company blogs) to scrape when --live is set")
    args = parser.parse_args()

    print("=" * 70)
    print("AI STARTUP INTELLIGENCE AGENT — running multi-agent pipeline")
    print("=" * 70)

    orchestrator = Orchestrator()
    result = orchestrator.run(fetch_live=args.live, feed_urls=args.feeds, page_urls=args.pages)
    orchestrator.save_outputs(result)

    reporter = ReportGenerator(result)
    reporter.generate_all()

    print("\nPipeline complete. Outputs written to ./output/:")
    for f in [config.DATASET_JSON, config.DATASET_CSV, config.SIGNALS_CSV,
              config.REPORT_MD, config.REPORT_PDF, config.REPORT_XLSX]:
        print(f"  - {f}")

    print("\nTo explore results interactively, run:")
    print("  streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
