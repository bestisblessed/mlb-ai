#!/bin/bash

set -e

YEAR="${1:-${YEAR:-$(date +%Y)}}"

echo "Fetching team game logs..."
python statsapi_team_game_logs_loop.py "$YEAR"

echo "Fetching pitcher game logs …"
python statsapi_pitcher_game_logs_loop.py "$YEAR"

echo "Fetching batter game logs …"
python statsapi_batter_game_logs_loop.py "$YEAR"

echo "Fetching all player season stats …"
python statsapi_player_season_stats_loop.py "$YEAR"

echo "Done for season $YEAR."
