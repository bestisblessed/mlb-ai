#!/bin/bash

set -e

#for YEAR in {2010..2024}; do
for YEAR in {2020..2025}; do
  echo "Fetching team game logs for $YEAR..."
  python statsapi_team_game_logs_loop.py $YEAR

  echo "Fetching pitcher game logs for $YEAR..."
  python statsapi_pitcher_game_logs_loop.py $YEAR

  echo "Fetching batter game logs for $YEAR..."
  python statsapi_batter_game_logs_loop.py $YEAR

  echo "Fetching player season stats for $YEAR..."
  python statsapi_player_season_stats_loop.py $YEAR

done

echo "Done."
