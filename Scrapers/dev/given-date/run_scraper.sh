#!/bin/bash
# To run the script at 12:01 AM every day, add this line to your crontab:
# 1 0 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

# Only cd if running on trinity
if [ "$(hostname)" = "trinity" ]; then
  cd /home/trinity/mlb-ai/Scrapers
fi

# Parse -d flag for date
DATE_ARG=""
SKIP_DATA_SYNC=0
while getopts ":d:" opt; do
  case $opt in
    d)
      if [ -z "$OPTARG" ]; then
        read -p "Enter date to scrape (YYYY-MM-DD): " USER_DATE
        DATE_ARG="-d $USER_DATE"
      else
        DATE_ARG="-d $OPTARG"
      fi
      SKIP_DATA_SYNC=1
      ;;
    :)
      # Missing argument for -d
      read -p "Enter date to scrape (YYYY-MM-DD): " USER_DATE
      DATE_ARG="-d $USER_DATE"
      SKIP_DATA_SYNC=1
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

# Set PYTHON_CMD and XVFB_CMD based on host
if [ "$(hostname)" = "trinity" ]; then
  PYTHON_CMD="/home/trinity/.pyenv/shims/python"
  XVFB_CMD="xvfb-run"
else
  PYTHON_CMD="python"
  XVFB_CMD=""
fi

# ===========================
# Run the main BallparkPal scraper
# ===========================
$XVFB_CMD $PYTHON_CMD ballparkpal_headless.py $DATE_ARG >> scraper.log 2>&1

# ===========================
# Run the BallparkPal park factors icons scraper
# ===========================
$XVFB_CMD $PYTHON_CMD ballparkpal_park_factors.py $DATE_ARG >> scraper.log 2>&1

# ===========================
# Run the pitching alt lines scraper
# ===========================
$XVFB_CMD $PYTHON_CMD ballparkpal_pitching_alt_lines.py $DATE_ARG >> scraper.log 2>&1

# ===========================
# Run the bovada alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_game_urls.py $DATE_ARG >> scraper.log 2>&1
#xvfb-run /home/trinity/.pyenv/shims/python bovada_scrape_pitcher_props.py $DATE_ARG >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD bovada_scrape_game_urls_playwright.py $DATE_ARG >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD bovada_scrape_pitcher_props_playwright.py $DATE_ARG >> scraper.log 2>&1

# ===========================
# Run the fanduel alt lines scraper
# ===========================
#xvfb-run /home/trinity/.pyenv/shims/python fanduel_scrape_pitcher_props_theoddsapi_working.py $DATE_ARG >> scraper.log 2>&1

# ===========================
# Run the MLB StatsAPI scrapers
# ===========================
echo "Fetching team game logs..." >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD statsapi_team_game_logs.py $DATE_ARG >> scraper.log 2>&1
echo "Fetching pitcher game logs …" >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD statsapi_pitcher_game_logs.py $DATE_ARG >> scraper.log 2>&1
echo "Fetching batter game logs …" >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD statsapi_batter_game_logs.py $DATE_ARG >> scraper.log 2>&1
echo "Fetching all player season stats …" >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD statsapi_player_season_stats.py $DATE_ARG >> scraper.log 2>&1
echo "Fetching bvp matchup stats …" >> scraper.log 2>&1
$XVFB_CMD $PYTHON_CMD statsapi_bvp_matchup_stats.py $DATE_ARG >> scraper.log 2>&1
echo "Done." >> scraper.log 2>&1

# ===========================
# Update the data repository
# ===========================
if [ $SKIP_DATA_SYNC -eq 0 ]; then
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
fi

# # Check if the last run had an error (looking for specific error messages)
# if grep -q "AttributeError: 'NoneType' object has no attribute 'find_all'" "scraper.log"; then
#     echo "$(date): Found login error in previous run, running signin script first" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
#     # Run the signin script
#     xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
#     # Wait a bit after signin
#     sleep 5
# fi