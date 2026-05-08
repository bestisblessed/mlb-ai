#!/usr/bin/env bash

TODAY=$(date +%Y-%m-%d)
read -p "Enter date (${TODAY}): " INPUT_DATE
DATE="${INPUT_DATE:-$TODAY}"
echo ""
python Scrapers/statsapi_live_daily_hr_hitters.py --date "$DATE"
echo ""
