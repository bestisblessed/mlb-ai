import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import io
from streamlit.components.v1 import html
import zipfile
import glob

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"

DAILY_HITTER_ROWS = 60
DAILY_PITCHER_ROWS = 40
DAILY_TABLE_HEIGHT = 1200
BVP_TABLE_HEIGHT = 900

TEAM_NAME_BY_ABBR = {
    "ARI": "Arizona Diamondbacks",
    "ATH": "Oakland Athletics",
    "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs",
    "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",
    "DET": "Detroit Tigers",
    "HOU": "Houston Astros",
    "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins",
    "NYM": "New York Mets",
    "NYY": "New York Yankees",
    "OAK": "Oakland Athletics",
    "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres",
    "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants",
    "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",
    "WAS": "Washington Nationals",
}


def _safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    return (num / den).fillna(0.0)


def _clean_batter_name(name):
    if not isinstance(name, str):
        return name
    cleaned = " ".join(name.split())
    match = re.match(r"^(.+)\s+[A-Z]\.\s+(.+)$", cleaned)
    if match and match.group(1).endswith(match.group(2)):
        return match.group(1)
    return cleaned


def build_daily_bvp_board(date_str: str):
    date_dir = os.path.join(DATA_DIR, date_str)
    matchups_path = os.path.join(date_dir, "matchups.csv")
    if not os.path.exists(matchups_path):
        return pd.DataFrame(), {"error": "matchups.csv not found"}
    matchups = pd.read_csv(matchups_path, low_memory=False)
    needed = ["Team", "Batter", "BatterID", "Pitcher", "PitcherID"]
    if not set(needed).issubset(matchups.columns):
        return pd.DataFrame(), {"error": "matchups.csv missing required columns"}
    matchup_keys = matchups[needed].copy()
    matchup_keys["Batter"] = matchup_keys["Batter"].apply(_clean_batter_name)
    matchup_keys = matchup_keys.drop_duplicates()
    matchup_keys["BatterID"] = pd.to_numeric(matchup_keys["BatterID"], errors="coerce").astype("Int64")
    matchup_keys["PitcherID"] = pd.to_numeric(matchup_keys["PitcherID"], errors="coerce").astype("Int64")
    frames = []
    for path in sorted(glob.glob(os.path.join(date_dir, "bvp_*.csv"))):
        try:
            bvp = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        required = {"batter_id", "pitcher_id", "batter", "pitcher"}
        if not required.issubset(bvp.columns):
            continue
        for col in ["atbats", "hits", "homeruns", "baseonballs", "strikeouts", "totalbases", "plateappearances"]:
            if col not in bvp.columns:
                bvp[col] = 0
            bvp[col] = pd.to_numeric(bvp[col], errors="coerce").fillna(0.0)
        bvp["batter_id"] = pd.to_numeric(bvp["batter_id"], errors="coerce").astype("Int64")
        bvp["pitcher_id"] = pd.to_numeric(bvp["pitcher_id"], errors="coerce").astype("Int64")
        frames.append(bvp)
    if not frames:
        return pd.DataFrame(), {"error": "No parseable bvp files"}
    all_bvp = pd.concat(frames, ignore_index=True)
    board = matchup_keys.merge(
        all_bvp.groupby(["batter_id", "pitcher_id"], as_index=False)[["atbats", "hits", "homeruns", "baseonballs", "strikeouts", "totalbases", "plateappearances"]].sum(),
        left_on=["BatterID", "PitcherID"], right_on=["batter_id", "pitcher_id"], how="left"
    )
    for col in ["atbats", "hits", "homeruns", "baseonballs", "strikeouts", "totalbases", "plateappearances"]:
        board[col] = board[col].fillna(0.0)
    board["obp"] = _safe_rate(board["hits"] + board["baseonballs"], board["atbats"] + board["baseonballs"])
    board["slg"] = _safe_rate(board["totalbases"], board["atbats"])
    board["ops"] = board["obp"] + board["slg"]
    board["sample_pa"] = board["plateappearances"].where(board["plateappearances"] > 0, board["atbats"])
    board["hit_rate"] = _safe_rate(board["hits"], board["sample_pa"])
    board["hr_rate"] = _safe_rate(board["homeruns"], board["sample_pa"])
    board["k_rate"] = _safe_rate(board["strikeouts"], board["sample_pa"])
    board["sample_confidence"] = np.clip(np.log1p(board["sample_pa"]) / np.log(16), 0, 1)
    board["hr_edge_score"] = (board["hr_rate"] * 120) * board["sample_confidence"]
    board["bvp_edge_score"] = ((board["ops"] * 45) + (board["hit_rate"] * 35) + (board["hr_rate"] * 120) - (board["k_rate"] * 8)) * board["sample_confidence"]
    return board, {}


