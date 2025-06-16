import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# ---------------------------------------------------------------------------
# Helpers to load season game logs
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading batter logs...")
def load_batter_logs(year: int) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, str(year), f"batters_gamelogs_{year}_statsapi.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data(show_spinner="Loading pitcher logs...")
def load_pitcher_logs(year: int) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, str(year), f"pitchers_gamelogs_{year}_statsapi.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Streamlit", "data"
)
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"
    
st.set_page_config(page_title="MLB AI",
                   page_icon="⚾", layout="wide")
#st.title("MLB AI")
st.markdown("<h1 style='text-align: center;'>MLB AI</h1>", unsafe_allow_html=True)  # Centering the title using HTML
#st.markdown("<h2 style='text-align: center;'>Your go-to source for MLB insights!</h2>", unsafe_allow_html=True)  # Subtitle
st.markdown("<hr>", unsafe_allow_html=True)  # Horizontal line for separation

# Add this CSS block once, before the scoreboard section (ideally near the top of your file, after st.set_page_config):
#st.markdown("""
#<style>
#/* Red progress bars for win probability */
#progress[value]::-webkit-progress-bar { background-color: #eee; border-radius: 5px; }
#progress[value]::-webkit-progress-value { background-color: #e53935; border-radius: 5px; }
#progress[value] { color: #e53935; }
#progress[value]::-moz-progress-bar { background-color: #e53935; }
#</style>
#""", unsafe_allow_html=True)

# -- Sidebar: date & game selectors --
st.sidebar.title("⚾️ MLB AI")

dates = sorted(
    (d for d in os.listdir(DATA_DIR)
     if re.match(r"\d{4}-\d{2}-\d{2}", d)),
    reverse=True
)
date = st.sidebar.selectbox("Select Date", dates)

# Add this mapping near the top of the file
TEAM_ABBR = {
    'arizona diamondbacks': 'ari',
    'atlanta braves': 'atl',
    'baltimore orioles': 'bal',
    'boston red sox': 'bos',
    'chicago cubs': 'chc',
    'chicago white sox': 'chw',
    'cincinnati reds': 'cin',
    'cleveland guardians': 'cle',
    'colorado rockies': 'col',
    'detroit tigers': 'det',
    'houston astros': 'hou',
    'kansas city royals': 'kc',
    'los angeles angels': 'laa',
    'los angeles dodgers': 'lad',
    'miami marlins': 'mia',
    'milwaukee brewers': 'mil',
    'minnesota twins': 'min',
    'new york mets': 'nym',
    'new york yankees': 'nyy',
    'oakland athletics': 'oak',
    'philadelphia phillies': 'phi',
    'pittsburgh pirates': 'pit',
    'san diego padres': 'sd',
    'san francisco giants': 'sf',
    'seattle mariners': 'sea',
    'st. louis cardinals': 'stl',
    'tampa bay rays': 'tb',
    'texas rangers': 'tex',
    'toronto blue jays': 'tor',
    'washington nationals': 'was',
}

