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

st.divider()

DATA_DIR = _get_data_dir()
info_path = os.path.join(DATA_DIR, "player_general_info.csv")
stats_path = os.path.join(DATA_DIR, "player_batting_stats.csv")
bat_log_path = os.path.join(DATA_DIR, "2025", "batters_gamelogs_2025_statsapi.csv")
pitch_log_path = os.path.join(DATA_DIR, "2025", "pitchers_gamelogs_2025_statsapi.csv")

if not os.path.exists(info_path) or not os.path.exists(stats_path):
    st.error("Player info data files not found")
    st.stop()

info_df = pd.read_csv(info_path)
stats_df = pd.read_csv(stats_path)
bat_log_df = pd.read_csv(bat_log_path) if os.path.exists(bat_log_path) else pd.DataFrame()
pitch_log_df = pd.read_csv(pitch_log_path) if os.path.exists(pitch_log_path) else pd.DataFrame()

# Limit selectable players to those that have batting stats available
# Build a set of slug prefixes present in the batting stats (strip numerical id suffix)
stats_slug_prefixes = set(stats_df["Player Slug"].str.replace(r"-\d+$", "", regex=True))
players = sorted([name for name in info_df["Player Name"].unique() if _slug_prefix(name) in stats_slug_prefixes])

# Set Kyle Tucker as the default player
default_player = "Kyle Tucker"
player = st.selectbox("Select Player", players, index=players.index(default_player) if default_player in players else 0)

if player:
    slug_pref = _slug_prefix(player)
    player_stats = stats_df[stats_df["Player Slug"].str.startswith(slug_pref)]
    if player_stats.empty:
        st.warning("No batting stats found for this player")
    else:
        info_row = info_df[info_df["Player Name"] == player].iloc[0]
        st.markdown(
            f"### {player} - {info_row['Position']}\n"
            f"**Bats/Throws:** {info_row['Bats/Throws']}  \n"
            f"**Height:** {info_row['Height']}  \n"
            f"**Weight:** {info_row['Weight']}  \n"
            f"**Age:** {info_row['Age']}"
        )

        # ----- Current Season Stats ----- #
        player_slug = player_stats.iloc[0]["Player Slug"]
        m = re.search(r"-(\d+)$", player_slug)
        player_id = int(m.group(1)) if m else None
        logs_df = pd.DataFrame()
        if player_id:
            if info_row["Position"] == "P" and not pitch_log_df.empty:
                logs_df = pitch_log_df[pitch_log_df["player_id"] == player_id]
            elif not bat_log_df.empty:
                logs_df = bat_log_df[bat_log_df["player_id"] == player_id]

        if not logs_df.empty:
            logs_df = logs_df.sort_values("date")
            st.subheader("2025 Season Stats")
            games_played = len(logs_df)
            if info_row["Position"] == "P":
                totals = logs_df[["inningsPitched", "strikeOuts", "wins", "losses", "saves"]].sum()
                era = logs_df.iloc[-1]["era"]
                whip = logs_df.iloc[-1]["whip"]
                st.markdown(
                    f"**Games:** {games_played} | **IP:** {totals['inningsPitched']:.1f} | "
                    f"**K:** {int(totals['strikeOuts'])} | **W-L:** {int(totals['wins'])}-{int(totals['losses'])} | "
                    f"**Saves:** {int(totals['saves'])} | **ERA:** {era} | **WHIP:** {whip}"
                )
            else:
                totals = logs_df[["hits", "homeRuns", "rbi", "runs", "stolenBases"]].sum()
                last = logs_df.iloc[-1]
                st.markdown(
                    f"**Games:** {games_played} | **AVG:** {last['avg']} | **OBP:** {last['obp']} | "
                    f"**SLG:** {last['slg']} | **OPS:** {last['ops']} | "
                    f"**Runs:** {int(totals['runs'])} | **HR:** {int(totals['homeRuns'])} | "
                    f"**RBI:** {int(totals['rbi'])} | **SB:** {int(totals['stolenBases'])}"
                )
            st.dataframe(logs_df.reset_index(drop=True), use_container_width=True)

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
