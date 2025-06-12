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

st.set_page_config(page_title="Matchups v2", page_icon="⚔️", layout="wide")
st.title("🆚 Matchups v2")

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
    return pd.read_csv(os.path.join(DATA_DIR, str(year), name), low_memory=False)


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
# Match the React demo colors (purple for vs LHP, green for vs RHP)
L_COLOR, R_COLOR = "#8884d8", "#82ca9d"


def card_bar(df: pd.DataFrame, metric: str, title: str):
    top = df.sort_values("Diff", ascending=False).head(10)
    fig = go.Figure()
    fig.add_bar(y=top["Batter"], x=top["vs_L"], name=f"{metric} vs LHP", orientation="h", marker_color=L_COLOR)
    fig.add_bar(y=top["Batter"], x=top["vs_R"], name=f"{metric} vs RHP", orientation="h", marker_color=R_COLOR)
    fig.update_layout(
        barmode="stack",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=140, r=20, t=30, b=20),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    _card(title, fig, top[["Batter", "vs_L", "vs_R", "Diff"]])


def _card(title: str, fig: go.Figure, table: pd.DataFrame):
    st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    num_cols = table.select_dtypes("number").columns
    fmt = {c: "{:.3f}" for c in num_cols}
    st.dataframe(table.style.format(fmt), use_container_width=True, hide_index=True)

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
        height=400,
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

st.markdown(CSS, unsafe_allow_html=True)

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
scatter_hr_ops()
## OPS cards
#card_bar(edges["OPS"], "OPS", "OPS Advantage vs RHP (Top 10)")
#card_bar(edges["OPS"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff").head(10), "OPS", "OPS Advantage vs LHP (Top 10)")
#
## HR cards
#card_bar(edges["HR100"], "HR/100 PA", "HR/100 PA Edge vs RHP (Top 10)")
#card_bar(edges["HR100"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff").head(10), "HR/100 PA", "HR/100 PA Edge vs LHP (Top 10)")
#
## K rate card
#card_bar(edges["Kpct"].assign(Diff=lambda d: d["vs_R"] - d["vs_L"]).sort_values("Diff", ascending=False).head(10), "K%", "Highest Strike‑out Rate vs RHP")
#
## scatter
#scatter_hr_ops()