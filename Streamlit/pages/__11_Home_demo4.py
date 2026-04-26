import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# --- Dark Mode Modern Design ---
# Game header and basic stats section with dark theme

def display_game_header(game_id, away_team, home_team, game_time, date, 
                       away_score, home_score, win_away, win_home, weather_data=None):
    """Dark mode modern design for game header and basic stats"""
    
    # Custom CSS for dark mode design
    st.markdown("""
    <style>
    .dark-container {
        background-color: #1e1e1e;
        color: #e0e0e0;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .dark-header {
        text-align: center;
        color: #ffffff;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    .dark-metadata {
        color: #a0a0a0;
        font-size: 0.9rem;
        text-align: center;
    }
    .team-section {
        background-color: #2d2d2d;
        border-radius: 6px;
        padding: 15px;
        margin-top: 10px;
    }
    .team-name-dark {
        color: #ffffff;
        font-weight: 600;
        font-size: 1.2rem;
        margin-bottom: 10px;
    }
    .stat-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .stat-label-dark {
        color: #a0a0a0;
    }
    .stat-value-dark {
        color: #ffffff;
        font-weight: 500;
    }
    .highlighted-score {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 5px 0;
        color: #4fc3f7;
    }
    .vs-marker {
        text-align: center;
        font-size: 1.5rem;
        color: #666;
        margin: 15px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    st.markdown(f"""
    <div class="dark-container">
        <div class="dark-header">
            <h2>{away_team} @ {home_team}</h2>
            <div class="dark-metadata">{date} · {game_time} · Game ID: {game_id}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Weather Summary (if available)
    if weather_data:
        st.markdown(f"""
        <div style='text-align:center; margin-bottom:15px; color:#a0a0a0;'>
            {weather_data}
        </div>
        """, unsafe_allow_html=True)
    
    # Score comparison with large numbers
    st.markdown(f"""
    <div style='display:flex; justify-content:space-around; margin:20px 0;'>
        <div style='text-align:center;'>
            <div class='stat-label-dark'>{away_team}</div>
            <div class='highlighted-score'>{away_score:.1f}</div>
        </div>
        <div class='vs-marker'>VS</div>
        <div style='text-align:center;'>
            <div class='stat-label-dark'>{home_team}</div>
            <div class='highlighted-score'>{home_score:.1f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Extract values for styling
    away_pct = float(re.search(r"(\d+\.\d+)%", win_away).group(1)) if re.search(r"(\d+\.\d+)%", win_away) else 50
    home_pct = float(re.search(r"(\d+\.\d+)%", win_home).group(1)) if re.search(r"(\d+\.\d+)%", win_home) else 50
    away_odds = re.search(r"\(([+-]\d+)\)", win_away).group(1) if re.search(r"\(([+-]\d+)\)", win_away) else ""
    home_odds = re.search(r"\(([+-]\d+)\)", win_home).group(1) if re.search(r"\(([+-]\d+)\)", win_home) else ""
    
    # Determine which team is favored for highlighting
    away_favored = "-" in away_odds if away_odds else False
    home_favored = "-" in home_odds if home_odds else False
    
    # Win probability section with colored highlights
    st.markdown("""
    <h3 style='text-align:center; color:#e0e0e0; margin:20px 0 15px 0;'>
        Win Probability
    </h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        away_highlight = "#4fc3f7" if away_favored else "#a0a0a0"
        st.markdown(f"""
        <div class="team-section">
            <div class="team-name-dark">{away_team}</div>
            <div style='font-size:1.8rem; font-weight:700; color:{away_highlight};'>
                {away_pct:.1f}%
            </div>
            <div style='color:{away_highlight}; font-weight:500;'>{away_odds}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        home_highlight = "#4fc3f7" if home_favored else "#a0a0a0"
        st.markdown(f"""
        <div class="team-section">
            <div class="team-name-dark">{home_team}</div>
            <div style='font-size:1.8rem; font-weight:700; color:{home_highlight};'>
                {home_pct:.1f}%
            </div>
            <div style='color:{home_highlight}; font-weight:500;'>{home_odds}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Close the main container
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add "view more" expander for additional stats
    with st.expander("View More Stats"):
        # Total runs
        total_runs = away_score + home_score
        
        st.markdown(f"""
        <div style='background-color:#2d2d2d; padding:15px; border-radius:6px; color:#e0e0e0;'>
            <div style='text-align:center; margin-bottom:10px;'>
                <span style='color:#a0a0a0;'>Total Projected Runs</span>
                <h2 style='color:#ffffff; margin:5px 0;'>{total_runs:.1f}</h2>
            </div>
            <div class='stat-row'>
                <span class='stat-label-dark'>Away Team Score</span>
                <span class='stat-value-dark'>{away_score:.2f}</span>
            </div>
            <div class='stat-row'>
                <span class='stat-label-dark'>Home Team Score</span>
                <span class='stat-value-dark'>{home_score:.2f}</span>
            </div>
            <div class='stat-row'>
                <span class='stat-label-dark'>Run Differential</span>
                <span class='stat-value-dark'>{abs(away_score - home_score):.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Divider
    st.divider()

# Example usage:
if __name__ == "__main__":
    st.set_page_config(page_title="MLB AI - Demo 4", page_icon="⚾", layout="wide")
    
    # Set dark theme for entire app
    st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("MLB AI - Dark Mode Design")
    
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