def render_bvp_methodology():
    with st.expander("ⓘ Methodology", expanded=False):
        st.markdown(
            """
            **Column definitions**
            - **Batter**: Hitter in the matchup.
            - **Team**: Batter's team.
            - **Pitcher**: Opposing probable starter.
            - **PA**: Plate appearances vs this pitcher; every completed trip to the plate.
            - **H/HR/BB/K**: Hits, home runs, walks, and strikeouts vs this pitcher.
            - **OPS**: On-base percentage plus slugging; quick blend of getting on base and power.
            - **H/PA**: Hits per plate appearance.
            - **HR/PA**: Home runs per plate appearance.
            - **K/PA**: Strikeouts per plate appearance.
            - **Confidence**: Sample-size score based on `log(1 + PA)` capped to `[0, 1]`.
            - **HR Edge**: HR-specific rating from `HR/PA * 120 * Confidence`.
            - **Overall Edge**: Composite rating from OPS, H/PA, HR/PA, K/PA, and Confidence.

            **Note:** PA and AB are not the same. PA includes walks and other plate outcomes; AB excludes walks.
            """
        )

st.set_page_config(page_title="MLB Daily Leaders", page_icon="⚾", layout="wide")
st.title("📊 MLB Daily Leaders")
dates = sorted((d for d in os.listdir(DATA_DIR) if re.match(r"\d{4}-\d{2}-\d{2}", d)), reverse=True)
date = st.sidebar.selectbox("Select Date", dates)
if date:
    sim_path = os.path.join(DATA_DIR, date, "game_simulations.csv")
    if os.path.exists(sim_path):
        sim = pd.read_csv(sim_path)
        all_batters = []
        all_pitchers = []
        for game_id in sim['game_id']:
            game_id = str(game_id)
            for team_num in [1, 2]:
                batter_path = os.path.join(DATA_DIR, date, game_id, f"proj_box_batters_{team_num}.csv")
                if os.path.exists(batter_path):
                    df = pd.read_csv(batter_path)
                    game_info = sim[sim['game_id'] == int(game_id)].iloc[0]
                    df['Game'] = f"{game_info['away_team']} @ {game_info['home_team']}"
                    df['Team'] = game_info['away_team'] if team_num == 1 else game_info['home_team']
                    all_batters.append(df)
            for team_num in [1, 2]:
                pitcher_path = os.path.join(DATA_DIR, date, game_id, f"proj_box_pitchers_{team_num}.csv")
                if os.path.exists(pitcher_path):
                    df = pd.read_csv(pitcher_path)
                    game_info = sim[sim['game_id'] == int(game_id)].iloc[0]
                    df['Game'] = f"{game_info['away_team']} @ {game_info['home_team']}"
                    df['Team'] = game_info['away_team'] if team_num == 1 else game_info['home_team']
                    all_pitchers.append(df)
        leader_tabs = st.tabs(["Hitters", "Pitchers", "BvP Matchups"])
        with leader_tabs[0]:
            if all_batters:
                batters_df = pd.concat(all_batters, ignore_index=True)
                st.subheader("Top Hitter Projections")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption("Home Run Leaders")
                    hr_leaders = batters_df.nlargest(DAILY_HITTER_ROWS, 'HR')[['Batter', 'HR', 'Game']]
                    hr_leaders = hr_leaders.reset_index(drop=True)
                    hr_leaders.index = hr_leaders.index + 1
                    numeric_cols = hr_leaders.select_dtypes(include=[np.number]).columns
                    hr_leaders[numeric_cols] = hr_leaders[numeric_cols].round(2)
                    st.dataframe(hr_leaders, height=DAILY_TABLE_HEIGHT, width="stretch")
                with col2:
                    st.caption("Hits Leaders")
                    hits_leaders = batters_df.nlargest(DAILY_HITTER_ROWS, 'H')[['Batter', 'H', '1B', '2B', '3B', 'Team']]
                    hits_leaders = hits_leaders.reset_index(drop=True)
                    hits_leaders.index = hits_leaders.index + 1
                    numeric_cols = hits_leaders.select_dtypes(include=[np.number]).columns
                    hits_leaders[numeric_cols] = hits_leaders[numeric_cols].round(2)
                    st.dataframe(hits_leaders, height=DAILY_TABLE_HEIGHT, width="stretch")
                with col3:
                    st.caption("RBI Leaders")
                    rbi_leaders = batters_df.nlargest(DAILY_HITTER_ROWS, 'RBI')[['Batter', 'RBI', 'Team']]
                    rbi_leaders = rbi_leaders.reset_index(drop=True)
                    rbi_leaders.index = rbi_leaders.index + 1
                    numeric_cols = rbi_leaders.select_dtypes(include=[np.number]).columns
                    rbi_leaders[numeric_cols] = rbi_leaders[numeric_cols].round(2)
                    st.dataframe(rbi_leaders, height=DAILY_TABLE_HEIGHT, width="stretch")
            else:
                st.info("No batter projections available for this date")
        with leader_tabs[1]:
            if all_pitchers:
                pitchers_df = pd.concat(all_pitchers, ignore_index=True)
                st.subheader("Top Pitcher Projections")
                alt_path = os.path.join(DATA_DIR, date, "pitcher_alt_strikeouts.csv")
                alt_df = None
                if os.path.exists(alt_path):
                    alt_df = pd.read_csv(alt_path)
                    if alt_df is not None:
                        for col in alt_df.columns:
                            if col != "Pitcher":
                                alt_df[col] = alt_df[col].apply(
                                    lambda x: f"+{int(x)}" if pd.notnull(x) and isinstance(x, (int, float)) and x > 0 else (f"{int(x)}" if pd.notnull(x) and isinstance(x, (int, float)) else x)
                                )
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.caption("Strikeout Leaders")
                    k_leaders = pitchers_df.nlargest(DAILY_PITCHER_ROWS, 'K')[['Pitcher', 'K', 'Game']]
                    k_leaders = k_leaders.reset_index(drop=True)
                    k_leaders.index = k_leaders.index + 1
                    numeric_cols = k_leaders.select_dtypes(include=[np.number]).columns
                    k_leaders[numeric_cols] = k_leaders[numeric_cols].round(2)
                    st.dataframe(k_leaders, height=DAILY_TABLE_HEIGHT, width=600)
                with col2:
                    if alt_df is not None:
                        st.caption("Alt Strikeout Odds")
                        st.dataframe(alt_df, height=DAILY_TABLE_HEIGHT, width=900)
                    else:
                        st.info("No alt strikeout odds available for this date")
                st.write("")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption("QS Probability Leaders")
                    qs_leaders = pitchers_df.nlargest(DAILY_PITCHER_ROWS, 'QS')[['Pitcher', 'QS', 'R', 'Team']].reset_index(drop=True)
                    qs_leaders.index += 1
                    qs_leaders['QS'] = (qs_leaders['QS'] * 100).round(1).astype(str) + '%'
                    qs_leaders[['R']] = qs_leaders[['R']].round(2)
                    st.dataframe(qs_leaders, height=DAILY_TABLE_HEIGHT)
                with col2:
                    st.caption("Win Probability Leaders")
                    win_leaders = pitchers_df.nlargest(DAILY_PITCHER_ROWS, 'W')[['Pitcher', 'W', 'Inn', 'Team']].reset_index(drop=True)
                    win_leaders.index += 1
                    win_leaders['W'] = (win_leaders['W'] * 100).round(1).astype(str) + '%'
                    win_leaders[['Inn']] = win_leaders[['Inn']].round(2)
                    st.dataframe(win_leaders, height=DAILY_TABLE_HEIGHT)
                with col3:
                    st.caption("I'm coming...")
                    img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jiri.jpg")
                    st.image(img_path, width="stretch")
            else:
                st.info("No pitcher projections available for this date")
        with leader_tabs[2]:
            bvp_board, bvp_error = build_daily_bvp_board(date)
            if bvp_error.get("error"):
                st.warning(f"BvP leaders unavailable: {bvp_error['error']}")
            else:
                st.subheader("Top 30 Overall Batter-Favorable BvP Matchups")
                top30 = bvp_board[bvp_board["sample_pa"] >= 3].sort_values(["bvp_edge_score", "ops", "sample_pa"], ascending=[False, False, False]).head(30).copy()
                top30["Team"] = top30["Team"].str.upper().map(TEAM_NAME_BY_ABBR).fillna(top30["Team"])
                top30 = top30.rename(columns={
                    "sample_pa": "PA", "hits": "H", "homeruns": "HR",
                    "baseonballs": "BB", "strikeouts": "K", "ops": "OPS", "hit_rate": "H/PA", "hr_rate": "HR/PA",
                    "k_rate": "K/PA", "sample_confidence": "Confidence", "hr_edge_score": "HR Edge", "bvp_edge_score": "Overall Edge"
                })
                bvp_view = top30[["Batter", "Team", "Pitcher", "PA", "H", "HR", "BB", "K", "OPS", "H/PA", "HR/PA", "K/PA", "Confidence", "HR Edge", "Overall Edge"]].copy().reset_index(drop=True)
                bvp_view["Confidence"] = bvp_view["Confidence"].round(2)
                bvp_view[["HR Edge", "Overall Edge"]] = bvp_view[["HR Edge", "Overall Edge"]].round(1)
                bvp_view.index += 1
                st.dataframe(bvp_view, width="stretch", height=BVP_TABLE_HEIGHT)
                render_bvp_methodology()
    else:
        st.error(f"Simulation data not found for {date}")
