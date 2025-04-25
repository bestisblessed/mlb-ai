#import streamlit as st
#import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt
#import plotly.express as px
#import plotly.graph_objects as go
#from plotly.subplots import make_subplots
#from datetime import datetime
#from openai import OpenAI
#import time
#import os
#import re
#import openai
#
#DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Streamlit", "data")
#if not os.path.exists(DATA_DIR):
#    DATA_DIR = "data"
## openai_api_key = st.secrets["openai"]["openai_api_key"]
## openai.api_key = openai_api_key
#st.set_page_config(page_title="MLB Game Analysis Dashboard", page_icon="⚾", layout="wide")
#st.title("MLB Game Analysis Dashboard")
#dates = sorted((d for d in os.listdir(DATA_DIR) if re.match(r"\d{4}-\d{2}-\d{2}", d)), reverse=True)
#date = st.sidebar.selectbox("Select Date", dates)
#if date:
#    sim_path = os.path.join(DATA_DIR, date, "game_simulations.csv")
#    detail_path = os.path.join(DATA_DIR, date, "game_simulations_per_game_tables.csv")
#    if os.path.exists(sim_path) and os.path.exists(detail_path):
#        sim = pd.read_csv(sim_path)
#        sim_detailed = pd.read_csv(detail_path)
#        games = sim.apply(lambda r: f"{r['time']}pm - {r['away_team']} @ {r['home_team']}", axis=1).tolist()
#        game_idx = st.sidebar.selectbox("Select Game", range(len(games)), format_func=lambda i: games[i])
#        if game_idx is not None:
#            selected_game = sim.iloc[game_idx]
#            game_id = str(selected_game["game_id"])
#            away_team = selected_game["away_team"]
#            home_team = selected_game["home_team"]
#            game_time = selected_game["time"]
#            detailed_row = sim_detailed[sim_detailed["game_id"] == int(game_id)].iloc[0]
#            st.subheader(f"{away_team} @ {home_team} - {game_time}")
#            st.caption(f"MLB Analysis · Game ID: {game_id} · {date} · {game_time}")
#            st.divider()
#            col1, col2, col3, col4 = st.columns(4)
#            with col1:
#                st.metric("Projected Runs (Away)", f"{selected_game['away_score']:.2f}")
#            with col2:
#                st.metric("Projected Runs (Home)", f"{selected_game['home_score']:.2f}")
#            with col3:
#                away_win_prob = detailed_row.get("win_away", "")
#                if isinstance(away_win_prob, str) and "%" in away_win_prob:
#                    win_pct = re.search(r"(\d+\.\d+)%", away_win_prob)
#                    odds = re.search(r"\(([+-]\d+)\)", away_win_prob)
#                    if win_pct and odds:
#                        formatted_text = f"({odds.group(1)}) {win_pct.group(1)}%"
#                        st.metric("Win Probability (Away)", formatted_text)
#                    else:
#                        st.metric("Win Probability (Away)", away_win_prob)
#                else:
#                    st.metric("Win Probability (Away)", away_win_prob)
#            with col4:
#                home_win_prob = detailed_row.get("win_home", "")
#                if isinstance(home_win_prob, str) and "%" in home_win_prob:
#                    win_pct = re.search(r"(\d+\.\d+)%", home_win_prob)
#                    odds = re.search(r"\(([+-]\d+)\)", home_win_prob)
#                    if win_pct and odds:
#                        formatted_text = f"{win_pct.group(1)}% ({odds.group(1)})"
#                        st.metric("Win Probability (Home)", formatted_text)
#                    else:
#                        st.metric("Win Probability (Home)", home_win_prob)
#                else:
#                    st.metric("Win Probability (Home)", home_win_prob)
#        st.write("")
#        away_col, home_col = st.columns(2)
#        with away_col:
#                st.subheader(f"{away_team}")
#                pitcher_path = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_1.csv")
#                if os.path.exists(pitcher_path):
#                    pitcher_df = pd.read_csv(pitcher_path)
#                    if not pitcher_df.empty:
#                        st.caption("Starting Pitcher Projection")
#                        pitcher = pitcher_df.iloc[0]
#                        stats = {
#                            "Pitcher": pitcher["Pitcher"],
#                            "DK": f"{pitcher['DK']:.1f}",
#                            "FD": f"{pitcher['FD']:.1f}",
#                            "IP": f"{pitcher['Inn']:.1f}",
#                            "K": f"{pitcher['K']:.1f}",
#                            "BB": f"{pitcher['BB']:.1f}",
#                            "H": f"{pitcher['H']:.1f}",
#                            "R": f"{pitcher['R']:.2f}",
#                            "Win%": f"{pitcher['W']*100:.0f}%",
#                            "QS%": f"{pitcher['QS']*100:.0f}%"
#                        }
#                        st.dataframe(pd.DataFrame([stats]), hide_index=True)
#                batters_path = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_1.csv")
#                if os.path.exists(batters_path):
#                    batters_df = pd.read_csv(batters_path)
#                    if not batters_df.empty:
#                        st.caption("Batting Order Projections")
#                        display_cols = ['Batter', 'PA', 'FD', 'DK', 'H', 'R', 'RBI', 'BB', 'K', '1B', '2B', '3B', 'HR', 'SB']
#                        formatted_df = batters_df[display_cols].copy()
#                        numeric_cols = formatted_df.select_dtypes(include=[np.number]).columns
#                        formatted_df[numeric_cols] = formatted_df[numeric_cols].round(2)
#                        st.dataframe(formatted_df, hide_index=True)
#        with home_col:
#                st.subheader(f"{home_team}")
#                pitcher_path = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_2.csv")
#                if os.path.exists(pitcher_path):
#                    pitcher_df = pd.read_csv(pitcher_path)
#                    if not pitcher_df.empty:
#                        st.caption("Starting Pitcher Projection")
#                        pitcher = pitcher_df.iloc[0]
#                        stats = {
#                            "Pitcher": pitcher["Pitcher"],
#                            "DK": f"{pitcher['DK']:.1f}",
#                            "FD": f"{pitcher['FD']:.1f}",
#                            "IP": f"{pitcher['Inn']:.1f}",
#                            "K": f"{pitcher['K']:.1f}",
#                            "BB": f"{pitcher['BB']:.1f}",
#                            "H": f"{pitcher['H']:.1f}",
#                            "R": f"{pitcher['R']:.2f}",
#                            "Win%": f"{pitcher['W']*100:.0f}%",
#                            "QS%": f"{pitcher['QS']*100:.0f}%"
#                        }
#                        st.dataframe(pd.DataFrame([stats]), hide_index=True)
#                batters_path = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_2.csv")
#                if os.path.exists(batters_path):
#                    batters_df = pd.read_csv(batters_path)
#                    if not batters_df.empty:
#                        st.caption("Batting Order Projections")
#                        display_cols = ['Batter', 'PA', 'FD', 'DK', 'H', 'R', 'RBI', 'BB', 'K', '1B', '2B', '3B', 'HR', 'SB']
#                        formatted_df = batters_df[display_cols].copy()
#                        numeric_cols = formatted_df.select_dtypes(include=[np.number]).columns
#                        formatted_df[numeric_cols] = formatted_df[numeric_cols].round(2)
#                        st.dataframe(formatted_df, hide_index=True)
#    else:
#        st.error(f"Simulation data not found for {date}")
#else:
#    st.title("MLB Game Analysis Dashboard")
#    st.info("Please select a date and game from the sidebar to view projections.")
#st.sidebar.markdown("---")
#st.sidebar.markdown("MLB AI © 2025 | [GitHub](https://github.com/bestisblessed) | By Tyler Durette")
import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# -- DATA_DIR setup (unchanged) --
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Streamlit", "data"
)
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"

