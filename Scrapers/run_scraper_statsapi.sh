#!/bin/bash

set -e

echo "Fetching team game logs..."
python statsapi_team_game_logs.py

echo "Fetching pitcher game logs …"
python statsapi_pitcher_game_logs.py

echo "Fetching batter game logs …"
python statsapi_batter_game_logs.py

echo "Done."