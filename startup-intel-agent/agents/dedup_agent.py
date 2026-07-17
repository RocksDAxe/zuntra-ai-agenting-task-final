"""
DedupAgent
----------
Consolidates signals that describe the SAME underlying event but were
reported by multiple sources (news outlet, directory, company blog, etc.).

Strategy:
  - Group candidate duplicates by (startup, signal_type) and nearby dates
    (within a configurable window, since outlets often report the same
    event a day or two apart).
  - Within a group, use fuzzy title/summary similarity (difflib) to confirm
    they're really the same story before merging.
  - Merged record keeps the earliest date (first to report) and lists all
    contributing sources for transparency/traceability.
"""
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List

DATE_WINDOW_DAYS = 3
SIMILARITY_THRESHOLD = 0.45


def _parse_date(d: str):
    try:
        return datetime.strptime(d, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


class DedupAgent:
    def process(self, signals: List[Dict]) -> List[Dict]:
        # group by (startup, signal_type) first — cheap partition before the
        # more expensive pairwise similarity check
        groups: Dict[tuple, List[Dict]] = {}
        for s in signals:
            key = (s["startup"], s["signal_type"])
            groups.setdefault(key, []).append(s)

        consolidated = []
        for key, group in groups.items():
            consolidated.extend(self._dedup_group(group))

        print(f"[DedupAgent] Consolidated {len(signals)} signals into "
              f"{len(consolidated)} unique events.")
        return consolidated

    def _dedup_group(self, group: List[Dict]) -> List[Dict]:
        used = [False] * len(group)
        merged_events = []

        for i in range(len(group)):
            if used[i]:
                continue
            cluster = [group[i]]
            used[i] = True
            date_i = _parse_date(group[i]["date"])

            for j in range(i + 1, len(group)):
                if used[j]:
                    continue
                date_j = _parse_date(group[j]["date"])
                within_window = True
                if date_i and date_j:
                    within_window = abs((date_i - date_j).days) <= DATE_WINDOW_DAYS

                title_sim = _similarity(group[i]["title"], group[j]["title"])
                summary_sim = _similarity(group[i]["summary"], group[j]["summary"])
                is_same_story = within_window and max(title_sim, summary_sim) >= SIMILARITY_THRESHOLD

                if is_same_story:
                    cluster.append(group[j])
                    used[j] = True

            merged_events.append(self._merge_cluster(cluster))

        return merged_events

    @staticmethod
    def _merge_cluster(cluster: List[Dict]) -> Dict:
        # Prefer the earliest-dated record as the canonical one (first report),
        # keep the longest summary for richer downstream insight generation.
        cluster_sorted_by_date = sorted(
            cluster, key=lambda s: _parse_date(s["date"]) or datetime.max
        )
        canonical = dict(cluster_sorted_by_date[0])
        longest_summary = max(cluster, key=lambda s: len(s.get("summary", "")))
        canonical["summary"] = longest_summary.get("summary", canonical.get("summary", ""))

        # merge funding fields if present anywhere in the cluster
        for s in cluster:
            if s.get("funding_amount_musd", 0) > canonical.get("funding_amount_musd", 0):
                canonical["funding_amount_musd"] = s["funding_amount_musd"]
            if s.get("funding_stage") and not canonical.get("funding_stage"):
                canonical["funding_stage"] = s["funding_stage"]

        canonical["sources"] = sorted({s["source"] for s in cluster})
        canonical["source_count"] = len(canonical["sources"])
        canonical.pop("source", None)
        canonical.pop("url", None)
        canonical["urls"] = sorted({s["url"] for s in cluster if s.get("url")})
        return canonical
