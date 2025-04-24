import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import io
from streamlit.components.v1 import html
st.set_page_config(page_title="MLB Daily Leaders", page_icon="⚾", layout="wide")
st.title("MLB Daily Leaders")
dates = sorted((d for d in os.listdir("data") if re.match(r"\d{4}-\d{2}-\d{2}", d)), reverse=True)
date = st.sidebar.selectbox("Select Date", dates)
if date:
    sim_path = f"data/{date}/game_simulations.csv"
    if os.path.exists(sim_path):
        sim = pd.read_csv(sim_path)
        all_batters = []
        all_pitchers = []
        for game_id in sim['game_id']:
            for team_num in [1, 2]:
                batter_path = f"data/{date}/{game_id}/proj_box_batters_{team_num}.csv"
                if os.path.exists(batter_path):
                    df = pd.read_csv(batter_path)
                    game_info = sim[sim['game_id'] == game_id].iloc[0]
                    df['Game'] = f"{game_info['away_team']} @ {game_info['home_team']}"
                    df['Team'] = game_info['away_team'] if team_num == 1 else game_info['home_team']
                    all_batters.append(df)
            for team_num in [1, 2]:
                pitcher_path = f"data/{date}/{game_id}/proj_box_pitchers_{team_num}.csv"
                if os.path.exists(pitcher_path):
                    df = pd.read_csv(pitcher_path)
                    game_info = sim[sim['game_id'] == game_id].iloc[0]
                    df['Game'] = f"{game_info['away_team']} @ {game_info['home_team']}"
                    df['Team'] = game_info['away_team'] if team_num == 1 else game_info['home_team']
                    all_pitchers.append(df)
        leader_tabs = st.tabs([
            "Hitters",
            "Pitchers"
        ])
        with leader_tabs[0]:
            if all_batters:
                batters_df = pd.concat(all_batters, ignore_index=True)
                st.subheader("Top Hitter Projections")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption("Projected Home Run Leaders")
                    hr_leaders = batters_df.nlargest(20, 'HR')[['Batter', 'HR', 'Game']]
                    hr_leaders = hr_leaders.reset_index(drop=True)
                    hr_leaders.index = hr_leaders.index + 1  # Start numbering at 1
                    numeric_cols = hr_leaders.select_dtypes(include=[np.number]).columns
                    hr_leaders[numeric_cols] = hr_leaders[numeric_cols].round(2)
                    st.dataframe(hr_leaders, height=600)  # Removed hide_index=True
                with col2:
                    st.caption("Projected Hits Leaders")
                    hits_leaders = batters_df.nlargest(20, 'H')[['Batter', 'H', '1B', '2B', '3B', 'Team']]
                    hits_leaders = hits_leaders.reset_index(drop=True)
                    hits_leaders.index = hits_leaders.index + 1
                    numeric_cols = hits_leaders.select_dtypes(include=[np.number]).columns
                    hits_leaders[numeric_cols] = hits_leaders[numeric_cols].round(2)
                    st.dataframe(hits_leaders, height=600)
                with col3:
                    st.caption("Projected RBI Leaders")
                    rbi_leaders = batters_df.nlargest(20, 'RBI')[['Batter', 'RBI', 'Team']]
                    rbi_leaders = rbi_leaders.reset_index(drop=True)
                    rbi_leaders.index = rbi_leaders.index + 1
                    numeric_cols = rbi_leaders.select_dtypes(include=[np.number]).columns
                    rbi_leaders[numeric_cols] = rbi_leaders[numeric_cols].round(2)
                    st.dataframe(rbi_leaders, height=600)
            else:
                st.info("No batter projections available for this date")
        with leader_tabs[1]:
            if all_pitchers:
                pitchers_df = pd.concat(all_pitchers, ignore_index=True)
                st.subheader("Top Pitcher Projections")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption("Strikeout Leaders")
                    k_leaders = pitchers_df.nlargest(20, 'K')[['Pitcher', 'K', 'Game']]
                    k_leaders = k_leaders.reset_index(drop=True)
                    k_leaders.index = k_leaders.index + 1
                    numeric_cols = k_leaders.select_dtypes(include=[np.number]).columns
                    k_leaders[numeric_cols] = k_leaders[numeric_cols].round(2)
                    st.dataframe(k_leaders, height=600)
                with col2:
                    st.caption("QS Probability Leaders")
                    qs_leaders = pitchers_df.nlargest(20, 'QS')[['Pitcher', 'QS', 'R', 'Team']]
                    qs_leaders = qs_leaders.reset_index(drop=True)
                    qs_leaders.index = qs_leaders.index + 1
                    qs_leaders['QS'] = (qs_leaders['QS'] * 100).round(1).astype(str) + '%'
                    qs_leaders[['R']] = qs_leaders[['R']].round(2)
                    st.dataframe(qs_leaders, height=600)
                with col3:
                    st.caption("Win Probability Leaders")
                    win_leaders = pitchers_df.nlargest(20, 'W')[['Pitcher', 'W', 'Inn', 'Team']]
                    win_leaders = win_leaders.reset_index(drop=True)
                    win_leaders.index = win_leaders.index + 1
                    win_leaders['W'] = (win_leaders['W'] * 100).round(1).astype(str) + '%'
                    win_leaders[['Inn']] = win_leaders[['Inn']].round(2)
                    st.dataframe(win_leaders, height=600)
            else:
                st.info("No pitcher projections available for this date")
    else:
        st.error(f"Simulation data not found for {date}")
