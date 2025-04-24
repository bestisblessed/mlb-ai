import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from openai import OpenAI
import time
import os
import re
import openai
# openai_api_key = st.secrets["openai"]["openai_api_key"]
# openai.api_key = openai_api_key
st.set_page_config(page_title="MLB Game Analysis Dashboard", page_icon="⚾", layout="wide")
dates = sorted((d for d in os.listdir("data") if re.match(r"\d{4}-\d{2}-\d{2}", d)), reverse=True)
date = st.sidebar.selectbox("Select Date", dates)
if date:
    sim_path = f"data/{date}/game_simulations.csv"
    detail_path = f"data/{date}/game_simulations_per_game_tables.csv"
    if os.path.exists(sim_path) and os.path.exists(detail_path):
        sim = pd.read_csv(sim_path)
        sim_detailed = pd.read_csv(detail_path)
        games = sim.apply(lambda r: f"{r['time']}pm - {r['away_team']} @ {r['home_team']}", axis=1).tolist()
        game_idx = st.sidebar.selectbox("Select Game", range(len(games)), format_func=lambda i: games[i])
        if game_idx is not None:
            selected_game = sim.iloc[game_idx]
            game_id = selected_game["game_id"]
            away_team = selected_game["away_team"]
            home_team = selected_game["home_team"]
            game_time = selected_game["time"]
            detailed_row = sim_detailed[sim_detailed["game_id"] == game_id].iloc[0]
            st.title(f"{away_team} @ {home_team} - {game_time}")
            st.caption(f"MLB Analysis · Game ID: {game_id} · {date} · {game_time}")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Projected Runs (Away)", f"{selected_game['away_score']:.2f}")
            with col2:
                st.metric("Projected Runs (Home)", f"{selected_game['home_score']:.2f}")
            with col3:
                away_win_prob = detailed_row.get("win_away", "")
                if isinstance(away_win_prob, str) and "%" in away_win_prob:
                    win_pct = re.search(r"(\d+\.\d+)%", away_win_prob)
                    odds = re.search(r"\(([+-]\d+)\)", away_win_prob)
                    if win_pct and odds:
                        formatted_text = f"({odds.group(1)}) {win_pct.group(1)}%"
                        st.metric("Win Probability (Away)", formatted_text)
                    else:
                        st.metric("Win Probability (Away)", away_win_prob)
                else:
                    st.metric("Win Probability (Away)", away_win_prob)
            with col4:
                home_win_prob = detailed_row.get("win_home", "")
                if isinstance(home_win_prob, str) and "%" in home_win_prob:
                    win_pct = re.search(r"(\d+\.\d+)%", home_win_prob)
                    odds = re.search(r"\(([+-]\d+)\)", home_win_prob)
                    if win_pct and odds:
                        formatted_text = f"{win_pct.group(1)}% ({odds.group(1)})"
                        st.metric("Win Probability (Home)", formatted_text)
                    else:
                        st.metric("Win Probability (Home)", home_win_prob)
        else:
                    st.metric("Win Probability (Home)", home_win_prob)
        away_col, home_col = st.columns(2)
        with away_col:
                st.subheader(f"{away_team}")
                pitcher_path = f"data/{date}/{game_id}/proj_box_pitchers_1.csv"
                if os.path.exists(pitcher_path):
                    pitcher_df = pd.read_csv(pitcher_path)
                    if not pitcher_df.empty:
                        st.caption("Starting Pitcher Projection")
                        pitcher = pitcher_df.iloc[0]
                        stats = {
                            "Pitcher": pitcher["Pitcher"],
                            "DK": f"{pitcher['DK']:.1f}",
                            "FD": f"{pitcher['FD']:.1f}",
                            "IP": f"{pitcher['Inn']:.1f}",
                            "K": f"{pitcher['K']:.1f}",
                            "BB": f"{pitcher['BB']:.1f}",
                            "H": f"{pitcher['H']:.1f}",
                            "R": f"{pitcher['R']:.2f}",
                            "Win%": f"{pitcher['W']*100:.0f}%",
                            "QS%": f"{pitcher['QS']*100:.0f}%"
                        }
                        st.table(pd.DataFrame([stats]))
                batters_path = f"data/{date}/{game_id}/proj_box_batters_1.csv"
                if os.path.exists(batters_path):
                    batters_df = pd.read_csv(batters_path)
                    if not batters_df.empty:
                        st.caption("Batting Order Projections")
                        display_cols = ['Batter', 'PA', 'FD', 'DK', 'H', 'R', 'RBI', 'BB', 'K', '1B', '2B', '3B', 'HR', 'SB']
                        formatted_df = batters_df[display_cols].copy()
                        numeric_cols = formatted_df.select_dtypes(include=[np.number]).columns
                        formatted_df[numeric_cols] = formatted_df[numeric_cols].round(2)
                        st.dataframe(formatted_df, hide_index=True)
        with home_col:
                st.subheader(f"{home_team}")
                pitcher_path = f"data/{date}/{game_id}/proj_box_pitchers_2.csv"
                if os.path.exists(pitcher_path):
                    pitcher_df = pd.read_csv(pitcher_path)
                    if not pitcher_df.empty:
                        st.caption("Starting Pitcher Projection")
                        pitcher = pitcher_df.iloc[0]
                        stats = {
                            "Pitcher": pitcher["Pitcher"],
                            "DK": f"{pitcher['DK']:.1f}",
                            "FD": f"{pitcher['FD']:.1f}",
                            "IP": f"{pitcher['Inn']:.1f}",
                            "K": f"{pitcher['K']:.1f}",
                            "BB": f"{pitcher['BB']:.1f}",
                            "H": f"{pitcher['H']:.1f}",
                            "R": f"{pitcher['R']:.2f}",
                            "Win%": f"{pitcher['W']*100:.0f}%",
                            "QS%": f"{pitcher['QS']*100:.0f}%"
                        }
                        st.table(pd.DataFrame([stats]))
                batters_path = f"data/{date}/{game_id}/proj_box_batters_2.csv"
                if os.path.exists(batters_path):
                    batters_df = pd.read_csv(batters_path)
                    if not batters_df.empty:
                        st.caption("Batting Order Projections")
                        display_cols = ['Batter', 'PA', 'FD', 'DK', 'H', 'R', 'RBI', 'BB', 'K', '1B', '2B', '3B', 'HR', 'SB']
                        formatted_df = batters_df[display_cols].copy()
                        numeric_cols = formatted_df.select_dtypes(include=[np.number]).columns
                        formatted_df[numeric_cols] = formatted_df[numeric_cols].round(2)
                        st.dataframe(formatted_df, hide_index=True)
    else:
        st.error(f"Simulation data not found for {date}")
else:
    st.title("MLB Game Analysis Dashboard")
    st.info("Please select a date and game from the sidebar to view projections.")
st.sidebar.markdown("---")
st.sidebar.markdown("MLB AI © 2025 | [GitHub](https://github.com/bestisblessed) | By Tyler Durette")
