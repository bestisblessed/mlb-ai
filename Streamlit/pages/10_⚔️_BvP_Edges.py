"""Streamlit page: BvP Edge Board.

Loads the daily ranked CSV produced by `scripts/rank_bvp_edges.py` (which
in turn reads the scraper's outputs at `data/<date>/bvp/`). If the day's
data isn't on disk yet, offers a one-click scrape+rank from the UI.

Designed for handicappers — sortable / filterable, with a tab per prop type.
"""
from __future__ import annotations

import os
import sys
import subprocess
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"

st.set_page_config(page_title="BvP Edges", page_icon="⚔️", layout="wide")

st.title("⚔️ Batter vs Pitcher Edge Board")
st.caption(
    "Career BvP splits + two-year weighted hitter priors, shrunk via "
    "empirical-Bayes (Beta-Binomial). Edges = posterior rate − prior rate."
)


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    target_date = st.date_input("Slate date", value=date.today())
    date_str = target_date.strftime("%Y-%m-%d")

    min_pa = st.slider("Min BvP PA", min_value=5, max_value=30, value=10, step=1)
    prior_k = st.slider("Prior strength (k, in PA)", min_value=20, max_value=200,
                        value=60, step=5,
                        help="Beta-Binomial equivalent prior sample size. "
                             "Higher = more shrinkage toward the season prior.")

    st.markdown("---")
    rerun_scrape = st.button("🔄 Re-scrape today (slow)")
    rerun_rank = st.button("🔁 Re-rank only")


def _bvp_dir(date_str: str) -> Path:
    return DATA_DIR / date_str / "bvp"


def _have_data(date_str: str) -> bool:
    d = _bvp_dir(date_str)
    return (d / "bvp_career.csv").exists() and (d / "batter_season.csv").exists() and (d / "games_index.csv").exists()


@st.cache_data(show_spinner=False)
def _load_raw(date_str: str):
    d = _bvp_dir(date_str)
    bvp = pd.read_csv(d / "bvp_career.csv")
    season = pd.read_csv(d / "batter_season.csv")
    games = pd.read_csv(d / "games_index.csv")
    return bvp, season, games


def _run_rank(date_str: str, min_pa: int, prior_k: int):
    cmd = [sys.executable, str(SCRIPTS_DIR / "rank_bvp_edges.py"),
           date_str, "--min-pa", str(min_pa), "--prior-k", str(prior_k)]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    return res.returncode, res.stdout, res.stderr


def _run_scrape(date_str: str):
    cmd = [sys.executable, str(SCRIPTS_DIR / "scrape_bvp_today.py"), date_str]
    res = subprocess.run(cmd, capture_output=True, text=True,
                         cwd=str(REPO_ROOT), timeout=900)
    return res.returncode, res.stdout, res.stderr


# ---------------------------------------------------------------------------
# Action triggers
# ---------------------------------------------------------------------------
if rerun_scrape:
    with st.spinner("Scraping today's BvP from MLB Stats API..."):
        rc, out, err = _run_scrape(date_str)
    if rc == 0:
        st.cache_data.clear()
        st.success("Scrape complete.")
    else:
        st.error(f"Scrape failed (rc={rc})")
        st.code(err or out)

if rerun_rank or rerun_scrape:
    with st.spinner("Computing edges..."):
        rc, out, err = _run_rank(date_str, min_pa, prior_k)
    if rc == 0:
        st.cache_data.clear()
        st.success("Edges re-ranked.")
    else:
        st.error(f"Rank failed (rc={rc})")
        st.code(err or out)


# ---------------------------------------------------------------------------
# Load + render
# ---------------------------------------------------------------------------
if not _have_data(date_str):
    st.warning(
        f"No BvP data for **{date_str}** yet. Click **🔄 Re-scrape today** "
        "in the sidebar (takes ~2-3 min for a full slate)."
    )
    st.stop()

# Always recompute on-the-fly so min_pa / prior_k slider changes are live
sys.path.insert(0, str(SCRIPTS_DIR))
from rank_bvp_edges import compute_edges  # noqa

