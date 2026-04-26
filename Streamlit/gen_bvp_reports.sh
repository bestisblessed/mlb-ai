#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRAPER_LOG="$SCRIPT_DIR/../Scrapers/scraper.log"
cd "$SCRIPT_DIR"
DATE_STR="${1:-$(date +%Y-%m-%d)}"

if [ -x "$HOME/.pyenv/shims/python" ]; then
    PYTHON="$HOME/.pyenv/shims/python"
else
    PYTHON=python
fi

git pull >> /dev/null 2>&1

echo "=== Generating BvP Edges for Dashboard ===" >> "$SCRAPER_LOG" 2>&1
"$PYTHON" "$SCRIPT_DIR/scripts/scrape_bvp_today.py" $DATE_STR >> "$SCRAPER_LOG" 2>&1
"$PYTHON" "$SCRIPT_DIR/scripts/rank_bvp_edges.py" $DATE_STR >> "$SCRAPER_LOG" 2>&1

if [ -t 0 ]; then
    read -p "Commit & push to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -f "data/${DATE_STR}/bvp/"
        git commit -m "BvP edge data update ${DATE_STR}" >> /dev/null 2>&1
        git push >> /dev/null 2>&1
    fi
else
    git add -f "data/${DATE_STR}/bvp/"
    git commit -m "BvP edge data update ${DATE_STR}" >> /dev/null 2>&1
    git push >> /dev/null 2>&1
fi

echo "" >> "$SCRAPER_LOG" 2>&1
echo "=== Generating BvP Home Run Reports ===" >> "$SCRAPER_LOG" 2>&1
"$PYTHON" "$SCRIPT_DIR/scripts/bvp_hr_reports.py" $DATE_STR >> "$SCRAPER_LOG" 2>&1

if [ "$(uname)" = "Darwin" ]; then
    open "$SCRIPT_DIR/reports/report_top20_career_hr_${DATE_STR}.png"
    open "$SCRIPT_DIR/reports/report_top20_hr_rate_${DATE_STR}.png"
fi
