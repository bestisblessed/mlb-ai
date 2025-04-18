#!/bin/bash

cd /home/trinity/mlb-ai/Scrapers
# source .env
xvfb-run /home/trinity/.pyenv/shims/python ballparkpal_headless.py >> scraper.log 2>&1

# source /home/trinity/.bashrc  # or .bashrc depending on your setup
# cd /home/trinity/mlb-ai/Scrapers
# /home/trinity/.pyenv/shims/python ballparkpal_signin_auto.py >> scraper.log 2>&1
# # /home/trinity/.pyenv/versions/3.12.0/bin/python ballparkpal_signin_auto.py >> scraper.log 2>&1