#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
DATE_STR="${1:-$(date +%Y-%m-%d)}"

git pull >> /dev/null 2>&1

echo "=== Generating BvP Edges for Dashboard ==="
python "$SCRIPT_DIR/scripts/scrape_bvp_today.py" $DATE_STR
python "$SCRIPT_DIR/scripts/rank_bvp_edges.py" $DATE_STR

git add -f "data/${DATE_STR}/bvp/"
git commit -m "BvP edge data update ${DATE_STR}" >> /dev/null 2>&1
git push >> /dev/null 2>&1

echo ""
echo "=== Generating BvP Home Run Reports ==="
python "$SCRIPT_DIR/scripts/bvp_hr_reports.py" $DATE_STR

open "$SCRIPT_DIR/reports/report_top20_career_hr_${DATE_STR}.png"
open "$SCRIPT_DIR/reports/report_top20_hr_rate_${DATE_STR}.png"
