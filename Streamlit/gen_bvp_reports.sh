#!/bin/bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRAPER_LOG="$SCRIPT_DIR/../Scrapers/scraper.log"
cd "$SCRIPT_DIR"
DATE_STR="${1:-$(date +%Y-%m-%d)}"

if [ -x "$HOME/.pyenv/shims/python" ]; then
    PYTHON="$HOME/.pyenv/shims/python"
else
    PYTHON=python
fi

log() { echo "$@" | tee -a "$SCRAPER_LOG"; }
run() { "$@" 2>&1 | tee -a "$SCRAPER_LOG"; }

git pull >> /dev/null 2>&1

log "=== Generating BvP Edges for Dashboard ==="
run "$PYTHON" "$SCRIPT_DIR/scripts/scrape_bvp_today.py" --workers 4 $DATE_STR
run "$PYTHON" "$SCRIPT_DIR/scripts/rank_bvp_edges.py" $DATE_STR

log ""
log "=== Generating BvP Home Run Reports ==="
run "$PYTHON" "$SCRIPT_DIR/scripts/bvp_hr_reports.py" $DATE_STR

if [ -t 0 ]; then
    read -p "Commit & push to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -f "data/${DATE_STR}/bvp/" "reports/"
        git commit -m "BvP edge data update ${DATE_STR}" >> /dev/null 2>&1
        git push >> /dev/null 2>&1
    fi
else
    git add -f "data/${DATE_STR}/bvp/" "reports/"
    git commit -m "BvP edge data update ${DATE_STR}" >> /dev/null 2>&1
    git push >> /dev/null 2>&1
fi

if [ "$(uname)" = "Darwin" ]; then
    open "$SCRIPT_DIR/reports/report_top20_career_hr_${DATE_STR}.png"
    open "$SCRIPT_DIR/reports/report_top20_hr_rate_${DATE_STR}.png"
fi