bvp_df, season_df, games_df = _load_raw(date_str)
qualified, full = compute_edges(bvp_df, season_df, games_df,
                                min_pa=min_pa, prior_k=prior_k)

# ---------------------------------------------------------------------------
# Header KPIs
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Games", len(games_df))
with c2: st.metric("Total BvP rows", len(bvp_df))
with c3: st.metric(f"Qualified (≥{min_pa} PA)", len(qualified))
with c4:
    n_pos = int((qualified["edge_score"] > 0).sum()) if len(qualified) else 0
    st.metric("Positive EDGE", n_pos)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
fc1, fc2, fc3 = st.columns(3)
with fc1:
    teams_all = sorted(set(games_df["away_name"]).union(games_df["home_name"]))
    sel_teams = st.multiselect("Filter teams", teams_all, default=[])
with fc2:
    hand_filter = st.multiselect("Pitcher hand", ["L", "R"], default=[])
with fc3:
    min_score = st.number_input("Min EDGE score", value=0.0, step=0.1, format="%.2f")


def _apply_filters(df):
    out = df
    if sel_teams:
        mask = (
            df["away_name"].isin(sel_teams) | df["home_name"].isin(sel_teams)
        )
        out = out[mask]
    if hand_filter:
        out = out[out["opp_pitcher_hand"].isin(hand_filter)]
    if min_score > 0:
        out = out[out["edge_score"] >= min_score]
    return out


qualified_f = _apply_filters(qualified)


# ---------------------------------------------------------------------------
# Helpers for table rendering
# ---------------------------------------------------------------------------
def _style_edges(df, edge_cols):
    def color(v):
        if pd.isna(v): return ""
        return "color:#3fb950;font-weight:600" if v > 0 else "color:#f85149"
    return df.style.format(
        {**{c: "{:+.1%}" for c in edge_cols},
         "p_h": "{:.3f}", "p_hr": "{:.3f}", "p_obp": "{:.3f}",
         "p_k": "{:.3f}", "season_h_rate": "{:.3f}",
         "season_hr_rate": "{:.3f}", "season_obp": "{:.3f}",
         "season_k_rate": "{:.3f}",
         "p_1plus_hit": "{:.1%}", "p_1plus_hr": "{:.1%}",
         "edge_score": "{:+.2f}", "score_hits": "{:+.2f}",
         "score_hr": "{:+.2f}", "score_obp": "{:+.2f}",
         "score_no_k": "{:+.2f}",
         }
    ).map(color, subset=edge_cols)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_top, tab_hits, tab_hr, tab_obp, tab_k, tab_raw = st.tabs(
    ["🔝 Top Composite", "⚾ Hits", "💣 Home Runs", "🎯 OBP / Hit-or-Walk",
     "🛡️ K-Avoidance", "📋 All / Raw"]
)

common_cols = [
    "batter_name", "pitcher_name", "opp_pitcher_hand",
    "plateAppearances", "hits", "homeRuns", "baseOnBalls", "strikeOuts",
    "bvp_h_rate_raw", "season_h_rate", "p_h",
    "hit_edge", "hr_edge", "obp_edge", "k_avoid_edge",
    "edge_score", "away_name", "home_name", "venue_name",
]

with tab_top:
    st.subheader("Composite Edge Board")
    df = qualified_f.sort_values("edge_score", ascending=False)
    st.dataframe(
        _style_edges(df[common_cols],
                     ["hit_edge", "hr_edge", "obp_edge", "k_avoid_edge"]),
        width='stretch', height=600,
    )

with tab_hits:
    st.subheader("Top Hit Plays (1+ / 2+ hit, total bases)")
    cols = ["batter_name", "pitcher_name", "plateAppearances", "atBats", "hits",
            "bvp_h_rate_raw", "season_h_rate", "p_h",
            "p_1plus_hit", "edge_1plus_hit", "score_hits",
            "away_name", "home_name"]
    df = qualified_f.sort_values("score_hits", ascending=False)[cols]
    st.dataframe(_style_edges(df, ["edge_1plus_hit"]),
                 width='stretch', height=600)

