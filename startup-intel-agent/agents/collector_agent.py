"""
CollectorAgent
--------------
Responsible for GATHERING raw intelligence from:
  1. Local seed data (data/seed_sources.json) — always available, powers the demo.
  2. Live sources (optional) — RSS feeds and simple HTML pages, used only when
     `fetch_live=True` and outbound internet access is available. This keeps the
     project fully runnable offline/out-of-the-box while still being a real
     scraper you can point at live sources.

Each raw item is normalized to a common schema:
{
    "source": str, "source_type": str, "startup": str,
    "date": "YYYY-MM-DD", "title": str, "text": str, "url": str
}
"""
import json
from datetime import datetime
from typing import List, Dict

import config


class CollectorAgent:
    def __init__(self, known_startups: List[str] = None):
        self.known_startups = known_startups or []

    # -- local seed data -----------------------------------------------------
    def collect_seed(self) -> List[Dict]:
        with open(config.RAW_SOURCES_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            item.setdefault("collected_at", datetime.utcnow().isoformat())
        return items

    # -- optional live scraping ------------------------------------------------
    def collect_live_rss(self, feed_urls: List[str]) -> List[Dict]:
        """
        Pulls entries from RSS/Atom feeds (tech news sites, company blogs).
        Requires `feedparser` and outbound internet access.
        Silently returns [] if dependencies/network are unavailable, so the
        pipeline never breaks when running in a sandboxed/offline environment.
        """
        items = []
        try:
            import feedparser
        except ImportError:
            print("[CollectorAgent] feedparser not installed; skipping live RSS collection.")
            return items

        for feed_url in feed_urls:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries:
                    title = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    startup = self._match_known_startup(title + " " + summary)
                    items.append({
                        "source": parsed.feed.get("title", feed_url),
                        "source_type": "tech_news",
                        "startup": startup or "Unknown",
                        "date": getattr(entry, "published", datetime.utcnow().isoformat())[:10],
                        "title": title,
                        "text": summary,
                        "url": getattr(entry, "link", feed_url),
                        "collected_at": datetime.utcnow().isoformat(),
                    })
            except Exception as e:  # noqa: BLE001
                print(f"[CollectorAgent] Failed to fetch {feed_url}: {e}")
        return items

    def collect_live_html(self, page_urls: List[str]) -> List[Dict]:
        """
        Fetches a plain HTML page (e.g. a company's /blog or /press page) and
        extracts a rough title + text block. Intended as a lightweight fallback
        for sources without RSS. Requires `requests` + `beautifulsoup4`.
        """
        items = []
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            print("[CollectorAgent] requests/bs4 not installed; skipping live HTML collection.")
            return items

        for url in page_urls:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "StartupIntelBot/1.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string if soup.title else url
                paragraphs = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p")[:15])
                startup = self._match_known_startup(title + " " + paragraphs)
                items.append({
                    "source": url.split("/")[2] if "//" in url else url,
                    "source_type": "company_blog",
                    "startup": startup or "Unknown",
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "title": title,
                    "text": paragraphs,
                    "url": url,
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:  # noqa: BLE001
                print(f"[CollectorAgent] Failed to fetch {url}: {e}")
        return items

    def _match_known_startup(self, text: str) -> str:
        text_lower = text.lower()
        for name in self.known_startups:
            if name.lower() in text_lower:
                return name
        return ""

    def collect_all(self, fetch_live: bool = False, feed_urls=None, page_urls=None) -> List[Dict]:
        items = self.collect_seed()
        if fetch_live:
            items += self.collect_live_rss(feed_urls or [])
            items += self.collect_live_html(page_urls or [])
        print(f"[CollectorAgent] Collected {len(items)} raw articles.")
        return items
