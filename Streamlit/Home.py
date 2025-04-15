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

# At the top of your file, after imports
OPENAI_API_KEY = st.secrets["general"]["OPENAI_API_KEY"]
api_key = OPENAI_API_KEY

st.set_page_config(page_title="MLB AI", page_icon="⚾", layout="wide")

# ---- Loading Data ---- #
base_dir = os.path.dirname(os.path.abspath(__file__))
df_player_general = pd.read_csv(os.path.join(base_dir, 'data/player_general_info.csv'))
df_player_stats = pd.read_csv(os.path.join(base_dir, 'data/player_batting_stats.csv'))

# Convert strings to lowercase for consistency
df_player_general = df_player_general.map(lambda x: x.lower() if isinstance(x, str) else x)
df_player_stats = df_player_stats.map(lambda x: x.lower() if isinstance(x, str) else x)

# Clean up numeric columns
numeric_cols = ['Barrel %', 'ExitVelocity', 'LaunchAngle', 'HardHit%', 'K%', 'BB%', 
                'XBA', 'XSLG', 'XWOBA', 'WOBA', 'XWOBACON', 'LA Sweet-Spot %', 'Barrel/PA']

# Replace '--' and other non-numeric values with NaN
for col in numeric_cols:
    if col in df_player_stats.columns:
        df_player_stats[col] = pd.to_numeric(df_player_stats[col], errors='coerce')

# Extract player id from slug
df_player_stats['player_id'] = df_player_stats['Player Slug'].apply(lambda x: x.split('-')[-1] if isinstance(x, str) else None)

# Create mapping from player name to id
player_to_id = {}
for slug in df_player_stats['Player Slug'].unique():
    if isinstance(slug, str):
        name_part = '-'.join(slug.split('-')[:-1])
        player_id = slug.split('-')[-1]
        player_name = ' '.join(word.capitalize() for word in name_part.split('-'))
        player_to_id[player_name] = player_id

# ---- Header ---- #
st.markdown("<h1 style='text-align: center;'>MLB AI Player Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6c757d; font-style: italic;'>Advanced Baseball Analytics at Your Fingertips</p>", unsafe_allow_html=True)

# ---- Player Selection ---- #
st.sidebar.markdown("## Player Selection")
player_names = sorted([name for name in player_to_id.keys() if name])
selected_player = st.sidebar.selectbox("Select a Player", player_names, index=player_names.index("Mookie Betts") if "Mookie Betts" in player_names else 0)
selected_id = player_to_id.get(selected_player)

# Filter data for selected player
player_stats = df_player_stats[df_player_stats['player_id'] == selected_id]
player_stats = player_stats.sort_values('Season')

# Get player general info by matching the player slug in the stats data
player_slug = player_stats['Player Slug'].iloc[0] if not player_stats.empty else None
player_name_parts = selected_player.lower().split() if selected_player else []
player_info = None

# Try to find the player in the general info dataframe
for _, row in df_player_general.iterrows():
    name = str(row['Player Name']).lower()
    if all(part in name for part in player_name_parts):
        player_info = row
        break

