#!/bin/bash
# To run the script at 12:01 AM every day, add this line to your crontab:
# 1 0 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

cd /home/trinity/mlb-ai/Scrapers
echo "$(date): Starting script execution" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
# source .env
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1
echo "$(date): Script execution completed" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
echo "$(date): Removing data/raw directory" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
rm -rf data/raw
git add data/
git commit -q -m "Data update $(date +%Y-%m-%d)" >> scraper.log 2>&1
git push >> scraper.log 2>&1
echo "$(date): Git push completed" >> scraper.log 2>&1


# source /home/trinity/.bashrc  # or .bashrc depending on your setup
# cd /home/trinity/mlb-ai/Scrapers
# /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
# # /home/trinity/.pyenv/versions/3.12.0/bin/python ballparkpal_signin_auto.py >> scraper.log 2>&1

