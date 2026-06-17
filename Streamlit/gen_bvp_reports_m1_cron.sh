#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SCRAPER_LOG="$SCRIPT_DIR/../Scrapers/scraper.log"
cd "$SCRIPT_DIR"

DATE_STR="${1:-$(date +%Y-%m-%d)}"
PYTHON="${MLB_AI_PYTHON:-$HOME/.pyenv/shims/python}"

export PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/Users/pablo/Code/mlb-ai/.playwright-browsers}"
DRY_RUN="${DRY_RUN:-0}"
PUSH_TO_GITHUB="${PUSH_TO_GITHUB:-y}"

log() { echo "$@" | tee -a "$SCRAPER_LOG"; }
run() {
  if [ "$DRY_RUN" = "1" ]; then
    printf 'DRY RUN:' | tee -a "$SCRAPER_LOG"
    printf ' %q' "$@" | tee -a "$SCRAPER_LOG"
    printf '\n' | tee -a "$SCRAPER_LOG"
  else
    "$@" 2>&1 | tee -a "$SCRAPER_LOG"
  fi
}

check_runtime() {
  "$PYTHON" - <<'PY'
import importlib.util
import sys

modules = ["matplotlib", "numpy", "pandas", "statsapi"]
missing = [module for module in modules if importlib.util.find_spec(module) is None]
if missing:
    print("Missing Python modules: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
print("Runtime import check passed")
PY
}

log "BvP reports env: python=$PYTHON date=$DATE_STR dry_run=$DRY_RUN push=$PUSH_TO_GITHUB"
check_runtime

if [ "$DRY_RUN" = "1" ]; then
  run git pull --ff-only
else
  git pull --ff-only >> /dev/null 2>&1
fi

log "=== Generating BvP Edges for Dashboard ==="
run "$PYTHON" "$SCRIPT_DIR/scripts/scrape_bvp_today.py" --workers 4 "$DATE_STR"
run "$PYTHON" "$SCRIPT_DIR/scripts/rank_bvp_edges.py" "$DATE_STR"

log ""
log "=== Generating BvP Home Run Reports ==="
run "$PYTHON" "$SCRIPT_DIR/scripts/bvp_hr_reports.py" "$DATE_STR"

if [ "$PUSH_TO_GITHUB" = "y" ]; then
  run git add -f "data/${DATE_STR}/bvp/" "reports/"
  run git commit -m "BvP edge data update ${DATE_STR}"
  run git push
else
  log "$(date): GitHub update skipped for BvP reports"
fi