# Dashboard Layout
if player_info is not None and not player_stats.empty:
    # Main content area
    cols = st.columns([2, 3])
    
    # Player Profile
    with cols[0]:
        st.markdown(f"## {selected_player}")
        st.markdown(f"""
        #### Player Info
        - **Position:** {player_info['Position']}
        - **Bats/Throws:** {player_info['Bats/Throws']}
        - **Height:** {player_info['Height']}
        - **Weight:** {player_info['Weight']}
        - **Age:** {player_info['Age']}
        """)
        
        # Career Summary
        st.markdown("#### Career Averages")
        # Filter out future projections
        current_year = 2024  # Using 2024 as the current year
        historical_stats = player_stats[player_stats['Season'] <= current_year]
        
        # Safely calculate career averages, handling missing data
        career_avg = {}
        for metric in numeric_cols:
            if metric in historical_stats.columns:
                # Use nanmean to handle NaN values
                career_avg[metric] = historical_stats[metric].mean()
        
        # Format career averages as a nice table
        career_df = pd.DataFrame([career_avg])
        st.dataframe(career_df.style.format({
            'Barrel %': '{:.1f}',
            'ExitVelocity': '{:.1f}',
            'LaunchAngle': '{:.1f}',
            'HardHit%': '{:.1f}',
            'XBA': '{:.3f}',
            'XSLG': '{:.3f}',
            'XWOBA': '{:.3f}',
            'K%': '{:.1f}',
            'BB%': '{:.1f}'
        }))
        
        # Radar Chart for Player Skills
        st.markdown("#### Player Skills Profile")
        
        # Calculate percentiles based on historical stats (non-projected)
        all_historical = df_player_stats[df_player_stats['Season'] <= current_year]
        percentiles = {}
        metrics = ['Barrel %', 'ExitVelocity', 'HardHit%', 'XBA', 'XSLG', 'XWOBA']
        labels = ['Barrel %', 'Exit Velo', 'Hard Hit%', 'xBA', 'xSLG', 'xwOBA']
        
        for metric in metrics:
            if metric in historical_stats.columns:
                player_value = historical_stats[metric].mean()
                # Group by player_id and calculate mean
                all_values = all_historical.groupby('player_id')[metric].mean()
                # Filter out NaN values
                all_values = all_values.dropna()
                if len(all_values) > 0 and not np.isnan(player_value):
                    percentile = (all_values < player_value).mean() * 100
                    percentiles[metric] = percentile if not np.isnan(percentile) else 50
                else:
                    percentiles[metric] = 50
        
        # Create radar chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=[percentiles.get(metric, 0) for metric in metrics],
            theta=labels,
            fill='toself',
            name=selected_player
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title="Percentile Rankings (vs. MLB)"
        )
        
        st.plotly_chart(fig)
    
    # Performance Trends
    with cols[1]:
        st.markdown("## Performance Trends")
        
        # Season Stats
        st.markdown("#### Yearly Statistics")
        display_cols = ['Season', 'Barrel %', 'ExitVelocity', 'LaunchAngle', 'HardHit%', 'XBA', 'XSLG', 'XWOBA', 'K%', 'BB%']
        # Make sure all columns exist
        available_cols = ['Season'] + [col for col in display_cols[1:] if col in player_stats.columns]
        display_player_stats = player_stats[available_cols].copy()
        
        # Add highlight for projected seasons
        def highlight_projected(s):
            try:
                is_projected = s['Season'] > current_year
                return ['background-color: #ffffcc' if is_projected else '' for _ in s]
            except:
                return ['' for _ in s]  # Return empty styling if error
        
        st.dataframe(display_player_stats.style.apply(highlight_projected, axis=1).format({
            'Barrel %': '{:.1f}',
            'ExitVelocity': '{:.1f}',
            'LaunchAngle': '{:.1f}',
            'HardHit%': '{:.1f}',
            'XBA': '{:.3f}',
            'XSLG': '{:.3f}',
            'XWOBA': '{:.3f}',
            'K%': '{:.1f}',
            'BB%': '{:.1f}'
        }))
        
        # Key Metrics Trends
        st.markdown("#### Key Metrics Over Time")
        
        fig = make_subplots(rows=2, cols=2, 
                            subplot_titles=("Contact Quality", "Expected Stats", 
                                           "Plate Discipline", "Power Metrics"))
        
        # Contact Quality
        if 'ExitVelocity' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['ExitVelocity'], 
                        name="Exit Velocity", mode='lines+markers'),
                row=1, col=1
            )
        if 'LaunchAngle' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['LaunchAngle'], 
                        name="Launch Angle", mode='lines+markers'),
                row=1, col=1
            )
        
        # Expected Stats
        if 'XBA' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['XBA'], 
                        name="xBA", mode='lines+markers'),
                row=1, col=2
            )
        if 'XSLG' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['XSLG'], 
                        name="xSLG", mode='lines+markers'),
                row=1, col=2
            )
        if 'XWOBA' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['XWOBA'], 
                        name="xwOBA", mode='lines+markers'),
                row=1, col=2
            )
        
        # Plate Discipline
        if 'K%' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['K%'], 
                        name="K%", mode='lines+markers'),
                row=2, col=1
            )
        if 'BB%' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['BB%'], 
                        name="BB%", mode='lines+markers'),
                row=2, col=1
            )
        
        # Power Metrics
        if 'Barrel %' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['Barrel %'], 
                        name="Barrel %", mode='lines+markers'),
                row=2, col=2
            )
        if 'HardHit%' in player_stats.columns:
            fig.add_trace(
                go.Scatter(x=player_stats['Season'], y=player_stats['HardHit%'], 
                        name="Hard Hit %", mode='lines+markers'),
                row=2, col=2
            )
        
        # Add a vertical line for current year
        for row in [1, 2]:
            for col in [1, 2]:
                fig.add_vline(x=current_year, line_width=1, line_dash="dash", line_color="red",
                             row=row, col=col)
        
        fig.update_layout(height=800, width=800, showlegend=True)
        st.plotly_chart(fig)

    # Additional Analysis Section
    st.markdown("## Advanced Analysis")
    tabs = st.tabs(["Performance Breakdown", "Projections", "Hitting Zones"])
    
    with tabs[0]:
        # Performance breakdown by year
        st.markdown("### Performance by Season")
        
        # Comparing actual vs expected stats
        if 'WOBA' in player_stats.columns and 'XWOBA' in player_stats.columns:
            comp_fig = go.Figure()
            
            # WOBA vs xWOBA
            comp_fig.add_trace(
                go.Bar(x=player_stats['Season'], y=player_stats['WOBA'], name="WOBA")
            )
            comp_fig.add_trace(
                go.Bar(x=player_stats['Season'], y=player_stats['XWOBA'], name="xWOBA")
            )
            
            comp_fig.update_layout(
                title="Actual vs Expected Performance",
                barmode='group',
                xaxis_title="Season",
                yaxis_title="Value"
            )
            
            st.plotly_chart(comp_fig)
        
        # Sweet spot analysis if data exists
        if 'LA Sweet-Spot %' in player_stats.columns and not player_stats['LA Sweet-Spot %'].isna().all():
            st.markdown("### Sweet Spot Analysis")
            
            sweet_fig = px.line(
                player_stats, x='Season', y='LA Sweet-Spot %', 
                title=f"{selected_player}'s Sweet Spot Percentage by Season"
            )
            sweet_fig.update_traces(mode='lines+markers')
            
            # Add MLB average sweet spot percentage (around 33%)
            sweet_fig.add_hline(y=33, line_dash="dash", line_color="gray", 
                               annotation_text="MLB Average", annotation_position="top right")
            
            st.plotly_chart(sweet_fig)
    
    with tabs[1]:
        # Projections for future seasons
        st.markdown("### Future Projections")
        
        if current_year < player_stats['Season'].max():
            projected_stats = player_stats[player_stats['Season'] > current_year]
            
            # Create a line chart showing key projected metrics
            proj_fig = go.Figure()
            
            # Include both historical and projected
            for metric, color in [('XBA', 'blue'), ('XSLG', 'red'), ('XWOBA', 'green')]:
                if metric in player_stats.columns:
                    # Historical
                    hist_data = player_stats[player_stats['Season'] <= current_year]
                    if not hist_data[metric].isna().all():
                        proj_fig.add_trace(
                            go.Scatter(
                                x=hist_data['Season'], 
                                y=hist_data[metric],
                                name=f"{metric} (Actual)",
                                line=dict(color=color)
                            )
                        )
                    
                    # Projected
                    if not projected_stats[metric].isna().all():
                        proj_fig.add_trace(
                            go.Scatter(
                                x=projected_stats['Season'], 
                                y=projected_stats[metric],
                                name=f"{metric} (Projected)",
                                line=dict(color=color, dash='dash')
                            )
                        )
            
            proj_fig.add_vline(x=current_year, line_width=1, line_dash="dash", line_color="red",
                             annotation_text="Current Year", annotation_position="top right")
            
            proj_fig.update_layout(
                title="Performance Projections",
                xaxis_title="Season",
                yaxis_title="Value"
            )
            
            st.plotly_chart(proj_fig)
            
            # Show projected stats in a table
            st.markdown("### Projected Statistics")
            
            # Make sure all columns exist
            available_cols = ['Season'] + [col for col in display_cols[1:] if col in projected_stats.columns]
            proj_df = projected_stats[available_cols]
            
            st.dataframe(proj_df.style.format({
                'Barrel %': '{:.1f}',
                'ExitVelocity': '{:.1f}',
                'LaunchAngle': '{:.1f}',
                'HardHit%': '{:.1f}',
                'XBA': '{:.3f}',
                'XSLG': '{:.3f}',
                'XWOBA': '{:.3f}',
                'K%': '{:.1f}',
                'BB%': '{:.1f}'
            }))
        else:
            st.write("No future projections available for this player.")
    
    with tabs[2]:
        # Hitting zones/quality visualization
        st.markdown("### Hitting Quality by Launch Parameters")
        
        # Create a scatter plot of Exit Velocity vs Launch Angle
        # Filter out NaN values for the scatter plot
        scatter_data = player_stats.dropna(subset=['LaunchAngle', 'ExitVelocity', 'Barrel %', 'XWOBA'])
        
        if not scatter_data.empty:
            scatter_fig = px.scatter(
                scatter_data, 
                x='LaunchAngle', 
                y='ExitVelocity',
                size='Barrel %',
                color='XWOBA',
                hover_name='Season',
                size_max=20,
                color_continuous_scale=px.colors.sequential.Viridis,
                title=f"{selected_player}'s Contact Quality by Launch Parameters"
            )
            
            # Add optimal launch angle zone (8-32 degrees) and exit velocity (95+ mph)
            scatter_fig.add_vrect(x0=8, x1=32, fillcolor="gray", opacity=0.2, line_width=0)
            scatter_fig.add_hline(y=95, line_dash="dash", line_color="red")
            
            scatter_fig.update_layout(
                annotations=[
                    dict(
                        x=20, y=105,
                        text="Optimal Launch Zone",
                        showarrow=False
                    )
                ]
            )
            
            st.plotly_chart(scatter_fig)
            
            # Additional explanation
            st.markdown("""
            ### Hitting Zones Explained
            - **Barrel:** Perfect combination of exit velocity and launch angle
            - **Optimal Launch Angle:** 8-32 degrees (highlighted zone)
            - **Optimal Exit Velocity:** 95+ mph (above red line)
            - **Sweet Spot %:** Percentage of batted balls in the optimal launch angle range
            """)
        else:
            st.write("Not enough data to generate launch parameter visualization.")

else:
    st.error("Player data not found. Please select a different player.")

# Footer
st.sidebar.markdown("## Filters")
include_projections = st.sidebar.checkbox("Include Future Projections", value=True)
season_min = int(df_player_stats['Season'].min())
season_max = int(df_player_stats['Season'].max())
season_range = st.sidebar.slider("Season Range", 
                               min_value=season_min,
                               max_value=season_max,
                               value=(season_min, season_max))

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("""
This dashboard provides advanced batting analytics for MLB players based on 
Statcast and expected metrics. Data includes actual statistics through 2024 
and projections for 2025.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("###### Created By Tyler Durette")
st.sidebar.markdown("MLB AI © 2024 | [GitHub](https://github.com/bestisblessed)")
