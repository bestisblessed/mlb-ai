#!/bin/bash

set -e

START_YEAR="${1:-2020}"
END_YEAR="${2:-$(date +%Y)}"

for YEAR in $(seq "$START_YEAR" "$END_YEAR"); do
  echo "Fetching team game logs for $YEAR..."
  python statsapi_team_game_logs_loop.py $YEAR

  echo "Fetching pitcher game logs for $YEAR..."
  python statsapi_pitcher_game_logs_loop.py $YEAR

  echo "Fetching batter game logs for $YEAR..."
  python statsapi_batter_game_logs_loop.py $YEAR

  echo "Fetching player season stats for $YEAR..."
  python statsapi_player_season_stats_loop.py $YEAR

done

echo "Done for seasons $START_YEAR through $END_YEAR."
