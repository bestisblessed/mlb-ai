import streamlit as st
import pandas as pd
import os
import re
from typing import List, Dict

# ------------------ Helper functions ------------------ #

def _get_data_dir() -> str:
    """Return absolute path to data directory (works in dev & prod)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "data")
    return d if os.path.exists(d) else "data"

def _parse_matchup_row(raw: str) -> Dict[str, str]:
    """Parse a single raw line from matchups.csv into a dict.

    The CSV from BallparkPal leaves several empty columns at the start,
    so we tokenise manually and stitch pieces together.  Schema returned:
        Side  : Batter handedness (R/L/S)
        Batter: Batter name
        Pitcher: Pitcher name
        AtBats, RC, HR, XB, 1B, BB, K — numbers where present (optional)
    """
    parts = [p.strip() for p in raw.split(',')]
    if not parts or parts[0] in ("Team", ""):
        return {}

    side = parts[0]

    # Drop empty placeholders
    rest = [p for p in parts[1:] if p]
    if len(rest) < 5:
        return {}

    batter = rest[0]
    # Look for first numeric segment (BatterID) & remove it
    numeric_idx = next((i for i, p in enumerate(rest[1:], 1) if p.lstrip('-').isdigit()), None)
    if numeric_idx is None or numeric_idx + 1 >= len(rest):
        return {}

    # Possible segments
    batter_id = rest[numeric_idx]
    at_bats   = rest[numeric_idx + 1]

    # Everything after that until next numeric is pitcher name
    pitcher_tokens: List[str] = []
    stats_start_idx = None
    for i in range(numeric_idx + 2, len(rest)):
        token = rest[i]
        if token.lstrip('-').isdigit():
            stats_start_idx = i
            break
        pitcher_tokens.append(token)

    if stats_start_idx is None or not pitcher_tokens:
        return {}

    pitcher    = ' '.join(pitcher_tokens)
    # Remaining numeric tokens are stats (may be fewer than 6)
    stats      = rest[stats_start_idx:]
    stat_keys  = ["RC", "HR", "XB", "1B", "BB", "K"]
    stat_map   = {k: (stats[i] if i < len(stats) else '') for i, k in enumerate(stat_keys)}

    return {
        "Side": side,
        "Batter": batter,
        "Pitcher": pitcher,
        "AtBats": at_bats,
        **stat_map
    }

# ------------------ Streamlit UI ------------------ #

st.set_page_config(page_title="Batter vs Pitcher", page_icon="⚔️", layout="wide")
st.title("🔍 Batter vs Pitcher Lookup")
st.divider()

DATA_DIR = _get_data_dir()
# Date selector
available_dates = sorted(
    (d for d in os.listdir(DATA_DIR) if re.match(r"\d{4}-\d{2}-\d{2}", d)),
    reverse=True
)
selected_date = st.sidebar.selectbox("Select Date", available_dates)

if not selected_date:
    st.info("Please choose a date from the sidebar.")
    st.stop()

# Game selector: mirror Home page
sim_path = os.path.join(DATA_DIR, selected_date, "game_simulations_per_game_tables.csv")
if not os.path.exists(sim_path):
    st.error(f"game_simulations_per_game_tables.csv not found for {selected_date}")
    st.stop()
sim = pd.read_csv(sim_path)
games = sim.apply(lambda r: f"{r['time']}pm - {r['away_team']} @ {r['home_team']}", axis=1).tolist()
game_idx = st.sidebar.selectbox("Select Game", range(len(games)), format_func=lambda i: games[i])
selected_game = sim.iloc[game_idx]
# extract only last names to match matchups.csv format
away_starter = selected_game["starter_away"].split()[-1]
home_starter = selected_game["starter_home"].split()[-1]

matchup_csv = os.path.join(DATA_DIR, selected_date, "matchups.csv")
if not os.path.exists(matchup_csv):
    st.error(f"matchups.csv not found for {selected_date}")
    st.stop()
# Search inputs
col1, col2 = st.columns(2)
batter_q  = col1.text_input("Batter name contains", "")
pitcher_q = col2.text_input("Pitcher name contains", "")
#st.divider()
st.write(" ")

records = []
with open(matchup_csv, "r", encoding="utf-8") as f:
    next(f)  # skip header
    for line in f:
        rec = _parse_matchup_row(line)
        if not rec:
            continue
        # only today's starters
        if rec["Pitcher"] not in (away_starter, home_starter):
            continue
        # apply name filters
        # if batter_q and batter_q.lower() not in rec["Batter"].lower():
        #     continue
        # if pitcher_q and pitcher_q.lower() not in rec["Pitcher"].lower():
        #     continue
        records.append(rec)

if not records:
    st.warning("No matchups found for the given criteria.")
    st.stop()

# build DataFrame from parsed records
df = pd.DataFrame(records)
for col in ["AtBats", "RC", "HR", "XB", "1B", "BB", "K"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Split by starting pitcher
away_df = df[df["Pitcher"] == away_starter].copy()
home_df = df[df["Pitcher"] == home_starter].copy()

# Sort by run component (RC) descending
if "RC" in away_df.columns:
    away_df = away_df.sort_values("RC", ascending=False)
if "RC" in home_df.columns:
    home_df = home_df.sort_values("RC", ascending=False)

# Display separate tables for each team
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"{selected_game['away_team']} batters vs {away_starter}")
    if not away_df.empty:
        # Visualize run component (RC) per batter
        try:
            st.bar_chart(away_df.set_index("Batter")["RC"])
        except Exception:
            pass
        st.dataframe(away_df.drop(columns=["Pitcher"]), hide_index=True)
    else:
        st.warning(f"No batters found against {away_starter}")
with col2:
    st.subheader(f"{selected_game['home_team']} batters vs {home_starter}")
    if not home_df.empty:
        # Visualize run component (RC) per batter
        try:
            st.bar_chart(home_df.set_index("Batter")["RC"])
        except Exception:
            pass
        st.dataframe(home_df.drop(columns=["Pitcher"]), hide_index=True)
    else:
        st.warning(f"No batters found against {home_starter}") 