with tab_hr:
    st.subheader("Top Home Run Plays")
    cols = ["batter_name", "pitcher_name", "plateAppearances", "atBats", "homeRuns",
            "bvp_hr_rate_raw", "season_hr_rate", "p_hr",
            "p_1plus_hr", "edge_1plus_hr", "score_hr",
            "away_name", "home_name"]
    df = qualified_f.sort_values("score_hr", ascending=False)[cols]
    st.dataframe(_style_edges(df, ["edge_1plus_hr"]),
                 width='stretch', height=600)

with tab_obp:
    st.subheader("Top OBP / Hit-or-Walk Plays")
    cols = ["batter_name", "pitcher_name", "plateAppearances", "hits",
            "baseOnBalls", "hitByPitch",
            "p_obp", "season_obp", "obp_edge", "score_obp",
            "away_name", "home_name"]
    df = qualified_f.sort_values("score_obp", ascending=False)[cols]
    st.dataframe(_style_edges(df, ["obp_edge"]),
                 width='stretch', height=600)

with tab_k:
    st.subheader("Top K-Avoidance / Contact Plays (under-Ks)")
    cols = ["batter_name", "pitcher_name", "plateAppearances", "atBats",
            "strikeOuts", "p_k", "season_k_rate", "k_avoid_edge", "score_no_k",
            "away_name", "home_name"]
    df = qualified_f.sort_values("score_no_k", ascending=False)[cols]
    st.dataframe(_style_edges(df, ["k_avoid_edge"]),
                 width='stretch', height=600)

with tab_raw:
    st.subheader("Full BvP table (all PAs, qualified + unqualified)")
    full_f = _apply_filters(full)
    st.dataframe(full_f, width='stretch', height=600)
    csv = full_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download full CSV", data=csv,
                       file_name=f"bvp_full_{date_str}.csv",
                       mime="text/csv")


# ---------------------------------------------------------------------------
# Methodology footer
# ---------------------------------------------------------------------------
with st.expander("📐 Methodology / how edges are computed"):
    st.markdown(r"""
**Source.** MLB Stats API, official `vsPlayerTotal` hydrate — career
batter-vs-pitcher splits for every batter on each team's active roster vs the
opposing probable starter.

**Prior.** Two-year weighted hitter rates:
$\text{rate}_{\text{prior}} = \frac{1.5 \cdot x_{\text{cur}} + 1.0 \cdot x_{\text{prev}}}
{1.5 \cdot \text{PA}_{\text{cur}} + 1.0 \cdot \text{PA}_{\text{prev}}}$.
This stabilizes the prior in April when many hitters have <50 PA on the year.
Falls back to league average (.231 H/PA, .029 HR/PA, .318 OBP, .225 K/PA) when
both seasons are 0 PA.

**Posterior.** Beta-Binomial empirical-Bayes shrinkage with prior strength
$k$ (default 60 PA):

$$p_{\text{post}} = \frac{\alpha + x}{\alpha + \beta + n}, \quad
\alpha = p_{\text{prior}} \cdot k, \quad \beta = (1 - p_{\text{prior}}) \cdot k$$

where $x, n$ are observed BvP successes / trials. With $n = 60$ BvP PA and
$k = 60$, the BvP sample carries equal weight to the season prior; with
$n = 10$ PA, the season prior carries ~6× the weight.

**Edges.** $\text{edge} = p_{\text{post}} - p_{\text{prior}}$. A +5% hit edge
means we expect this batter to hit ~5 percentage points above his usual rate
in this matchup.

**1+ hit / 1+ HR.** Convert per-PA rate to per-game using
$1 - (1 - p)^4$ (typical 4 PA / game).

**EDGE_SCORE.** z-weighted blend over today's qualified pool:
40% hits, 30% HR, 20% OBP, 10% K-avoidance.

**Min PA filter.** Excludes BvP samples with fewer than the slider value
of plate appearances.
""")
    st.caption(
        "Sources: scripts/scrape_bvp_today.py · scripts/rank_bvp_edges.py · "
        f"data/{date_str}/bvp/bvp_edges.csv"
    )
