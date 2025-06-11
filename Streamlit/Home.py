import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# ---------------------------------------------------------------------------
# Helper : parse BallparkPal matchups.csv into a dict
# ---------------------------------------------------------------------------
def _parse_matchup_row(raw: str):
    """Parse a single raw line from matchups.csv into a dict."""
    parts = [p.strip() for p in raw.split(',')]
    if not parts or parts[0] in ("Team", ""):
        return {}

    side = parts[0]
    # Drop empty placeholders at the start
    rest = [p for p in parts[1:] if p]
    if len(rest) < 5:
        return {}

    # First non-empty is Batter name
    batter = rest[0]
    # Next numeric is BatterID, then AtBats
    numeric_idx = next((i for i, p in enumerate(rest[1:], 1) if p.lstrip('-').isdigit()), None)
    if numeric_idx is None or numeric_idx + 1 >= len(rest):
        return {}

    batter_id = rest[numeric_idx]
    at_bats = rest[numeric_idx + 1]

    # Everything after that until next numeric is pitcher name
    pitcher_tokens = []
    stats_start_idx = None
    for i in range(numeric_idx + 2, len(rest)):
        token = rest[i]
        if token.lstrip('-').isdigit():
            stats_start_idx = i
            break
        pitcher_tokens.append(token)

    if stats_start_idx is None or not pitcher_tokens:
        return {}

    pitcher = ' '.join(pitcher_tokens)
    # Remaining tokens are stats: RC, HR, XB, 1B, BB, K (may be fewer)
    stats = rest[stats_start_idx:]
    stat_keys = ["RC", "HR", "XB", "1B", "BB", "K"]
    stat_map = {k: (stats[i] if i < len(stats) else '') for i, k in enumerate(stat_keys)}

    return {
        "Side": side,
        "Batter": batter,
        "BatterID": batter_id,
        "AtBats": at_bats,
        "Pitcher": pitcher,
        **stat_map
    }

# -- DATA_DIR setup (unchanged) --
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Streamlit", "data"
)
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"

# -- Page config & title --
st.set_page_config(page_title="MLB AI",
                   page_icon="⚾", layout="wide")
st.title("MLB AI")

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
            st.markdown(
                f"<p style='margin-top:-10px; color:#8e8e8e; font-size:0.9rem;'>"
                f"Game ID: {game_id} · {date} · {game_time}</p>",
                unsafe_allow_html=True,
            )
            # ── Weather Summary (emojis) under header ─────────────────────────
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
                    # use wider padding around the dash separator
                    separator = " &nbsp;&nbsp;-&nbsp;&nbsp; "  # two non-breaking spaces on each side
                    weather_summary = separator.join(
                        f"{emoji_map[lbl]} _{lbl}_" for lbl in sorted_labels
                    )

                    # ── Build additional directional details inline ──
                    def _describe_direction_icon(icon_label: str):
                        """Convert direction SVG filenames into human-readable text."""
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

                    extra_details = [
                        _describe_direction_icon(lbl) for lbl in labels if lbl not in emoji_map
                    ]
                    extra_details = [d for d in extra_details if d]

                    combined_line = weather_summary
                    if extra_details:
                        extra_text = " • ".join(extra_details)
                        # add extra padding before the details block
                        combined_line += (
                            " &nbsp;&nbsp;&nbsp;&nbsp;"  # four NBSPs as gap
                            "<span style='color:#b8b8b8; font-size:0.85rem;'>"
                            + extra_text + "</span>"
                        )

                    # Use unsafe HTML to keep everything on one line
                    st.markdown(combined_line, unsafe_allow_html=True)
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

            # -------------------- NEW: load & prepare matchups --------------------
            matchups_df = None
            matchups_path = os.path.join(DATA_DIR, date, "matchups.csv")
            if os.path.exists(matchups_path):
                with open(matchups_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[1:]  # skip header
                recs = [_parse_matchup_row(l) for l in lines]
                recs = [r for r in recs if r]
                if recs:
                    matchups_df = pd.DataFrame(recs)
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

                pdf_display = pdf.copy()
                pdf_display["Player_Link"] = pdf_display["Player URL"]
                cols = [
                    "Pitcher", "Player_Link", "DK", "FD",
                    "Inn", "K", "BB", "H", "R", "W", "QS"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        "Player_Link": st.column_config.LinkColumn(
                            label="",
                            display_text="🔗",
                            width=30
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
                    "Batter", "Player_Link", "PA", "FD", "DK",
                    "H", "R", "RBI", "BB", "K", "1B", "2B",
                    "3B", "HR", "SB"
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
                        width=30  # Set column width to tiny
                        )
                    }
                )

        # -------------------- Matchups vs Home Starter --------------------
        if matchups_df is not None and starter_home_last:
            vs_df = matchups_df[matchups_df["Pitcher"] == starter_home_last]
            if not vs_df.empty:
                st.caption(f"Matchups vs {starter_home} (BETA)")
                # Display columns (drop the misleading 'AtBats' and rename batting side)
                disp_cols = ["Batter", "Side", "RC", "HR", "XB", "1B", "BB", "K"]
                vs_disp = vs_df[disp_cols].copy()
                num_cols = vs_disp.select_dtypes(include=[object]).columns.difference(["Batter", "Side"])
                vs_disp[num_cols] = vs_disp[num_cols].apply(pd.to_numeric, errors="coerce")
                vs_disp[num_cols] = vs_disp[num_cols].round(2)
                vs_disp = vs_disp.rename(columns={"Side": "L/R"})
                st.dataframe(vs_disp, hide_index=True)

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
                    "Pitcher", "Player_Link", "DK", "FD",
                    "Inn", "K", "BB", "H", "R", "W", "QS"
                ]
                pdf_display = pdf_display[cols]

                st.dataframe(
                    pdf_display,
                    hide_index=True,
                    column_config={
                        "Player_Link": st.column_config.LinkColumn(
                            label="",
                            display_text="🔗",
                            width=30
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
                    "Batter", "Player_Link", "PA", "FD", "DK",
                    "H", "R", "RBI", "BB", "K", "1B", "2B",
                    "3B", "HR", "SB"
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
                        width=30  # Set column width to tiny
                        )
                    }
                )

        # -------------------- Matchups vs Away Starter --------------------
        if matchups_df is not None and starter_away_last:
            vs_df = matchups_df[matchups_df["Pitcher"] == starter_away_last]
            if not vs_df.empty:
                st.caption(f"Matchups vs {starter_away} (BETA)")
                # Display columns (drop the misleading 'AtBats' and rename batting side)
                disp_cols = ["Batter", "Side", "RC", "HR", "XB", "1B", "BB", "K"]
                vs_disp = vs_df[disp_cols].copy()
                num_cols = vs_disp.select_dtypes(include=[object]).columns.difference(["Batter", "Side"])
                vs_disp[num_cols] = vs_disp[num_cols].apply(pd.to_numeric, errors="coerce")
                vs_disp[num_cols] = vs_disp[num_cols].round(2)
                vs_disp = vs_disp.rename(columns={"Side": "L/R"})
                st.dataframe(vs_disp, hide_index=True)

else:
    st.info("Please select a date and game from the sidebar to view projections.")

# -- Sidebar footer --
st.sidebar.markdown("---")
st.sidebar.markdown(
    "MLB AI © 2025 | [GitHub]"
    "(https://github.com/bestisblessed) | By Tyler Durette"
)
