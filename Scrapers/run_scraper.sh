#!/bin/bash
# To run the script at 6:30 AM every day, add this line to your crontab:
# 30 6 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

cd /home/trinity/mlb-ai/Scrapers
echo "$(date): Starting script execution" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
# source .env
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1
echo "$(date): Script execution completed" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1


# source /home/trinity/.bashrc  # or .bashrc depending on your setup
# cd /home/trinity/mlb-ai/Scrapers
# /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
# # /home/trinity/.pyenv/versions/3.12.0/bin/python ballparkpal_signin_auto.py >> scraper.log 2>&1

