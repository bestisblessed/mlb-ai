"""
Streamlit page: Batter‑vs‑Pitcher Matchups (2023‑25)
---------------------------------------------------
• Reads StatsAPI CSV bundles from ../data/<year>/
• Calculates OPS, HR/100PA, K% splits vs starter handedness
• Shows bar‑chart cards + scatter, styled like the React demo

Drop this file in Streamlit/pages/ and add the season CSVs to
Streamlit/data/<year>/ then `streamlit run Home.py`.
"""

import ast
import os
import pathlib
from typing import Tuple, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.express.colors import qualitative

# --------------------------------------------------------------------
# 1  DATA DIRECTORY  (aligns with other pages)
# --------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if not os.path.isdir(DATA_DIR):
    DATA_DIR = "data"  # fallback for test runners

SEASONS = (2023, 2024, 2025)

# --------------------------------------------------------------------
# 2  CSV LOADERS (with Streamlit cache)
# --------------------------------------------------------------------
@st.cache_data(show_spinner="📥 Loading StatsAPI CSVs…")
def _load_csv(year: int, name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, str(year), name))


def load_season(year: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        _load_csv(year, f"batters_gamelogs_{year}_statsapi.csv"),
        _load_csv(year, f"pitchers_gamelogs_{year}_statsapi.csv"),
        _load_csv(year, f"batters_details_{year}_statsapi.csv"),
        _load_csv(year, f"pitchers_details_{year}_statsapi.csv"),
    )


@st.cache_data(show_spinner="🔄 Merging seasons…")
def combine_seasons(years=SEASONS):
    parts = [load_season(y) for y in years]
    bat_log = pd.concat([p[0] for p in parts])
    pit_log = pd.concat([p[1] for p in parts])
    bat_det = pd.concat([p[2] for p in parts]).drop_duplicates("player_id")
    pit_det = pd.concat([p[3] for p in parts]).drop_duplicates("player_id")
    return bat_log, pit_log, bat_det, pit_det


# --------------------------------------------------------------------
# 3  SPLIT CALCULATION
# --------------------------------------------------------------------
@st.cache_data(show_spinner="⚙️ Computing split edges…")
def build_edges() -> Dict[str, pd.DataFrame]:
    bat, pit, bat_det, pit_det = combine_seasons()

    # starters + handedness
    pit_st = pit[pit["gamesStarted"] == 1].copy()
    pit_st = pit_st.rename(columns={"player_id": "pitcher_id"})
    pit_det["throws"] = pit_det["pitchHand"].apply(
        lambda x: ast.literal_eval(x)["code"] if pd.notnull(x) else np.nan
    )
    pit_st = pit_st.merge(
        pit_det[["player_id", "throws"]].rename(columns={"player_id": "pitcher_id"}),
        on="pitcher_id",
        how="left",
    )

    # merge by game date + teams
    bat["date"] = pd.to_datetime(bat["date"])
    pit_st["date"] = pd.to_datetime(pit_st["date"])
    merged = bat.merge(
        pit_st[["date", "team", "throws"]],
        left_on=["date", "opponent"],
        right_on=["date", "team"],
        how="inner",
    )

    # rate stats per PA
    merged = merged.assign(
        plateAppearances=lambda d: d["atBats"] + d["baseOnBalls"],
        OBP=lambda d: (d["hits"] + d["baseOnBalls"]) / (d["atBats"] + d["baseOnBalls"]),
        SLG=lambda d: d["totalBases"] / d["atBats"],
    )
    merged["OPS"] = merged["OBP"] + merged["SLG"]
    merged["HR100"] = merged["homeRuns"] / merged["plateAppearances"] * 100
    merged["Kpct"] = merged["strikeOuts"] / merged["plateAppearances"] * 100

    # aggregate
    agg = (
        merged.groupby(["player_id", "throws"])
        .agg(AB=("atBats", "sum"), OPS=("OPS", "mean"), HR100=("HR100", "mean"), Kpct=("Kpct", "mean"))
        .reset_index()
    )
    agg = agg[agg["AB"] >= 30]

    out = {}
    for metric in ["OPS", "HR100", "Kpct"]:
        piv = agg.pivot(index="player_id", columns="throws", values=metric).dropna()
        piv["Diff"] = piv["R"] - piv["L"]
        df = (
            piv.reset_index()
            .merge(bat_det[["player_id", "fullName"]], on="player_id")
            .rename(columns={"fullName": "Batter", "L": "vs_L", "R": "vs_R"})
        )
        out[metric] = df
    return out

edges = build_edges()

# --------------------------------------------------------------------
# 4  VISUAL HELPERS
# --------------------------------------------------------------------
L_COLOR, R_COLOR = qualitative.Plotly[2], qualitative.Plotly[1]


