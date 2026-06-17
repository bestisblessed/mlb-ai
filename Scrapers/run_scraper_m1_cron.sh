#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"

LOG_FILE="${MLB_SCRAPER_LOG:-scraper.log}"
PYTHON="${MLB_AI_PYTHON:-$HOME/.pyenv/shims/python}"

export PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export BALLPARKPAL_HEADLESS="${BALLPARKPAL_HEADLESS:-1}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/Users/pablo/Code/mlb-ai/.playwright-browsers}"
DRY_RUN="${DRY_RUN:-0}"
PUSH_TO_GITHUB="${PUSH_TO_GITHUB:-y}"

touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

run() {
  if [ "$DRY_RUN" = "1" ]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

check_runtime() {
  "$PYTHON" - <<'PY'
import importlib.util
import sys

modules = [
    "bs4",
    "dotenv",
    "matplotlib",
    "mlbstatsapi",
    "nest_asyncio",
    "pandas",
    "playwright",
    "requests",
    "statsapi",
    "tqdm",
]
missing = [module for module in modules if importlib.util.find_spec(module) is None]
if missing:
    print("Missing Python modules: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
print("Runtime import check passed")
PY
}

echo "MLB scraper env: python=$PYTHON headless=$BALLPARKPAL_HEADLESS browsers=$PLAYWRIGHT_BROWSERS_PATH dry_run=$DRY_RUN push=$PUSH_TO_GITHUB"
check_runtime

if [ "$DRY_RUN" = "1" ]; then
  run git pull --ff-only
else
  git pull --ff-only
fi

run "$PYTHON" ballparkpal_signin_auto.py
run "$PYTHON" ballparkpal_headless.py
run "$PYTHON" ballparkpal_park_factors.py
run "$PYTHON" ballparkpal_pitching_alt_lines.py
run "$PYTHON" bovada_scrape_game_urls_playwright.py
run "$PYTHON" bovada_scrape_pitcher_props_playwright.py

echo "Fetching team game logs..."
run "$PYTHON" statsapi_team_game_logs.py
echo "Fetching pitcher game logs..."
run "$PYTHON" statsapi_pitcher_game_logs.py
echo "Fetching batter game logs..."
run "$PYTHON" statsapi_batter_game_logs.py
echo "Fetching all player season stats..."
run "$PYTHON" statsapi_player_season_stats.py
echo "Fetching bvp matchup stats..."
run "$PYTHON" statsapi_bvp_matchup_stats.py
echo "Done."

run rm -rf data/raw

if [ "$PUSH_TO_GITHUB" = "y" ]; then
  run git add -f data/20*
  run git commit -m "Data update $(date +%Y-%m-%d)"
  run git push
else
  echo "$(date): GitHub update skipped for scraper data"
fi

run cp -r data/20* ../Streamlit/data/

if [ "$PUSH_TO_GITHUB" = "y" ]; then
  run git add -f ../Streamlit/data/20*
  run git commit -m "Data update streamlit $(date +%Y-%m-%d)"
  run git push
else
  echo "$(date): Streamlit data copied locally; GitHub update skipped"
fi

echo "---------------------------------------"
echo "---------------------------------------"
echo "---------------------------------------"
