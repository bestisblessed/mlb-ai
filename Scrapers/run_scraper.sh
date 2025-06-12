#!/bin/bash
# To run the script at 12:01 AM every day, add this line to your crontab:
# 1 0 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

cd /home/trinity/mlb-ai/Scrapers

# ===========================
# Run the main BallparkPal scraper
# ===========================
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1

# ===========================
# Run the BallparkPal park factors icons scraper
# ===========================
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_park_factors.py >> scraper.log 2>&1

# ===========================
# Run the pitching alt lines scraper
# ===========================
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_pitching_alt_lines.py >> scraper.log 2>&1


# ===========================
# Run the bovada alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_game_urls.py >> scraper.log 2>&1
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_pitcher_props.py >> scraper.log 2>&1
xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_game_urls_playwright.py >> scraper.log 2>&1
xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_pitcher_props_playwright.py >> scraper.log 2>&1


# ===========================
# Run the fanduel alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python fanduel_scrape_pitcher_props_theoddsapi_working.py >> scraper.log 2>&1



# ===========================
# Update the data repository
# ===========================
rm -rf data/raw
git pull >> scraper.log 2>&1
git add -f data/202*
git commit -m "Data update $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated" >> scraper.log 2>&1


# ===========================
# Sync data to Streamlit app
# ===========================
cp -r data/202* ../Streamlit/data/
git add -f ../Streamlit/data/202*
git commit -m "Data update streamlit $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated streamlit" >> scraper.log 2>&1
echo "---------------------------------------" >> scraper.log 2>&1



# # Check if the last run had an error (looking for specific error messages)
# if grep -q "AttributeError: 'NoneType' object has no attribute 'find_all'" "scraper.log"; then
#     echo "$(date): Found login error in previous run, running signin script first" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
#     # Run the signin script
#     xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
#     # Wait a bit after signin
#     sleep 5
# fi