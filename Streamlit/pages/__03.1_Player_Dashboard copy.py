import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Player Dashboard 2010-2025", page_icon="⚾", layout="wide")

# ----------------------- Helpers ----------------------- #

def _get_data_dirs() -> list[str]:
    """Return all year directories from 2010 through 2025 that exist."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.join(base, "..", "Scrapers", "data")
    if not os.path.isdir(root):
        root = os.path.join("Scrapers", "data")
    years = [str(y) for y in range(2010, 2026)]
    return [os.path.join(root, y) for y in years if os.path.isdir(os.path.join(root, y))]

@st.cache_data(show_spinner="Loading player data...")
def load_data():
    bat_det_list, bat_log_list = [], []
    pit_det_list, pit_log_list = [], []
    team_log_list = []

    for d in _get_data_dirs():
        year = os.path.basename(d)
        bat_det_path = os.path.join(d, f"batters_details_{year}_statsapi.csv")
        if os.path.isfile(bat_det_path):
            bat_det_list.append(pd.read_csv(bat_det_path, low_memory=False))
        bat_log_path = os.path.join(d, f"batters_gamelogs_{year}_statsapi.csv")
        if os.path.isfile(bat_log_path):
            bat_log_list.append(pd.read_csv(bat_log_path, low_memory=False))

        pit_det_path = os.path.join(d, f"pitchers_details_{year}_statsapi.csv")
        if os.path.isfile(pit_det_path):
            pit_det_list.append(pd.read_csv(pit_det_path, low_memory=False))
        pit_log_path = os.path.join(d, f"pitchers_gamelogs_{year}_statsapi.csv")
        if os.path.isfile(pit_log_path):
            pit_log_list.append(pd.read_csv(pit_log_path, low_memory=False))

        team_path = os.path.join(d, f"team_gamelogs_{year}_statsapi.csv")
        if os.path.isfile(team_path):
            team_log_list.append(pd.read_csv(team_path, low_memory=False))

    bat_det = pd.concat(bat_det_list, ignore_index=True) if bat_det_list else pd.DataFrame()
    bat_log = pd.concat(bat_log_list, ignore_index=True) if bat_log_list else pd.DataFrame()
    pit_det = pd.concat(pit_det_list, ignore_index=True) if pit_det_list else pd.DataFrame()
    pit_log = pd.concat(pit_log_list, ignore_index=True) if pit_log_list else pd.DataFrame()
    team_log = pd.concat(team_log_list, ignore_index=True) if team_log_list else pd.DataFrame()
    return bat_det, bat_log, pit_det, pit_log, team_log

# ----------------------- UI ----------------------- #

st.title("Player Dashboard (2010-2025)")

bat_det, bat_log, pit_det, pit_log, team_log = load_data()

player_type = st.radio("Player Type", ["Batter", "Pitcher"], horizontal=True)

def _select_player(df: pd.DataFrame) -> str:
    players = sorted(df["fullName"].unique())
    return st.selectbox("Player", players)

if player_type == "Batter":
    player = _select_player(bat_det)
    if player:
        info = bat_det[bat_det["fullName"] == player].iloc[0]
        logs = bat_log[bat_log["player_id"] == info["player_id"]]
        st.subheader(f"{player} - {info['primaryPosition']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Age", info["currentAge"])
        col2.metric("Height", info["height"])
        col3.metric("Weight", info["weight"])
        bat_side = info.get("batSide", "").replace("{'code': '", "").split("'")[0]
        col4.metric("Bats", bat_side)
        show_cols = ["date", "team", "opponent", "runs", "hits", "homeRuns", "rbi", "strikeOuts", "baseOnBalls", "stolenBases", "avg", "ops"]
        logs = logs[show_cols].copy()
        logs["date"] = pd.to_datetime(logs["date"])
        logs = logs.sort_values("date")
        st.dataframe(logs, use_container_width=True)
        stat = st.selectbox("Stat to Plot", [c for c in ["hits", "homeRuns", "rbi", "strikeOuts", "stolenBases", "avg", "ops"] if c in logs.columns])
        fig = px.line(logs, x="date", y=stat, markers=True, title=f"{stat} over Time")
        st.plotly_chart(fig, use_container_width=True)
        team = logs["team"].iloc[0]
        team_res = team_log[(team_log["teams_home_team_name"] == team) | (team_log["teams_away_team_name"] == team)][["gameDate", "teams_away_team_name", "teams_home_team_name", "perspective_team_runs", "perspective_opp_runs", "perspective_result"]]
        team_res["gameDate"] = pd.to_datetime(team_res["gameDate"]).dt.date
        st.subheader(f"{team} Results")
        st.dataframe(team_res.sort_values("gameDate"), use_container_width=True)
else:
    player = _select_player(pit_det)
    if player:
        info = pit_det[pit_det["fullName"] == player].iloc[0]
        logs = pit_log[pit_log["player_id"] == info["player_id"]]
        st.subheader(f"{player} - {info['primaryPosition']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Age", info["currentAge"])
        col2.metric("Height", info["height"])
        col3.metric("Weight", info["weight"])
        throw_side = info.get("pitchHand", "").replace("{'code': '", "").split("'")[0]
        col4.metric("Throws", throw_side)
        show_cols = ["date", "team", "opponent", "inningsPitched", "strikeOuts", "baseOnBalls", "hits", "runs", "homeRuns", "era", "whip"]
        logs = logs[show_cols].copy()
        logs["date"] = pd.to_datetime(logs["date"])
        logs = logs.sort_values("date")
        st.dataframe(logs, use_container_width=True)
        stat = st.selectbox("Stat to Plot", [c for c in ["strikeOuts", "baseOnBalls", "hits", "runs", "homeRuns", "era", "whip"] if c in logs.columns])
        fig = px.line(logs, x="date", y=stat, markers=True, title=f"{stat} over Time")
        st.plotly_chart(fig, use_container_width=True)
        team = logs["team"].iloc[0]
        team_res = team_log[(team_log["teams_home_team_name"] == team) | (team_log["teams_away_team_name"] == team)][["gameDate", "teams_away_team_name", "teams_home_team_name", "perspective_team_runs", "perspective_opp_runs", "perspective_result"]]
        team_res["gameDate"] = pd.to_datetime(team_res["gameDate"]).dt.date
        st.subheader(f"{team} Results")
        st.dataframe(team_res.sort_values("gameDate"), use_container_width=True)
