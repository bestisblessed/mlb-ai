import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import matplotlib.pyplot as plt
import io

# --- Sports Broadcast Style Layout ---
# Game header and basic stats section inspired by TV broadcasts

def create_gauge_chart(percent, color='#1d3c78'):
    """Create a gauge chart for win probability visualization"""
    fig, ax = plt.subplots(figsize=(3, 1.5), subplot_kw={'polar': True})
    
    # Gauge settings
    pos = (percent/100) * np.pi
    
    # Background ring
    ax.barh(0, np.pi, height=0.6, color='#e0e0e0', alpha=0.3)
    
    # Foreground ring
    ax.barh(0, pos, height=0.6, color=color)
    
    # Customize gauge
    ax.set_xlim(0, np.pi)
    ax.set_ylim(-0.8, 0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines.clear()
    
    # Add percentage text in the middle
    ax.text(np.pi/2, 0, f"{percent:.1f}%", 
           ha='center', va='center', fontsize=12, fontweight='bold')
    
    # Convert plot to image
    buf = io.BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf

def display_game_header(game_id, away_team, home_team, game_time, date, 
                       away_score, home_score, win_away, win_home, weather_data=None):
    """Sports broadcast style layout for game header and basic stats"""
    
    # Custom CSS for broadcast style
    st.markdown("""
    <style>
    .broadcast-header {
        background: linear-gradient(90deg, #1d3c78 0%, #2a5298 100%);
        color: white;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    .matchup-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 10px 0;
    }
    .team-block {
        flex: 1;
        text-align: center;
    }
    .team-name-large {
        font-size: 1.6rem;
        font-weight: bold;
        margin: 0;
    }
    .team-record {
        color: #ccc;
        font-size: 0.9rem;
    }
    .score-block {
        background-color: #fff;
        color: #333;
        padding: 5px 15px;
        border-radius: 5px;
        margin: 0 10px;
        font-size: 2.2rem;
        font-weight: bold;
        min-width: 60px;
        text-align: center;
    }
    .metadata-bar {
        display: flex;
        justify-content: space-between;
        background-color: rgba(255,255,255,0.1);
        padding: 5px 10px;
        border-radius: 3px;
        margin-top: 10px;
        font-size: 0.9rem;
    }
    .stat-block {
        background-color: white;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stat-header {
        color: #1d3c78;
        font-weight: bold;
        border-bottom: 2px solid #eee;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Broadcast header
    st.markdown(f"""
    <div class="broadcast-header">
        <div class="matchup-row">
            <div class="team-block">
                <p class="team-name-large">{away_team.upper()}</p>
            </div>
            <div class="score-block">{away_score:.1f}</div>
            <div style="font-size:1.2rem; font-weight:bold;">@</div>
            <div class="score-block">{home_score:.1f}</div>
            <div class="team-block">
                <p class="team-name-large">{home_team.upper()}</p>
            </div>
        </div>
        <div class="metadata-bar">
            <div>{date} · {game_time}</div>
            <div>Game ID: {game_id}</div>
            <div>{weather_data if weather_data else ""}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Extract win percentage values for visuals
    away_pct = float(re.search(r"(\d+\.\d+)%", win_away).group(1)) if re.search(r"(\d+\.\d+)%", win_away) else 50
    home_pct = float(re.search(r"(\d+\.\d+)%", win_home).group(1)) if re.search(r"(\d+\.\d+)%", win_home) else 50
    away_odds = re.search(r"\(([+-]\d+)\)", win_away).group(1) if re.search(r"\(([+-]\d+)\)", win_away) else ""
    home_odds = re.search(r"\(([+-]\d+)\)", win_home).group(1) if re.search(r"\(([+-]\d+)\)", win_home) else ""
    
    # Create two columns for team stats
    col1, col2 = st.columns(2)
    
    # Away team stats
    with col1:
        st.markdown("""
        <div class="stat-block">
            <div class="stat-header">VISITOR PROJECTION</div>
        """, unsafe_allow_html=True)
        
        # Win probability gauge for away team
        gauge_img = create_gauge_chart(away_pct, '#1d3c78')
        st.image(gauge_img, caption=f"{away_team} Win Probability")
        
        # Stat rows
        st.markdown(f"""
            <div style="margin:15px 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>Projected Runs</span>
                    <span style="font-weight:bold;">{away_score:.2f}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>Win Odds</span>
                    <span style="font-weight:bold;">{away_odds}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Home team stats
    with col2:
        st.markdown("""
        <div class="stat-block">
            <div class="stat-header">HOME PROJECTION</div>
        """, unsafe_allow_html=True)
        
        # Win probability gauge for home team
        gauge_img = create_gauge_chart(home_pct, '#d32f2f')
        st.image(gauge_img, caption=f"{home_team} Win Probability")
        
        # Stat rows
        st.markdown(f"""
            <div style="margin:15px 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>Projected Runs</span>
                    <span style="font-weight:bold;">{home_score:.2f}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>Win Odds</span>
                    <span style="font-weight:bold;">{home_odds}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Total runs and over/under
    total_runs = away_score + home_score
    
    st.markdown(f"""
    <div class="stat-block" style="text-align:center;">
        <div class="stat-header">GAME TOTAL</div>
        <h1 style="font-size:2.5rem; margin:10px 0;">{total_runs:.1f}</h1>
        <div style="color:#666;">Projected Total Runs</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Divider
    st.divider()

# Example usage:
if __name__ == "__main__":
    st.set_page_config(page_title="MLB AI - Demo 5", page_icon="⚾", layout="wide")
    st.title("MLB AI - Sports Broadcast Style")
    
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
        weather_data="🏟️ Roof Closed · 🌞 76–82°F"
    )
    
    # Placeholder for the rest of the content
    st.markdown("## Team Details Would Appear Below") 