else:
    st.info("Please select a date from the sidebar to view daily leaders")
st.sidebar.markdown("")
if date and 'batters_df' in locals() and 'pitchers_df' in locals():
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #1f77b4; text-align: center; }}
                h2 {{ color: #2c3e50; margin-top: 30px; }}
                .pitcher-grid-container {{
                    display: grid;
                    grid-template-columns: 1.2fr 2.8fr;
                    gap: 20px;
                    margin: 20px 0;
                }}
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
            <h2 class="section-title">Pitcher Projections</h2>
            <div class="pitcher-grid-container">
                <div class="grid-item">
                    <h3>Strikeout Leaders</h3>
                    {k_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>Alt Strikeout Odds</h3>
                    {alt_df.to_html(index=True) if 'alt_df' in locals() and alt_df is not None else '<p>No alt strikeout odds available for this date</p>'}
                </div>
            </div>
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
            <p style="text-align: center; margin-top: 40px; color: #666;">
                Generated by MLB AI on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
    </html>
    """
    html_dark_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #121212; color: #e0e0e0; }}
                h1 {{ color: #bb86fc; text-align: center; }}
                h2 {{ color: #e0e0e0; margin-top: 30px; }}
                .pitcher-grid-container {{
                    display: grid;
                    grid-template-columns: 1.2fr 2.8fr;
                    gap: 20px;
                    margin: 20px 0;
                }}
                .grid-container {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin: 20px 0;
                }}
                .grid-item {{
                    background: #1e1e1e;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                }}
                .grid-item h3 {{
                    color: #e0e0e0;
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
                    border: 1px solid #444;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #333;
                    color: #e0e0e0;
                }}
                tr:nth-child(even) {{ background-color: #2a2a2a; }}
                .date {{
                    text-align: center;
                    color: #aaa;
                    margin-bottom: 30px;
                }}
                .section-title {{
                    text-align: center;
                    margin: 40px 0 20px 0;
                    color: #e0e0e0;
                    border-bottom: 2px solid #bb86fc;
                    padding-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>MLB Daily Leaders Report</h1>
            <p class="date">Date: {date}</p>
            <h2 class="section-title">Pitcher Projections</h2>
            <div class="pitcher-grid-container">
                <div class="grid-item">
                    <h3>Strikeout Leaders</h3>
                    {k_leaders.to_html(index=True)}
                </div>
                <div class="grid-item">
                    <h3>Alt Strikeout Odds</h3>
                    {alt_df.to_html(index=True) if 'alt_df' in locals() and alt_df is not None else '<p>No alt strikeout odds available for this date</p>'}
                </div>
            </div>
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
            <p style="text-align: center; margin-top: 40px; color: #aaa;">
                Generated by MLB AI on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
    </html>
    """
    light_bytes = html_content.encode()
    dark_bytes = html_dark_content.encode()
    st.sidebar.download_button(
        label="Download Report (Light)",
        data=light_bytes,
        file_name=f'mlb_daily_leaders_{date}_light.html',
        mime='text/html',
    )
    st.sidebar.download_button(
        label="Download Report (Dark)",
        data=dark_bytes,
        file_name=f'mlb_daily_leaders_{date}_dark.html',
        mime='text/html',
    )
else:
    st.sidebar.button("Generate & Download Report", disabled=True)
    if st.sidebar.button("Generate & Download Report"):
        st.sidebar.warning("Please select a date and ensure data is loaded first")
st.sidebar.markdown("---")
st.sidebar.markdown("MLB AI © 2025 | [GitHub](https://github.com/bestisblessed) | By Tyler Durette")
