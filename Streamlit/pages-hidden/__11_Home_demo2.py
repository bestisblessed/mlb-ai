import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# --- Dashboard/Scoreboard Style Layout ---
# Game header and basic stats section with prominent score display

def display_game_header(game_id, away_team, home_team, game_time, date, 
                       away_score, home_score, win_away, win_home, weather_data=None):
    """Dashboard/Scoreboard style layout for game header and basic stats"""
    
    # Custom CSS for styling
    st.markdown("""
    <style>
    .scoreboard {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 20px;
    }
    .team {
        padding: 10px 20px;
        text-align: center;
        flex-grow: 1;
    }
    .score {
        font-size: 3.5rem;
        font-weight: bold;
        padding: 0 20px;
    }
    .versus {
        font-size: 1.5rem;
        padding: 0 15px;
        color: #666;
    }
    .game-info {
        text-align: center;
        color: #666;
        margin-bottom: 15px;
    }
    .prob-bar {
        height: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Game info bar (date, time, ID)
    st.markdown(f"""
    <div class='game-info'>
        <p>{date} · {game_time} · Game ID: {game_id}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Scoreboard main display
    st.markdown(f"""
    <div class='scoreboard'>
        <div class='team'>
            <h3>{away_team}</h3>
            <div class='score'>{away_score:.1f}</div>
        </div>
        <div class='versus'>@</div>
        <div class='team'>
            <h3>{home_team}</h3>
            <div class='score'>{home_score:.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Weather Summary (if available)
    if weather_data:
        st.markdown(f"<div style='text-align:center; margin-bottom:15px;'>{weather_data}</div>", 
                    unsafe_allow_html=True)
    
    # Win probability bars
    col1, gap, col2 = st.columns([47, 6, 47])
    
    # Extract win percentage values
    away_pct = float(re.search(r"(\d+\.\d+)%", win_away).group(1)) if re.search(r"(\d+\.\d+)%", win_away) else 50
    home_pct = float(re.search(r"(\d+\.\d+)%", win_home).group(1)) if re.search(r"(\d+\.\d+)%", win_home) else 50
    
    # Away team probability
    with col1:
        st.markdown(f"<p style='margin:0; text-align:center;'><b>{win_away}</b></p>", unsafe_allow_html=True)
        st.progress(away_pct/100)
    
    # VS in middle
    with gap:
        st.markdown("<p style='text-align:center; margin-top:20px;'>VS</p>", unsafe_allow_html=True)
    
    # Home team probability
    with col2:
        st.markdown(f"<p style='margin:0; text-align:center;'><b>{win_home}</b></p>", unsafe_allow_html=True)
        st.progress(home_pct/100)
    
    # Divider
    st.divider()

# Example usage:
if __name__ == "__main__":
    st.set_page_config(page_title="MLB AI - Demo 2", page_icon="⚾", layout="wide")
    st.title("MLB AI - Scoreboard Design")
    
    # Example values
    display_game_header(
        game_id="777483", 
        away_team="Philadelphia Phillies", 
        home_team="Miami Marlins", 
        game_time="6:40", 
        date="2025-06-16",
        away_score=4.88, 
        home_score=4.39, 
        win_away="53.8% (-116)", 
        win_home="46.2% (+116)",
        weather_data="🏟️ <i>Roof Closed</i> &nbsp;&nbsp;-&nbsp;&nbsp; 🌞 <i>76–82°F</i>"
    )
    
    # Placeholder for the rest of the content
    st.markdown("## Team Details Would Appear Below") 