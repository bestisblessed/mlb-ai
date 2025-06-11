import os
import re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Player Dashboard", page_icon="🧢", layout="wide")
# ------------------ Helpers ------------------ #

def _get_data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "data")
    return d if os.path.exists(d) else "data"


def _slug_prefix(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ------------------ UI ------------------ #

st.title("🧢 Player Dashboard")

DATA_DIR = _get_data_dir()
info_path = os.path.join(DATA_DIR, "player_general_info.csv")
stats_path = os.path.join(DATA_DIR, "player_batting_stats.csv")

if not os.path.exists(info_path) or not os.path.exists(stats_path):
    st.error("Player info data files not found")
    st.stop()

info_df = pd.read_csv(info_path)
stats_df = pd.read_csv(stats_path)

# Limit selectable players to those that have batting stats available
# Build a set of slug prefixes present in the batting stats (strip numerical id suffix)
stats_slug_prefixes = set(stats_df["Player Slug"].str.replace(r"-\d+$", "", regex=True))
players = sorted([name for name in info_df["Player Name"].unique() if _slug_prefix(name) in stats_slug_prefixes])

player = st.selectbox("Select Player", players)

if player:
    slug_pref = _slug_prefix(player)
    player_stats = stats_df[stats_df["Player Slug"].str.startswith(slug_pref)]
    if player_stats.empty:
        st.warning("No batting stats found for this player")
    else:
        info_row = info_df[info_df["Player Name"] == player].iloc[0]
        st.subheader(f"{player} - {info_row['Position']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Bats/Throws", info_row["Bats/Throws"])
        col2.metric("Height", info_row["Height"])
        col3.metric("Weight", info_row["Weight"])
        col4.metric("Age", str(info_row["Age"]))

        numeric_cols = [
            "ExitVelocity",
            "LaunchAngle",
            "HardHit%",
            "Barrel %",
            "Barrel/PA",
            "XBA",
            "XSLG",
            "WOBA",
            "XWOBA",
            "K%",
            "BB%",
        ]
        display_df = player_stats[["Season"] + [c for c in numeric_cols if c in player_stats.columns]].copy()
        display_df = display_df.sort_values("Season")
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

        if "ExitVelocity" in display_df.columns:
            fig = px.line(display_df, x="Season", y="ExitVelocity", markers=True,
                          title="Average Exit Velocity by Season")
            st.plotly_chart(fig, use_container_width=True)
        if "Barrel %" in display_df.columns:
            fig2 = px.bar(display_df, x="Season", y="Barrel %",
                          title="Barrel Rate by Season")
            st.plotly_chart(fig2, use_container_width=True)
