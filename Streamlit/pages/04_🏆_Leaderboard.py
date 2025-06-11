import os
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Leaderboard", page_icon="📈", layout="wide")

# ------------------ Helpers ------------------ #

def _get_data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "data")
    return d if os.path.exists(d) else "data"


def _slug_prefix(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

# ------------------ UI ------------------ #

st.title("📈 Leaderboard")

st.divider()  # Add a divider after the title

DATA_DIR = _get_data_dir()
stats_path = os.path.join(DATA_DIR, "player_batting_stats.csv")

if not os.path.exists(stats_path):
    st.error("player_batting_stats.csv not found in data directory")
    st.stop()

stats_df = pd.read_csv(stats_path)

seasons = sorted(stats_df["Season"].unique(), reverse=True)
metrics_options = [
    "ExitVelocity",
    "Barrel %",
    "HardHit%",
    "WOBA",
]

col1, col2 = st.columns(2)
chosen_season = col1.selectbox("Season", seasons)
metric = col2.selectbox("Metric", metrics_options)

season_df = stats_df[stats_df["Season"] == chosen_season]
# Convert metric column to numeric, "--" or errors become NaN
season_df[metric] = pd.to_numeric(season_df[metric], errors="coerce")
leaders = season_df[["Player Slug", metric]].sort_values(metric, ascending=False, na_position="last")
leaders["Player"] = leaders["Player Slug"].apply(lambda s: " ".join(p.title() for p in s.split("-")[:-1]))

st.subheader(f"Top 50 {metric} - {chosen_season}")  # Update subheader

st.dataframe(leaders.drop(columns=["Player Slug"]).reset_index(drop=True), height=730, use_container_width=True)  # Increase height to display more rows without scrolling