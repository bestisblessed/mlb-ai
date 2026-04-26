import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="2024 Player Dashboard", page_icon="⚾", layout="wide")

# ----------------------- Helpers ----------------------- #

def _get_2024_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "..", "Scrapers", "data", "2024")
    return d if os.path.isdir(d) else os.path.join("Scrapers", "data", "2024")

@st.cache_data(show_spinner="Loading player data...")
def load_data():
    data_dir = _get_2024_dir()
    bat_det = pd.read_csv(os.path.join(data_dir, "batters_details_2024_statsapi.csv"), low_memory=False)
    bat_log = pd.read_csv(os.path.join(data_dir, "batters_gamelogs_2024_statsapi.csv"), low_memory=False)
    pit_det = pd.read_csv(os.path.join(data_dir, "pitchers_details_2024_statsapi.csv"), low_memory=False)
    pit_log = pd.read_csv(os.path.join(data_dir, "pitchers_gamelogs_2024_statsapi.csv"), low_memory=False)
    team_log = pd.read_csv(os.path.join(data_dir, "team_gamelogs_2024_statsapi.csv"), low_memory=False)
    return bat_det, bat_log, pit_det, pit_log, team_log

# ----------------------- UI ----------------------- #

st.title("2024 Player Dashboard")

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
        st.dataframe(logs, width="stretch")
        stat = st.selectbox("Stat to Plot", [c for c in ["hits", "homeRuns", "rbi", "strikeOuts", "stolenBases", "avg", "ops"] if c in logs.columns])
        fig = px.line(logs, x="date", y=stat, markers=True, title=f"{stat} over Time")
        st.plotly_chart(fig, width="stretch")
        team = logs["team"].iloc[0]
        team_res = team_log[(team_log["teams_home_team_name"] == team) | (team_log["teams_away_team_name"] == team)][["gameDate", "teams_away_team_name", "teams_home_team_name", "perspective_team_runs", "perspective_opp_runs", "perspective_result"]]
        team_res["gameDate"] = pd.to_datetime(team_res["gameDate"]).dt.date
        st.subheader(f"{team} Results")
        st.dataframe(team_res.sort_values("gameDate"), width="stretch")
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
        st.dataframe(logs, width="stretch")
        stat = st.selectbox("Stat to Plot", [c for c in ["strikeOuts", "baseOnBalls", "hits", "runs", "homeRuns", "era", "whip"] if c in logs.columns])
        fig = px.line(logs, x="date", y=stat, markers=True, title=f"{stat} over Time")
        st.plotly_chart(fig, width="stretch")
        team = logs["team"].iloc[0]
        team_res = team_log[(team_log["teams_home_team_name"] == team) | (team_log["teams_away_team_name"] == team)][["gameDate", "teams_away_team_name", "teams_home_team_name", "perspective_team_runs", "perspective_opp_runs", "perspective_result"]]
        team_res["gameDate"] = pd.to_datetime(team_res["gameDate"]).dt.date
        st.subheader(f"{team} Results")
        st.dataframe(team_res.sort_values("gameDate"), width="stretch")
