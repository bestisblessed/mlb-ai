import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# --- Clean Minimalist Layout with Tabs ---
# Game header and basic stats section

def display_game_header(game_id, away_team, home_team, game_time, date, 
                       away_score, home_score, win_away, win_home, weather_data=None):
    """Clean minimalist layout for game header and basic stats with tabs"""
    
    # Custom CSS for minimalist design
    st.markdown("""
    <style>
    .game-header {
        text-align: center;
        margin-bottom: 10px;
    }
    .game-metadata {
        color: #666;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 20px;
    }
    .stat-container {
        padding: 15px;
        background-color: #fafafa;
        border-radius: 5px;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 5px;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0;
    }
    .team-name {
        font-size: 1.3rem;
        font-weight: 500;
        margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Game title
    st.markdown(f"<h2 class='game-header'>{away_team} @ {home_team}</h2>", 
               unsafe_allow_html=True)
    
    # Game metadata
    st.markdown(f"<p class='game-metadata'>{date} · {game_time} · Game ID: {game_id}</p>", 
               unsafe_allow_html=True)
    
    # Weather Summary (if available)
    if weather_data:
        st.markdown(f"<div style='text-align:center; margin-bottom:15px;'>{weather_data}</div>", 
                   unsafe_allow_html=True)
    
    # Create tabs for different views
    overview_tab, matchup_tab, odds_tab = st.tabs(["Overview", "Matchup", "Odds"])
    
    # Overview Tab - Simple score display
    with overview_tab:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class='stat-container'>
                <p class='team-name'>{away_team}</p>
                <p class='stat-label'>Projected Runs</p>
                <p class='stat-value'>{away_score:.2f}</p>
                <p class='stat-label' style='margin-top:10px;'>Win Probability</p>
                <p class='stat-value'>{win_away}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class='stat-container'>
                <p class='team-name'>{home_team}</p>
                <p class='stat-label'>Projected Runs</p>
                <p class='stat-value'>{home_score:.2f}</p>
                <p class='stat-label' style='margin-top:10px;'>Win Probability</p>
                <p class='stat-value'>{win_home}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Matchup Tab - Side-by-side comparison
    with matchup_tab:
        # Extract numerical win probability values
        away_pct = float(re.search(r"(\d+\.\d+)%", win_away).group(1)) if re.search(r"(\d+\.\d+)%", win_away) else 50
        home_pct = float(re.search(r"(\d+\.\d+)%", win_home).group(1)) if re.search(r"(\d+\.\d+)%", win_home) else 50
        
        st.markdown("#### Win Probability")
        st.markdown(f"<div style='display:flex;'>"
                   f"<div style='flex:1; text-align:left;'>{win_away}</div>"
                   f"<div style='flex:1; text-align:right;'>{win_home}</div>"
                   "</div>", unsafe_allow_html=True)
                   
        # Combined progress bar
        st.progress(away_pct/100)
        
        st.markdown("#### Projected Runs")
        
        # Create comparison chart
        chart_data = pd.DataFrame({
            'Team': [away_team, home_team],
            'Runs': [away_score, home_score]
        })
        st.bar_chart(chart_data.set_index('Team'))
    
    # Odds Tab - View focusing on betting odds
    with odds_tab:
        # Extract odds values
        away_odds = re.search(r"\(([+-]\d+)\)", win_away).group(1) if re.search(r"\(([+-]\d+)\)", win_away) else ""
        home_odds = re.search(r"\(([+-]\d+)\)", win_home).group(1) if re.search(r"\(([+-]\d+)\)", win_home) else ""
        
        # Use favorite/underdog color coding
        away_color = "#43a047" if "-" in away_odds else "#e57373"  # Green for favorite, red for underdog
        home_color = "#43a047" if "-" in home_odds else "#e57373"
        
        st.markdown("### Betting Odds")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div style='padding:10px; border-radius:5px;'>
                <p style='color:#666; font-size:0.9rem; margin:0;'>{away_team}</p>
                <h2 style='color:{away_color}; margin:0;'>{away_odds}</h2>
                <p style='font-size:0.9rem; margin:0;'>Win Prob: {away_pct:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div style='padding:10px; border-radius:5px;'>
                <p style='color:#666; font-size:0.9rem; margin:0;'>{home_team}</p>
                <h2 style='color:{home_color}; margin:0;'>{home_odds}</h2>
                <p style='font-size:0.9rem; margin:0;'>Win Prob: {home_pct:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
        # Show over/under
        total_runs = away_score + home_score
        st.markdown(f"""
        <div style='text-align:center; margin-top:20px;'>
            <p style='color:#666; font-size:0.9rem; margin:0;'>Total (Over/Under)</p>
            <h2>{total_runs:.1f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Divider after all tabs
    st.divider()

# Example usage:
if __name__ == "__main__":
    st.set_page_config(page_title="MLB AI - Demo 3", page_icon="⚾", layout="wide")
    st.title("MLB AI - Minimalist Design with Tabs")
    
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