#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

LOG_FILE="scraper.log"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

PUSH_TO_GITHUB="n"
if [ -t 0 ]; then
    read -r -p "Push/update GitHub with the scraped files? [y/N] " PUSH_TO_GITHUB
    echo
fi

case "$PUSH_TO_GITHUB" in
    [yY]|[yY][eE][sS])
        PUSH_TO_GITHUB="y"
        ;;
    *)
        PUSH_TO_GITHUB="n"
        ;;
esac

# ===========================
# Refresh the BallparkPal session if needed
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_signin_auto.py

# ===========================
# Run the main BallparkPal scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_headless.py

# ===========================
# Run the BallparkPal park factors icons scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_park_factors.py

# ===========================
# Run the pitching alt lines scraper
# ===========================
/Users/td/.pyenv/shims/python ballparkpal_pitching_alt_lines.py

# ===========================
# Run the bovada alt lines scraper
# ===========================
#python bovada_scrape_game_urls.py
#python bovada_scrape_pitcher_props.py
/Users/td/.pyenv/shims/python bovada_scrape_game_urls_playwright.py
/Users/td/.pyenv/shims/python bovada_scrape_pitcher_props_playwright.py

# ===========================
# Run the fanduel alt lines scraper
# ===========================
#python fanduel_scrape_pitcher_props_theoddsapi_working.py

# ===========================
# Run the MLB StatsAPI scrapers
# ===========================
echo "Fetching team game logs..."
/Users/td/.pyenv/shims/python statsapi_team_game_logs.py
echo "Fetching pitcher game logs …"
/Users/td/.pyenv/shims/python statsapi_pitcher_game_logs.py
echo "Fetching batter game logs …"
/Users/td/.pyenv/shims/python statsapi_batter_game_logs.py
echo "Fetching all player season stats …"
/Users/td/.pyenv/shims/python statsapi_player_season_stats.py
echo "Fetching bvp matchup stats …"
/Users/td/.pyenv/shims/python statsapi_bvp_matchup_stats.py
echo "Done."

# ===========================
# Update the data repository
# ===========================
rm -rf data/raw
if [ "$PUSH_TO_GITHUB" = "y" ]; then
    git pull
    git add -f data/20*
    git commit -m "Data update $(date +%Y-%m-%d)"
    git push
    echo "$(date): Data updated"
else
    echo "$(date): GitHub update skipped for scraper data"
fi

# ===========================
# Sync data to Streamlit app
# ===========================
cp -r data/20* ../Streamlit/data/
if [ "$PUSH_TO_GITHUB" = "y" ]; then
    git add -f ../Streamlit/data/20*
    git commit -m "Data update streamlit $(date +%Y-%m-%d)"
    git push
    echo "$(date): Data updated streamlit"
else
    echo "$(date): Streamlit data copied locally; GitHub update skipped"
fi
echo "---------------------------------------"
echo "---------------------------------------"
echo "---------------------------------------"