def card_bar(df: pd.DataFrame, metric: str, title: str):
    top = df.sort_values("Diff", ascending=False).head(10)
    fig = go.Figure()
    fig.add_bar(y=top["Batter"], x=top["vs_L"], name=f"{metric} vs LHP", orientation="h", marker_color=L_COLOR)
    fig.add_bar(y=top["Batter"], x=top["vs_R"], name=f"{metric} vs RHP", orientation="h", marker_color=R_COLOR)
    fig.update_layout(
        barmode="stack",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=140, r=20, t=30, b=20),
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _card(title, fig, top[["Batter", "vs_L", "vs_R", "Diff"]])


def _card(title: str, fig: go.Figure, table: pd.DataFrame):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    num_cols = table.select_dtypes("number").columns
    fmt = {c: "{:.3f}" for c in num_cols}
    st.dataframe(table.style.format(fmt), use_container_width=True, hide_index=True, height=180)
    st.markdown("</div>", unsafe_allow_html=True)


def scatter_hr_ops():
    hr = edges["HR100"].sort_values("Diff", ascending=False).head(10)
    ops = edges["OPS"].set_index("player_id")
    scatter = hr.assign(OPS_diff=hr["player_id"].map(ops["Diff"]))
    fig = go.Figure(
        data=go.Scatter(
            x=scatter["Diff"],
            y=scatter["OPS_diff"],
            mode="markers+text",
            text=scatter["Batter"],
            textposition="top center",
            marker=dict(color=L_COLOR, size=10),
        )
    )
    fig.update_layout(
        xaxis_title="HR/100 PA diff (R-L)",
        yaxis_title="OPS diff (R-L)",
        height=320,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    _card("Diff OPS vs Diff HR/100 PA", fig, scatter[["Batter", "Diff", "OPS_diff"]])


# --------------------------------------------------------------------
# 5  PAGE RENDER
# --------------------------------------------------------------------
CSS = """
<style>
.card{background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);padding:1.25rem;margin-bottom:2rem;}
.card h3{font-weight:700;margin-bottom:0.75rem;font-size:1.1rem;}
.stDataFrame tbody tr:nth-child(even){background:#fafafa;}
.stDataFrame tbody td{padding:2px 6px;font-size:0.85rem;}
</style>
"""

st.set_page_config(page_title="Matchups", page_icon="⚾", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("📊 Batter‑vs‑Pitcher Split Dashboard (2023‑25)")

card_bar = card_bar  # alias

# OPS cards
card_bar(edges["OPS"], "OPS", "OPS Advantage vs RHP (Top 10)")
card_bar(edges["OPS"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff").head(10), "OPS", "OPS Advantage vs LHP (Top 10)")

# HR cards
card_bar(edges["HR100"], "HR/100 PA", "HR/100 PA Edge vs RHP (Top 10)")
card_bar(edges["HR100"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff").head(10), "HR/100 PA", "HR/100 PA Edge vs LHP (Top 10)")

# K rate card
card_bar(edges["Kpct"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff", ascending=False).head(10), "K%", "Highest Strike‑out Rate vs RHP")

# scatter
scatter_hr_ops()





## bvp_dashboard_demo.py
#import streamlit as st
#import pandas as pd
#import plotly.graph_objects as go
#from plotly.express.colors import qualitative
#import os
#import re
#from typing import Dict, List
#
#st.set_page_config(page_title="BvP Dashboard", layout="wide")
#st.markdown(
#    """
#    <style>
#      /* ====== Card look ====== */
#      .card     { background:#fff; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); padding:1.25rem; margin-bottom:2rem; }
#      .card h3 { font-weight:700; margin-bottom:0.75rem; }
#      /* tighten table */
#      .stDataFrame tbody tr:nth-child(even) { background:#fafafa; }
#      .stDataFrame tbody td { padding:2px 6px; font-size:0.85rem; }
#    </style>
#    """,
#    unsafe_allow_html=True,
#)
#
## ------------------ Helper functions (from v1) ------------------ #
#
#def _get_data_dir() -> str:
#    """Return absolute path to data directory (works in dev & prod)."""
#    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#    d = os.path.join(base, "data")
#    return d if os.path.exists(d) else "data"
#
#def _parse_matchup_row(raw: str) -> Dict[str, str]:
#    """Parse a single raw line from matchups.csv into a dict."""
#    parts = [p.strip() for p in raw.split(',')]
#    if not parts or parts[0] in ("Team", ""):
#        return {}
#
#    side = parts[0]
#    # Drop empty placeholders
#    rest = [p for p in parts[1:] if p]
#    if len(rest) < 5:
#        return {}
#
#    # First non-empty is Batter name
#    batter = rest[0]
#    # Next numeric is BatterID, then AtBats
#    numeric_idx = next((i for i, p in enumerate(rest[1:], 1) if p.lstrip('-').isdigit()), None)
#    if numeric_idx is None or numeric_idx + 1 >= len(rest):
#        return {}
#
#    batter_id = rest[numeric_idx]
#    at_bats = rest[numeric_idx + 1]
#
#    # Everything after that until next numeric is pitcher name
#    pitcher_tokens: List[str] = []
#    stats_start_idx = None
#    for i in range(numeric_idx + 2, len(rest)):
#        token = rest[i]
#        if token.lstrip('-').isdigit():
#            stats_start_idx = i
#            break
#        pitcher_tokens.append(token)
#
#    if stats_start_idx is None or not pitcher_tokens:
#        return {}
#
#    pitcher = ' '.join(pitcher_tokens)
#    # Remaining tokens are stats: RC, HR, XB, 1B, BB, K (may be fewer)
#    stats = rest[stats_start_idx:]
#    stat_keys = ["RC", "HR", "XB", "1B", "BB", "K"]
#    stat_map = {k: (stats[i] if i < len(stats) else '') for i, k in enumerate(stat_keys)}
#
#    return {
#        "Side": side,
#        "Batter": batter,
#        "BatterID": batter_id,
#        "AtBats": at_bats,
#        "Pitcher": pitcher,
#        **stat_map
#    }
#
#
#def show_bvp_card(title: str, df: pd.DataFrame):
#    """Display BvP data in a card with a bar chart and table."""
#    st.markdown('<div class="card">', unsafe_allow_html=True)
#    st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
#
#    if df.empty:
#        st.warning("No matchup data available.")
#        st.markdown("</div>", unsafe_allow_html=True)
#        return
#
#    # --- Bar chart for Run Components (RC)
#    rc_df = df.sort_values("RC", ascending=True)
#    fig = go.Figure()
#    fig.add_bar(
#        y=rc_df["Batter"],
#        x=rc_df["RC"],
#        name="Run Components",
#        orientation="h",
#        marker_color="#8884d8",
#    )
#    fig.update_layout(
#        height=30 * len(rc_df),
#        margin=dict(l=120, r=20, t=20, b=20),
#    )
#    st.plotly_chart(fig, use_container_width=True)
#
#    # --- Data table
#    display_cols = ["Batter", "Side", "AtBats", "RC", "HR", "XB", "1B", "BB", "K"]
#    st.dataframe(
#        df[display_cols],
#        use_container_width=True,
#        hide_index=True
#    )
#    st.markdown("</div>", unsafe_allow_html=True)
#
#
## ------------------ Layout ------------------ #
#st.markdown("<h1>Batter-vs-Pitcher Matchups</h1>", unsafe_allow_html=True)
#st.divider()
#
#DATA_DIR = _get_data_dir()
## Date selector
#available_dates = sorted(
#    (d for d in os.listdir(DATA_DIR) if re.match(r"\d{4}-\d{2}-\d{2}", d)),
#    reverse=True
#)
#selected_date = st.sidebar.selectbox("Select Date", available_dates)
#
#if not selected_date:
#    st.info("Please choose a date from the sidebar.")
#    st.stop()
#
## Game selector: mirror Home page
#sim_path = os.path.join(DATA_DIR, selected_date, "game_simulations_per_game_tables.csv")
#if not os.path.exists(sim_path):
#    st.error(f"game_simulations_per_game_tables.csv not found for {selected_date}")
#    st.stop()
#
#sim = pd.read_csv(sim_path)
#games = sim.apply(lambda r: f"{r['time']}pm - {r['away_team']} @ {r['home_team']}", axis=1).tolist()
#game_idx = st.sidebar.selectbox("Select Game", range(len(games)), format_func=lambda i: games[i])
#
#if game_idx is None:
#    st.stop()
#
#selected_game = sim.iloc[game_idx]
## extract only last names to match matchups.csv format
#away_starter_full = selected_game["starter_away"]
#home_starter_full = selected_game["starter_home"]
#away_starter_last = away_starter_full.split()[-1]
#home_starter_last = home_starter_full.split()[-1]
#
## --- Load and parse matchup data
#matchup_csv = os.path.join(DATA_DIR, selected_date, "matchups.csv")
#if not os.path.exists(matchup_csv):
#    st.error(f"matchups.csv not found for {selected_date}")
#    st.stop()
#
#records = []
#with open(matchup_csv, "r", encoding="utf-8") as f:
#    next(f)  # skip header
#    for line in f:
#        rec = _parse_matchup_row(line)
#        if rec:
#            records.append(rec)
#
#if not records:
#    st.warning("No matchups found in the file.")
#    st.stop()
#
## build DataFrame from parsed records
#df = pd.DataFrame(records)
#for col in ["AtBats", "RC", "HR", "XB", "1B", "BB", "K"]:
#    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
#
## Split by starting pitcher
#away_matchups = df[df["Pitcher"] == home_starter_last].copy()
#home_matchups = df[df["Pitcher"] == away_starter_last].copy()
#
#
## --- Display Matchup Cards
#col1, col2 = st.columns(2)
#with col1:
#    show_bvp_card(f"{selected_game['away_team']} vs. {home_starter_full}", away_matchups)
#
#with col2:
#    show_bvp_card(f"{selected_game['home_team']} vs. {away_starter_full}", home_matchups)
