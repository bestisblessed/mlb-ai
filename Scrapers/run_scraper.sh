#!/bin/bash
# To run the script at 12:01 AM every day, add this line to your crontab:
# 1 0 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh

cd /home/trinity/mlb-ai/Scrapers

# # Check if the last run had an error (looking for specific error messages)
# if grep -q "AttributeError: 'NoneType' object has no attribute 'find_all'" "scraper.log"; then
#     echo "$(date): Found login error in previous run, running signin script first" >> /home/trinity/mlb-ai/Scrapers/scraper.log 2>&1
#     # Run the signin script
#     xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
#     # Wait a bit after signin
#     sleep 5
# fi

# Run the main scraper
echo "---------------------------------------" >> scraper.log 2>&1
#echo "$(date): Starting script execution" >> scraper.log 2>&1
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1
#echo "$(date): Script execution completed" >> scraper.log 2>&1
#echo "$(date): Removing data/raw directory" >> scraper.log 2>&1
rm -rf data/raw
git pull >> scraper.log 2>&1
git add data/
git commit -m "Data update $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated" >> scraper.log 2>&1

cp -r data/202* ../Streamlit/data/
git add -f ../Streamlit/data/
git commit -m "Data update streamlit $(date +%Y-%m-%d)" >> /dev/null 2>&1
git push >> /dev/null 2>&1
echo "$(date): Data updated streamlit" >> scraper.log 2>&1
echo "---------------------------------------" >> scraper.log 2>&1
# source /home/trinity/.bashrc  # or .bashrc depending on your setup
# cd /home/trinity/mlb-ai/Scrapers
# /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
# # /home/trinity/.pyenv/versions/3.12.0/bin/python ballparkpal_signin_auto.py >> scraper.log 2>&1

