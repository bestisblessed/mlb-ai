#!/bin/bash
# To run the script at 12:01 AM every day, add this line to your crontab:
# 1 0 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

set -e
#DD_METRIC_SUCCESS="mlb_scraper.success:1|g"
#DD_METRIC_FAILURE="mlb_scraper.failure:1|g"
#trap 'echo "$DD_METRIC_SUCCESS" | nc -u -w0 127.0.0.1 8125' EXIT

cd /home/trinity/mlb-ai/Scrapers
#export DISPLAY=:0

# ===========================
# Run the main BallparkPal scraper
# ===========================
/usr/bin/xvfb-run -a /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1

# ===========================
# Run the BallparkPal park factors icons scraper
# ===========================
/usr/bin/xvfb-run -a /home/trinity/.pyenv/shims/python ballparkpal_park_factors.py >> scraper.log 2>&1

# ===========================
# Run the pitching alt lines scraper
# ===========================
/usr/bin/xvfb-run -a /home/trinity/.pyenv/shims/python ballparkpal_pitching_alt_lines.py >> scraper.log 2>&1


# ===========================
# Run the bovada alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_game_urls.py >> scraper.log 2>&1
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_pitcher_props.py >> scraper.log 2>&1
/usr/bin/xvfb-run -a /home/trinity/.pyenv/shims/python bovada_scrape_game_urls_playwright.py >> scraper.log 2>&1
/usr/bin/xvfb-run -a /home/trinity/.pyenv/shims/python bovada_scrape_pitcher_props_playwright.py >> scraper.log 2>&1


# ===========================
# Run the fanduel alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python fanduel_scrape_pitcher_props_theoddsapi_working.py >> scraper.log 2>&1


# ===========================
# Run the MLB StatsAPI scrapers
# ===========================
echo "Fetching team game logs..." >> scraper.log 2>&1
/home/trinity/.pyenv/shims/python statsapi_team_game_logs.py >> scraper.log 2>&1
echo "Fetching pitcher game logs …" >> scraper.log 2>&1
/home/trinity/.pyenv/shims/python statsapi_pitcher_game_logs.py >> scraper.log 2>&1
echo "Fetching batter game logs …" >> scraper.log 2>&1
/home/trinity/.pyenv/shims/python statsapi_batter_game_logs.py >> scraper.log 2>&1
echo "Fetching all player season stats …" >> scraper.log 2>&1
/home/trinity/.pyenv/shims/python statsapi_player_season_stats.py >> scraper.log 2>&1
echo "Fetching bvp matchup stats …" >> scraper.log 2>&1
/home/trinity/.pyenv/shims/python statsapi_bvp_matchup_stats.py >> scraper.log 2>&1
echo "Done." >> scraper.log 2>&1


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


# # Check if the last run had an error (looking for specific error messages)
# if grep -q "AttributeError: 'NoneType' object has no attribute 'find_all'" "scraper.log"; then
#     echo "$(date): Found login error in previous run, running signin script first" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
#     # Run the signin script
#     xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
#     # Wait a bit after signin
#     sleep 5
# fi
#
#

trap 'echo "$DD_METRIC_FAILURE" | nc -u -w0 127.0.0.1 8125' ERR