# -- Page config & title --
st.set_page_config(page_title="MLB Game Analysis Dashboard",
                   page_icon="⚾", layout="wide")
st.title("MLB Game Analysis Dashboard")

# -- Sidebar: date & game selectors --
dates = sorted(
    (d for d in os.listdir(DATA_DIR)
     if re.match(r"\d{4}-\d{2}-\d{2}", d)),
    reverse=True
)
date = st.sidebar.selectbox("Select Date", dates)

if date:
    sim_path = os.path.join(DATA_DIR, date, "game_simulations.csv")
    detail_path = os.path.join(
        DATA_DIR, date, "game_simulations_per_game_tables.csv"
    )

    if os.path.exists(sim_path) and os.path.exists(detail_path):
        sim = pd.read_csv(sim_path)
        sim_detailed = pd.read_csv(detail_path)

        # build list of game labels
        games = sim.apply(
            lambda r: f"{r['time']}pm - {r['away_team']} @ {r['home_team']}",
            axis=1
        ).tolist()

        game_idx = st.sidebar.selectbox(
            "Select Game", range(len(games)),
            format_func=lambda i: games[i]
        )

        if game_idx is not None:
            # pull selected game
            selected_game = sim.iloc[game_idx]
            game_id      = str(selected_game["game_id"])
            away_team    = selected_game["away_team"]
            home_team    = selected_game["home_team"]
            game_time    = selected_game["time"]
            detailed_row = sim_detailed[
                sim_detailed["game_id"] == int(game_id)
            ].iloc[0]

            # Header & metrics
            st.subheader(f"{away_team} @ {home_team} - {game_time}")
            st.caption(f"MLB Analysis · Game ID: {game_id} · {date} · {game_time}")
            st.divider()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Projected Runs (Away)", f"{selected_game['away_score']:.2f}")
            c2.metric("Projected Runs (Home)", f"{selected_game['home_score']:.2f}")

            # Win probabilities with formatting
            def fmt_win_prob(raw, label, col):
                if isinstance(raw, str) and "%" in raw:
                    pct  = re.search(r"(\d+\.\d+)%", raw)
                    odds = re.search(r"\(([+-]\d+)\)", raw)
                    text = (f"{pct.group(1)}% ({odds.group(1)})"
                            if pct and odds else raw)
                else:
                    text = raw
                col.metric(label, text)

            fmt_win_prob(detailed_row.get("win_away", ""),
                         "Win Probability (Away)", c3)
            fmt_win_prob(detailed_row.get("win_home", ""),
                         "Win Probability (Home)", c4)

    else:
        st.error(f"Simulation data not found for {date}")
        st.stop()

    # -- Main columns: Away vs Home projections --
    away_col, home_col = st.columns(2)

    # -- AWAY PROJECTIONS --
    with away_col:
        st.subheader(away_team)

        # Starting Pitcher
        p1 = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_1.csv")
        if os.path.exists(p1):
            pdf = pd.read_csv(p1)
            if not pdf.empty:
                st.caption("Starting Pitcher Projection")

                # expose URL and reorder
                pdf_display = pdf.copy()
                pdf_display["Player_Link"] = pdf_display["Player URL"]
                cols = [
                    "Player_Link", "Pitcher", "DK", "FD",
                    "Inn", "K", "BB", "H", "R", "W", "QS"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        # LinkColumn takes a list of display_text values (one per row) :contentReference[oaicite:0]{index=0}
                        "Player_Link": st.column_config.LinkColumn(
                            label="Pitcher",
                            display_text=pdf["Pitcher"].tolist()
                        )
                    }
                )

        # Batting Order
        b1 = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_1.csv")
        if os.path.exists(b1):
            bdf = pd.read_csv(b1)
            if not bdf.empty:
                st.caption("Batting Order Projections")

                bdf_display = bdf.copy()
                bdf_display["Player_Link"] = bdf_display["Player URL"]
                cols = [
                    "Batter", "PA", "FD", "DK",
                    "H", "R", "RBI", "BB", "K", "1B", "2B",
                    "3B", "HR", "SB", "Player_Link"
                ]
                bdf_display = bdf_display[cols]
                nums = bdf_display.select_dtypes(include=[np.number]).columns
                bdf_display[nums] = bdf_display[nums].round(2)

                st.dataframe(
                    bdf_display,
                    hide_index=True,
                    column_config={
                    "Player_Link": st.column_config.LinkColumn(
                        label="",
                        display_text="📍",
                        width=30  # Set column width to tiny
                        )
                    }
                )

    # -- HOME PROJECTIONS --
    with home_col:
        st.subheader(home_team)

        # Starting Pitcher
        p2 = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_2.csv")
        if os.path.exists(p2):
            pdf = pd.read_csv(p2)
            if not pdf.empty:
                st.caption("Starting Pitcher Projection")

                pdf_display = pdf.copy()
                pdf_display["Player_Link"] = pdf_display["Player URL"]
                cols = [
                    "Pitcher", "DK", "FD",
                    "Inn", "K", "BB", "H", "R", "W", "QS", "Player_Link"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        "Player_Link": st.column_config.LinkColumn(
                            label="Pitcher",
                            display_text=pdf["Pitcher"].tolist()
                        )
                    }
                )

        # Batting Order
        b2 = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_2.csv")
        if os.path.exists(b2):
            bdf = pd.read_csv(b2)
            if not bdf.empty:
                st.caption("Batting Order Projections")

                bdf_display = bdf.copy()
                bdf_display["Player_Link"] = bdf_display["Player URL"]
                cols = [
                    "Batter", "PA", "FD", "DK",
                    "H", "R", "RBI", "BB", "K", "1B", "2B",
                    "3B", "HR", "SB", "Player_Link"
                ]
                bdf_display = bdf_display[cols]
                nums = bdf_display.select_dtypes(include=[np.number]).columns
                bdf_display[nums] = bdf_display[nums].round(2)

                st.dataframe(
                    bdf_display,
                    hide_index=True,
                    column_config={
                    "Player_Link": st.column_config.LinkColumn(
                        label="",
                        display_text="📍",
                        width=30  # Set column width to tiny
                        )
                    }
                )

else:
    st.info("Please select a date and game from the sidebar to view projections.")

# -- Sidebar footer --
st.sidebar.markdown("---")
st.sidebar.markdown(
    "MLB AI © 2025 | [GitHub]"
    "(https://github.com/bestisblessed) | By Tyler Durette"
)
