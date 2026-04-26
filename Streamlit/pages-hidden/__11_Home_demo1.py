import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# --- Modern Card-Based Layout ---
# Game header and basic stats section

# Assuming these variables exist from the main app flow:
# game_id, away_team, home_team, game_time, date
# selected_game with 'away_score' and 'home_score'
# detailed_row with 'win_away' and 'win_home'

def display_game_header(game_id, away_team, home_team, game_time, date, 
                       away_score, home_score, win_away, win_home, weather_data=None):
    """Modern card-based layout for game header and basic stats"""
    
    # --- Game Title Card ---
    st.markdown(f"""
    <div style='background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px;'>
        <h2 style='text-align:center; margin:0;'>{away_team} @ {home_team}</h2>
        <p style='text-align:center; color:#666; margin:5px 0;'>{date} · {game_time} · Game ID: {game_id}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Weather Summary (if available) ---
    if weather_data:
        st.markdown(weather_data, unsafe_allow_html=True)

    # --- Team Cards with Stats ---
    col1, col2 = st.columns(2)
    
    # Away Team Card
    with col1:
        st.markdown(f"""
        <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #1e88e5;'>
            <h3 style='margin:0; color:#1e88e5;'>{away_team}</h3>
            <p style='font-size:1.8rem; margin:10px 0;'>{away_score:.2f}</p>
            <p style='margin:0;'><b>Win Probability:</b> {win_away}</p>
        </div>
        """, unsafe_allow_html=True)

    # Home Team Card
    with col2:
        st.markdown(f"""
        <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #43a047;'>
            <h3 style='margin:0; color:#43a047;'>{home_team}</h3>
            <p style='font-size:1.8rem; margin:10px 0;'>{home_score:.2f}</p>
            <p style='margin:0;'><b>Win Probability:</b> {win_home}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Divider
    st.divider()

# Example usage:
if __name__ == "__main__":
    st.set_page_config(page_title="MLB AI - Demo 1", page_icon="⚾", layout="wide")
    st.title("MLB AI - Card-Based Design")
    
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
        weather_data="<p>🏟️ <i>Roof Closed</i> &nbsp;&nbsp;-&nbsp;&nbsp; 🌞 <i>76–82°F</i></p>"
    )
    
    # Placeholder for the rest of the content
    st.markdown("## Team Details Would Appear Below") 