if date:
    sim_path = os.path.join(DATA_DIR, date, "game_simulations.csv")
    detail_path = os.path.join(
        DATA_DIR, date, "game_simulations_per_game_tables.csv"
    )

    if os.path.exists(sim_path) and os.path.exists(detail_path):
        sim = pd.read_csv(sim_path)
        sim_detailed = pd.read_csv(detail_path)

        year = int(date.split('-')[0])
        bat_logs = load_batter_logs(year)
        pit_logs = load_pitcher_logs(year)

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

            # Build weather summary HTML before rendering the card
            weather_html = ''
            pf_path = os.path.join(DATA_DIR, date, "park_factors_icons.csv")
            if os.path.exists(pf_path):
                pf_df = pd.read_csv(pf_path, dtype={"game_id": int})
                pf_row = pf_df[pf_df["game_id"] == int(game_id)]
                if not pf_row.empty:
                    labels = [lbl.strip() for lbl in pf_row.iloc[0]["icon_labels"].split(",")]
                    emoji_map = {
                        "<60°F": "🥶",
                        "60–75°F": "🌤️",
                        "76–82°F": "🌞",
                        "83–89°F": "🥵",
                        "≥90°F": "🔥",
                        "Light Breeze": "🌬️",
                        "Moderate Wind": "💨",
                        "Heavy Wind": "🌪️",
                        "Roof Closed": "🏟️",
                        "Low Pressure": "🔽",
                        "High Pressure": "🔼",
                        "Low Humidity": "🏜️",
                        "High Humidity": "💦"
                    }
                    sorted_labels = sorted(
                        [lbl for lbl in labels if emoji_map.get(lbl)],
                        key=lambda lbl: 0 if lbl in {"<60°F", "60–75°F", "76–82°F", "83–89°F", "≥90°F"}
                                    else 1 if lbl in {"Light Breeze", "Moderate Wind", "Heavy Wind"}
                                    else 2
                    )
                    #separator = " &nbsp;&middot;&nbsp; "  # middle dot with spaces
                    separator = " &nbsp;&nbsp;-&nbsp;&nbsp; "
                    weather_summary = separator.join(
                        f"{emoji_map[lbl]} {lbl}" for lbl in sorted_labels
                    )
                    def _describe_direction_icon(icon_label: str):
                        base = icon_label.rsplit(".", 1)[0]
                        m = re.match(r"(Out|In|From)(.+)", base)
                        if not m:
                            return None
                        prefix, tail = m.groups()
                        tail_words = re.sub(r"([a-z])([A-Z])", r"\1 \2", tail)
                        tail_words = tail_words.replace(" Center", "-center").replace(" Middle", "-middle")
                        direction_text = tail_words.lower()
                        if prefix == "Out":
                            return f"wind out to {direction_text}"
                        if prefix == "In":
                            return f"wind in from {direction_text}"
                        if prefix == "From":
                            return f"wind from {direction_text}"
                        return None
                    extra_details = list(dict.fromkeys([
                        _describe_direction_icon(lbl) for lbl in labels if _describe_direction_icon(lbl) and lbl not in emoji_map
                    ]))
                    combined_line = f"<span style='font-size:0.85rem; color:black;'>{weather_summary}</span>"
                    if extra_details:
                        extra_text = " • ".join(extra_details)
                        combined_line += "<br>" + f"<span style='color:#b8b8b8; font-size:0.85rem;'>" + extra_text + "</span>"
                    weather_html = f"<div style='text-align:center; margin-top:8px;'>{combined_line}</div>"
            # Now render the card with weather_html included
            st.markdown(f"""
            <div style='background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px;'>
                <h2 style='text-align:center; margin:0 0 0px 0; line-height:1.1;'>{away_team} @ {home_team}</h2>
                <p style='text-align:center; color:#666; margin:0; font-size:0.85rem; line-height:1.1;'>{date} · {game_time} · Game ID: {game_id}</p>
                {weather_html}
            </div>
            """, unsafe_allow_html=True)
            #st.divider()
            st.write("")
            #st.write("")

            # --- Compact Scoreboard Style for Projected Runs and Win Probability ---
            away_abbr = TEAM_ABBR.get(away_team.lower(), away_team).upper()
            home_abbr = TEAM_ABBR.get(home_team.lower(), home_team).upper()
            away_runs = selected_game['away_score']
            home_runs = selected_game['home_score']
            win_away = detailed_row.get('win_away', '')
            win_home = detailed_row.get('win_home', '')
            # Extract win percentage values
            away_pct = float(re.search(r"(\d+\.\d+)%", win_away).group(1)) if re.search(r"(\d+\.\d+)%", win_away) else 50
            home_pct = float(re.search(r"(\d+\.\d+)%", win_home).group(1)) if re.search(r"(\d+\.\d+)%", win_home) else 50
            st.markdown(f"""
            <div style='display:flex; justify-content:center; align-items:center; margin-bottom:8px;'>
                <div style='flex:1; text-align:center;'>
                    <div style='font-size:3rem; font-weight:600;'>{away_abbr}</div>
                    <div style='height:10px;'></div>
                    <div style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:1.4em; font-weight:600; color:#222;'>{away_runs:.2f}</div>
                    <div style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:0.9rem; color:#3a3a3a;'>Projected Runs</div>
                </div>
                <div style='width:40px;'></div>
                <div style='flex:1; text-align:center;'>
                    <div style='font-size:3rem; font-weight:600;'>{home_abbr}</div>
                    <div style='height:10px;'></div>
                    <div style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:1.4em; font-weight:600; color:#222;'>{home_runs:.2f}</div>
                    <div style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:0.9rem; color:#3a3a3a;'>Projected Runs</div>
                    <br>
                </div>
            </div>
            <div style='display:flex; justify-content:center; align-items:center; margin-bottom:8px;'>
                <div style='flex:1; text-align:center;'>
                    <span style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:1.1rem; color:#3a3a3a;'>{win_away}</span>
                    <div style='height:7px; margin:2px 0 0 0;'><progress value='{away_pct}' max='100' style='width:80%; height:7px; background-color:green;'></progress></div>
                </div>
                <div style='width:40px;'></div>
                <div style='flex:1; text-align:center;'>
                    <span style='font-family: "Roboto Mono", "Oswald", monospace, sans-serif; font-size:1.1rem; color:#3a3a3a;'>{win_home}</span>
                    <div style='height:7px; margin:2px 0 0 0;'><progress value='{home_pct}' max='100' style='width:80%; height:7px; background-color:green;'></progress></div>
                </div>
            </div>
            <div style='height:28px;'></div>
            <br>
            <hr style='border: none; border-top: 1.5px solid #e0e0e0; margin: 0 0 18px 0;'>
            """, unsafe_allow_html=True)
            st.write("")

            # -------------------- NEW: load & prepare matchups --------------------
            matchups_df = None
            matchups_path = os.path.join(DATA_DIR, date, "matchups.csv")
            if os.path.exists(matchups_path):
                matchups_df = pd.read_csv(matchups_path)
            # grab starter names for filtering
            starter_away = detailed_row.get("starter_away", "")  # away pitcher full name
            starter_home = detailed_row.get("starter_home", "")  # home pitcher full name
            # extract last names for matchup filtering
            starter_away_last = starter_away.split()[-1] if isinstance(starter_away, str) and starter_away else ""
            starter_home_last = starter_home.split()[-1] if isinstance(starter_home, str) and starter_home else ""

    else:
        st.error(f"Simulation data not found for {date}")
        st.stop()

    # -- Main columns: Away vs Home projections --
    away_col, spacer, home_col = st.columns([1, 0.05, 1])  # 0.08 is a small spacer, adjust as needed

    # -- AWAY PROJECTIONS --
    with away_col:
        #st.subheader(away_team)

        # Starting Pitcher
        p1 = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_1.csv")
        if os.path.exists(p1):
            pdf = pd.read_csv(p1)
            if not pdf.empty:
                st.markdown("<h5 style='text-align:center;'>Starting Pitcher Projections</h5>", unsafe_allow_html=True)

                pdf_display = pdf.copy()
                pdf_display["Player_Link"] = pdf_display["Player URL"]
                cols = [
                    "Pitcher", "Inn", "K", "BB", "H", "R", "W", "QS", "Player_Link"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        "Player_Link": st.column_config.LinkColumn(
                            label="",
                            display_text="🔗",
                            width=9  # Make the link column very small,
                        )
                    },
                    use_container_width=True
                )

                for _, prow in pdf.iterrows():
                    pid = int(prow.get("Player ID", 0))
                    with st.expander("Last 10 Games"):
                        logs = pit_logs[pit_logs['player_id'] == pid]
                        if not logs.empty:
                            disp_cols = [
                                "date", "opponent", "inningsPitched",
                                "strikeOuts", "runs", "hits"
                            ]
                            disp_cols = [c for c in disp_cols if c in logs.columns]
                            st.dataframe(
                                logs.sort_values('date', ascending=False)
                                    .head(10)[disp_cols],
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.write("No game logs found.")
                    st.markdown("<br>", unsafe_allow_html=True)  # Ensure this is only after the dropdown

        # Batting Order
        b1 = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_1.csv")
        if os.path.exists(b1):
            bdf = pd.read_csv(b1)
            if not bdf.empty:
                st.markdown("<h5 style='text-align:center;'>Batting Projections</h5>", unsafe_allow_html=True)

                bdf_display = bdf.copy()
                bdf_display["Player_Link"] = bdf_display["Player URL"]
                cols = [
                    "Batter", "PA", "H", "RBI", "BB", "K", "1B", "2B",
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
                            display_text="🔗",
                            width=9  # Make the link column very small,
                        )
                    },
                    use_container_width=True
                )
                st.markdown("<br>", unsafe_allow_html=True)  # Add empty line after the table

        # -------------------- Matchups vs Home Starter --------------------
        if matchups_df is not None and starter_home_last:
            vs_df = matchups_df[matchups_df["Pitcher"] == starter_home_last]
            if not vs_df.empty:
                st.markdown("<h5 style='text-align:center;'>Batter Matchup Projections vs Starting Pitcher</h5>", unsafe_allow_html=True)
                # Display all relevant columns from matchups.csv
                disp_cols = ["Batter", "Team", "vs", "RC", "HR", "XB", "1B", "BB", "K"]
                vs_disp = vs_df[disp_cols].copy()
                num_cols = vs_disp.select_dtypes(include=[object]).columns.difference(["Batter", "Team", "Pitcher"])
                vs_disp[num_cols] = vs_disp[num_cols].apply(pd.to_numeric, errors="coerce")
                vs_disp[num_cols] = vs_disp[num_cols].round(2)
                vs_disp = vs_disp.rename(columns={"Team": "L/R"})
                st.dataframe(
                    vs_disp,
                    hide_index=True,
                    use_container_width=True
                )
                #st.markdown("<br>", unsafe_allow_html=True)  # Add empty line after the table

        # -------------------- Career BvP vs Home Starter (moved here) --------------------
        away_abbr = TEAM_ABBR.get(away_team.lower(), away_team).upper()
        bvp_file = os.path.join(DATA_DIR, date, f"bvp_{away_abbr}_vs_{starter_home_last.lower()}.csv")
        bvp_df = pd.read_csv(bvp_file) if os.path.exists(bvp_file) else None
        if os.path.exists(b1):
            bdf = pd.read_csv(b1)
            if not bdf.empty:
                for _, brow in bdf.iterrows():
                    batter = brow["Batter"]
                    batter_id = int(brow["Player ID"])
                    with st.expander(f"**{batter}** - Career BvP vs {starter_home} & Last 10 Games"):
                        # Career BvP first
                        st.markdown(f"**Career BvP vs {starter_home}**")
                        if bvp_df is not None:
                            batter_bvp = bvp_df[bvp_df["batter_id"] == batter_id]
                            if not batter_bvp.empty:
                                display_cols = [
                                    'atbats', 'avg', 'hits', 'homeruns', 'doubles', 'baseonballs', 'strikeouts', 'year'
                                ]
                                display_cols = [c for c in display_cols if c in batter_bvp.columns]
                                bvp_display = batter_bvp[display_cols].copy()
                                bvp_display = bvp_display.fillna(0).replace({None: 0})
                                if 'year' in bvp_display.columns:
                                    bvp_display['year'] = pd.to_numeric(bvp_display['year'], errors='coerce')
                                    bvp_display = bvp_display.sort_values(by='year', ascending=False)
                                    bvp_display['year'] = bvp_display['year'].astype('Int64').astype(str)
                                st.dataframe(
                                    bvp_display,
                                    hide_index=True,
                                    use_container_width=True
                                )
                                st.markdown("<br>", unsafe_allow_html=True)  # Add empty line after the table
                            else:
                                st.write("No career BvP data for this batter vs pitcher.")
                        else:
                            st.write("No career BvP data for this matchup.")

                        # Last 10 Games second
                        st.markdown("**Last 10 Games**")
                        logs = bat_logs[bat_logs['player_id'] == batter_id]
                        if not logs.empty:
                            disp_cols = [
                                "date", "opponent", "atBats", "hits",
                                "doubles", "triples", "homeRuns", "rbi", "runs",
                                "strikeOuts", "stolenBases", "caughtStealing",
                            ]
                            disp_cols = [c for c in disp_cols if c in logs.columns]
                            st.dataframe(
                                logs.sort_values('date', ascending=False).head(10)[disp_cols],
                                hide_index=True
                            )
                        else:
                            st.write("No game logs found.")

    # -- HOME PROJECTIONS --
    with home_col:
        #st.subheader(home_team)

        # Starting Pitcher
        p2 = os.path.join(DATA_DIR, date, game_id, "proj_box_pitchers_2.csv")
        if os.path.exists(p2):
            pdf = pd.read_csv(p2)
            if not pdf.empty:
                st.markdown("<h5 style='text-align:center;'>Starting Pitcher Projections</h5>", unsafe_allow_html=True)

                pdf_display = pdf.copy()
                pdf_display["Player_Link"] = pdf_display["Player URL"]
                cols = [
                    "Pitcher", "Inn", "K", "BB", "H", "R", "W", "QS", "Player_Link"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        "Player_Link": st.column_config.LinkColumn(
                            label="",
                            display_text="🔗",
                            width=9  # Make the link column very small,
                        )
                    },
                    use_container_width=True
                )

                for _, prow in pdf.iterrows():
                    pid = int(prow.get("Player ID", 0))
                    with st.expander("Last 10 Games"):
                        logs = pit_logs[pit_logs['player_id'] == pid]
                        if not logs.empty:
                            disp_cols = [
                                "date", "opponent", "inningsPitched",
                                "strikeOuts", "runs", "hits"
                            ]
                            disp_cols = [c for c in disp_cols if c in logs.columns]
                            st.dataframe(
                                logs.sort_values('date', ascending=False)
                                    .head(10)[disp_cols],
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.write("No game logs found.")
                    st.markdown("<br>", unsafe_allow_html=True)  # Ensure this is only after the dropdown

        # Batting Order
        b2 = os.path.join(DATA_DIR, date, game_id, "proj_box_batters_2.csv")
        if os.path.exists(b2):
            bdf = pd.read_csv(b2)
            if not bdf.empty:
                st.markdown("<h5 style='text-align:center;'>Batting Projections</h5>", unsafe_allow_html=True)

                bdf_display = bdf.copy()
                bdf_display["Player_Link"] = bdf_display["Player URL"]
                cols = [
                    "Batter", "PA", "H", "RBI", "BB", "K", "1B", "2B",
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
                            display_text="🔗",
                            width=9  # Make the link column very small,
                        )
                    },
                    use_container_width=True
                )
                st.markdown("<br>", unsafe_allow_html=True)  # Add empty line after the table

        # -------------------- Matchups vs Away Starter --------------------
        if matchups_df is not None and starter_away_last:
            vs_df = matchups_df[matchups_df["Pitcher"] == starter_away_last]
            if not vs_df.empty:
                st.markdown("<h5 style='text-align:center;'>Batter Matchup Projections vs Starting Pitcher</h5>", unsafe_allow_html=True)
                # Display all relevant columns from matchups.csv
                disp_cols = ["Batter", "Team", "vs", "RC", "HR", "XB", "1B", "BB", "K"]
                vs_disp = vs_df[disp_cols].copy()
                num_cols = vs_disp.select_dtypes(include=[object]).columns.difference(["Batter", "Team", "Pitcher"])
                vs_disp[num_cols] = vs_disp[num_cols].apply(pd.to_numeric, errors="coerce")
                vs_disp[num_cols] = vs_disp[num_cols].round(2)
                vs_disp = vs_disp.rename(columns={"Team": "L/R"})
                st.dataframe(vs_disp, hide_index=True, use_container_width=True)

        # -------------------- Career BvP vs Away Starter (moved here) --------------------
        home_abbr = TEAM_ABBR.get(home_team.lower(), home_team).upper()
        bvp_file = os.path.join(DATA_DIR, date, f"bvp_{home_abbr}_vs_{starter_away_last.lower()}.csv")
        bvp_df = pd.read_csv(bvp_file) if os.path.exists(bvp_file) else None
        if os.path.exists(b2):
            bdf = pd.read_csv(b2)
            if not bdf.empty:
                for _, brow in bdf.iterrows():
                    batter = brow["Batter"]
                    batter_id = int(brow["Player ID"])
                    with st.expander(f"**{batter}** - Career BvP vs {starter_away} & Last 10 Games"):
                        # Career BvP first
                        st.markdown(f"**Career BvP vs {starter_away}**")
                        if bvp_df is not None:
                            batter_bvp = bvp_df[bvp_df["batter_id"] == batter_id]
                            if not batter_bvp.empty:
                                display_cols = [
                                    'atbats', 'avg', 'hits', 'homeruns', 'doubles', 'baseonballs', 'strikeouts', 'year'
                                ]
                                display_cols = [c for c in display_cols if c in batter_bvp.columns]
                                bvp_display = batter_bvp[display_cols].copy()
                                bvp_display = bvp_display.fillna(0).replace({None: 0})
                                if 'year' in bvp_display.columns:
                                    bvp_display['year'] = pd.to_numeric(bvp_display['year'], errors='coerce')
                                    bvp_display = bvp_display.sort_values(by='year', ascending=False)
                                    bvp_display['year'] = bvp_display['year'].astype('Int64').astype(str)
                                st.dataframe(bvp_display, hide_index=True, use_container_width=True)
                            else:
                                st.write("No career BvP data for this batter vs pitcher.")
                        else:
                            st.write("No career BvP data for this matchup.")

                        # Last 10 Games second
                        st.markdown("**Last 10 Games**")
                        logs = bat_logs[bat_logs['player_id'] == batter_id]
                        if not logs.empty:
                            disp_cols = [
                                "date", "opponent", "atBats", "hits",
                                "doubles", "triples", "homeRuns", "rbi", "runs",
                                "strikeOuts", "stolenBases", "caughtStealing",
                            ]
                            disp_cols = [c for c in disp_cols if c in logs.columns]
                            st.dataframe(
                                logs.sort_values('date', ascending=False).head(10)[disp_cols],
                                hide_index=True
                            )
                        else:
                            st.write("No game logs found.")

else:
    st.info("Please select a date and game from the sidebar to view projections.")

# -- Sidebar footer --
st.sidebar.markdown("---")
st.sidebar.markdown(
    "MLB AI © 2025 | [GitHub]"
    "(https://github.com/bestisblessed) | By Tyler Durette"
)
