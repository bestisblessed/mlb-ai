#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

# ===========================
# Run the main BallparkPal scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1

# ===========================
# Run the BallparkPal park factors icons scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_park_factors.py >> scraper.log 2>&1

# ===========================
# Run the pitching alt lines scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_pitching_alt_lines.py >> scraper.log 2>&1

# ===========================
# Run the bovada alt lines scraper
# ===========================
#python bovada_scrape_game_urls.py
#python bovada_scrape_pitcher_props.py
/Users/td/.pyenv/shims/python bovada_scrape_game_urls_playwright.py >> scraper.log 2>&1
/Users/td/.pyenv/shims/python bovada_scrape_pitcher_props_playwright.py >> scraper.log 2>&1

# ===========================
# Run the fanduel alt lines scraper
# ===========================
#python fanduel_scrape_pitcher_props_theoddsapi_working.py

# ===========================
# Run the MLB StatsAPI scrapers
# ===========================
echo "Fetching team game logs..."
/Users/td/.pyenv/shims/python statsapi_team_game_logs.py >> scraper.log 2>&1
echo "Fetching pitcher game logs …"
/Users/td/.pyenv/shims/python statsapi_pitcher_game_logs.py >> scraper.log 2>&1
echo "Fetching batter game logs …"
/Users/td/.pyenv/shims/python statsapi_batter_game_logs.py >> scraper.log 2>&1
echo "Fetching all player season stats …"
/Users/td/.pyenv/shims/python statsapi_player_season_stats.py >> scraper.log 2>&1
echo "Fetching bvp matchup stats …"
/Users/td/.pyenv/shims/python statsapi_bvp_matchup_stats.py >> scraper.log 2>&1
echo "Done."

# ===========================
# Update the data repository
# ===========================
rm -rf data/raw
git pull >> scraper.log 2>&1
git add -f data/20*
git commit -m "Data update $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated" >> scraper.log 2>&1

# ===========================
# Sync data to Streamlit app
# ===========================
cp -r data/20* ../Streamlit/data/
git add -f ../Streamlit/data/20*
git commit -m "Data update streamlit $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated streamlit" >> scraper.log 2>&1
echo "---------------------------------------" >> scraper.log 2>&1
echo "---------------------------------------" >> scraper.log 2>&1
echo "---------------------------------------" >> scraper.log 2>&1