else:
    st.info("Please select a date from the sidebar to view daily leaders")
st.sidebar.markdown("---")
if date and 'batters_df' in locals() and 'pitchers_df' in locals():
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #1f77b4; text-align: center; }}
                h2 {{ color: #2c3e50; margin-top: 30px; }}
                .grid-container {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin: 20px 0;
                }}
                .grid-item {{
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .grid-item h3 {{
                    color: #2c3e50;
                    margin-top: 0;
                    text-align: center;
                }}
                table {{ 
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                    font-size: 14px;
                }}
                th, td {{ 
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{ 
                    background-color: #f8f9fa;
                    color: #2c3e50;
                }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .date {{ 
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                }}
                .section-title {{
                    text-align: center;
                    margin: 40px 0 20px 0;
                    color: #2c3e50;
                    border-bottom: 2px solid #1f77b4;
                    padding-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>MLB Daily Leaders Report</h1>
            <p class="date">Date: {date}</p>
            <h2 class="section-title">Hitter Projections</h2>
            <div class="grid-container">
                <div class="grid-item">
                    <h3>Home Run Leaders</h3>
                    {hr_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>Hits Leaders</h3>
                    {hits_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>RBI Leaders</h3>
                    {rbi_leaders.to_html(index=True)}
                </div>
            </div>
            <h2 class="section-title">Pitcher Projections</h2>
            <div class="grid-container">
                <div class="grid-item">
                    <h3>Strikeout Leaders</h3>
                    {k_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>QS Probability Leaders</h3>
                    {qs_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>Win Probability Leaders</h3>
                    {win_leaders.to_html(index=True)}
                </div>
            </div>
            <p style="text-align: center; margin-top: 40px; color: #666;">
                Generated by MLB AI on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
    </html>
    """
    html_bytes = html_content.encode()
    st.sidebar.download_button(
        label="Generate & Download Report",
        data=html_bytes,
        file_name=f'mlb_daily_leaders_{date}.html',
        mime='text/html',
    )
else:
    st.sidebar.button("Generate & Download Report", disabled=True)
    if st.sidebar.button("Generate & Download Report"):
        st.sidebar.warning("Please select a date and ensure data is loaded first")
st.sidebar.markdown("---")
st.sidebar.markdown("MLB AI © 2025 | [GitHub](https://github.com/bestisblessed) | By Tyler Durette")
