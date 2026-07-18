"""
Streamlit Dashboard — AI Startup Intelligence Agent
====================================================
Run with:  streamlit run dashboard/app.py

Features:
  - Startup profile cards (sector, HQ, funding, stage, momentum/risk)
  - Signal timeline (funding, hiring, launches, partnerships, acquisitions)
  - Growth-stage & recommendation breakdown
  - Startup comparison view (bonus)
  - Investment watchlist with persistence to output/watchlist.json (bonus)
  - One-click "Run pipeline now" for real-time refresh (bonus)
  - PDF / Excel / CSV export download buttons (bonus)
"""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from agents.orchestrator import Orchestrator
from reports.report_generator import ReportGenerator

st.set_page_config(page_title="AI Startup Intelligence Agent", layout="wide", page_icon="🚀")

# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_dataset():
    if not config.DATASET_JSON.exists():
        return None
    with open(config.DATASET_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def run_pipeline():
    with st.spinner("Running multi-agent pipeline (collect → extract → dedupe → predict → insight)..."):
        orchestrator = Orchestrator()
        result = orchestrator.run(fetch_live=False)
        orchestrator.save_outputs(result)
        ReportGenerator(result).generate_all()
    st.cache_data.clear()
    st.success("Pipeline run complete — data refreshed.")


def load_watchlist():
    if config.WATCHLIST_FILE.exists():
        return json.loads(config.WATCHLIST_FILE.read_text())
    return []


def save_watchlist(names):
    config.WATCHLIST_FILE.write_text(json.dumps(sorted(set(names)), indent=2))


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("🚀 Startup Intel Agent")
st.sidebar.caption("Multi-agent pipeline: Collect → Extract → Dedupe → Predict Stage → Insight")


data = load_dataset()
if not data:
    st.warning("No dataset found yet. Click **Run pipeline now** in the sidebar to generate one.")
    st.stop()

startups = data["startups"]
df = pd.DataFrame([{
    "Name": s["name"], "Sector": s["sector"], "HQ": s["headquarters"],
    "Founded": s["founded_year"], "Employees": s["employee_estimate"],
    "Stage": s["stage"]["predicted_stage"], "Confidence": s["stage"]["confidence"],
    "Funding ($M)": s["stage"]["total_funding_musd"],
    "Latest Round": s["stage"]["latest_funding_stage"],
    "Momentum": s["insights"]["momentum_score"], "Risk": s["insights"]["risk_score"],
    "Recommendation": s["insights"]["recommendation"], "Signals": s["signal_count"],
} for s in startups])

sectors = ["All"] + sorted(df["Sector"].unique().tolist())
sel_sector = st.sidebar.selectbox("Filter by sector", sectors)
recommendations = ["All"] + sorted(df["Recommendation"].unique().tolist())
sel_reco = st.sidebar.selectbox("Filter by recommendation", recommendations)

filtered_df = df.copy()
if sel_sector != "All":
    filtered_df = filtered_df[filtered_df["Sector"] == sel_sector]
if sel_reco != "All":
    filtered_df = filtered_df[filtered_df["Recommendation"] == sel_reco]

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Export Reports")
if config.REPORT_PDF.exists():
    st.sidebar.download_button("Download PDF report", config.REPORT_PDF.read_bytes(),
                                file_name="executive_report.pdf", use_container_width=True)
if config.REPORT_XLSX.exists():
    st.sidebar.download_button("Download Excel workbook", config.REPORT_XLSX.read_bytes(),
                                file_name="startup_intelligence.xlsx", use_container_width=True)
if config.DATASET_CSV.exists():
    st.sidebar.download_button("Download CSV dataset", config.DATASET_CSV.read_bytes(),
                                file_name="startup_dataset.csv", use_container_width=True)

# --------------------------------------------------------------------------- #
# Header + KPIs
# --------------------------------------------------------------------------- #
st.title("AI Startup Intelligence Dashboard")
st.caption("Autonomous multi-agent pipeline for startup investment intelligence")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Startups tracked", len(df))
k2.metric("Raw articles ingested", data["raw_article_count"])
k3.metric("Unique signals", data["signal_count_after_dedup"])
dupes = data["signal_count_before_dedup"] - data["signal_count_after_dedup"]
k4.metric("Duplicates merged", dupes)
k5.metric("Strong Buy signals", int((df["Recommendation"] == "Strong Buy Signal").sum()))

tabs = st.tabs(["📊 Overview", "🏢 Profiles", "📈 Signal Timeline",
                "⚖️ Compare", "⭐ Watchlist"])

# --------------------------------------------------------------------------- #
# Tab 1: Overview
# --------------------------------------------------------------------------- #
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.scatter(
            filtered_df, x="Momentum", y="Risk", size="Funding ($M)", color="Stage",
            hover_name="Name", text="Name", title="Momentum vs. Risk (bubble = funding size)",
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        stage_counts = filtered_df["Stage"].value_counts().reset_index()
        stage_counts.columns = ["Stage", "Count"]
        fig2 = px.pie(stage_counts, names="Stage", values="Count", title="Growth Stage Distribution", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.bar(filtered_df.sort_values("Funding ($M)", ascending=True),
                  x="Funding ($M)", y="Name", orientation="h", color="Recommendation",
                  title="Total Funding Tracked by Startup")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Full Dataset")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# Tab 2: Profiles
# --------------------------------------------------------------------------- #
with tabs[1]:
    names_in_view = filtered_df["Name"].tolist()
    for s in startups:
        if s["name"] not in names_in_view:
            continue
        with st.container(border=True):
            top = st.columns([3, 1, 1, 1])
            top[0].markdown(f"### {s['name']}  \n*{s['sector']} · {s['headquarters']}*")
            top[1].metric("Momentum", f"{s['insights']['momentum_score']}/100")
            top[2].metric("Risk", f"{s['insights']['risk_score']}/100")
            top[3].markdown(f"**{s['insights']['recommendation']}**")

            st.markdown(
                f"**Stage:** {s['stage']['predicted_stage']} "
                f"(confidence {s['stage']['confidence']:.0%}) &nbsp;|&nbsp; "
                f"**Funding:** ${s['stage']['total_funding_musd']:.1f}M "
                f"({s['stage']['latest_funding_stage']}) &nbsp;|&nbsp; "
                f"**Employees (est):** {s['employee_estimate']}"
            )
            st.caption(s["insights"]["rationale"])

            oc, rc = st.columns(2)
            with oc:
                st.markdown("**Opportunities**")
                for o in s["insights"]["opportunities"]:
                    st.markdown(f"- {o}")
            with rc:
                st.markdown("**Risks**")
                for r in s["insights"]["risks"]:
                    st.markdown(f"- {r}")

            with st.expander("View raw consolidated signals"):
                sig_df = pd.DataFrame([{
                    "Date": sig["date"], "Type": sig["signal_type"], "Title": sig["title"],
                    "Sources": ", ".join(sig.get("sources", [])), "# Sources": sig.get("source_count", 1),
                } for sig in s["signals"]])
                st.dataframe(sig_df, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# Tab 3: Signal Timeline
# --------------------------------------------------------------------------- #
with tabs[2]:
    all_signals = []
    for s in startups:
        if s["name"] not in filtered_df["Name"].tolist():
            continue
        for sig in s["signals"]:
            all_signals.append({
                "Startup": s["name"], "Date": sig["date"], "Type": sig["signal_type"],
                "Title": sig["title"], "Sources": sig.get("source_count", 1),
            })
    if all_signals:
        sig_df = pd.DataFrame(all_signals).sort_values("Date")
        fig4 = px.scatter(sig_df, x="Date", y="Startup", color="Type", size="Sources",
                           hover_data=["Title"], title="Signal Timeline Across Startups")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(sig_df.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No signals for the current filter selection.")

# --------------------------------------------------------------------------- #
# Tab 4: Compare (bonus)
# --------------------------------------------------------------------------- #
with tabs[3]:
    st.subheader("Startup Comparison")
    options = df["Name"].tolist()
    chosen = st.multiselect("Select 2+ startups to compare", options, default=options[:2])
    if len(chosen) >= 2:
        compare_df = df[df["Name"].isin(chosen)].set_index("Name")
        st.dataframe(compare_df.T, use_container_width=True)

        radar_metrics = ["Momentum", "Risk", "Funding ($M)", "Signals"]
        radar_df = df[df["Name"].isin(chosen)][["Name"] + radar_metrics]
        fig5 = px.line_polar(
            radar_df.melt(id_vars="Name", var_name="Metric", value_name="Value"),
            r="Value", theta="Metric", color="Name", line_close=True,
            title="Comparative Profile"
        )
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Select at least two startups above to compare.")

# --------------------------------------------------------------------------- #
# Tab 5: Watchlist (bonus)
# --------------------------------------------------------------------------- #
with tabs[4]:
    st.subheader("Investment Watchlist")
    current_watchlist = load_watchlist()
    new_watchlist = st.multiselect(
        "Startups on your watchlist", df["Name"].tolist(), default=current_watchlist,
    )
    if st.button("💾 Save watchlist"):
        save_watchlist(new_watchlist)
        st.success(f"Saved {len(new_watchlist)} startup(s) to watchlist.")

    if current_watchlist:
        wl_df = df[df["Name"].isin(current_watchlist)]
        st.dataframe(wl_df, use_container_width=True, hide_index=True)
        for s in startups:
            if s["name"] in current_watchlist:
                for sig in s["signals"]:
                    if sig["signal_type"] in ("funding", "acquisition", "layoffs"):
                        st.info(f"🔔 **{s['name']}** — {sig['title']} ({sig['date']})")
    else:
        st.info("Your watchlist is empty. Select startups above and save.")
