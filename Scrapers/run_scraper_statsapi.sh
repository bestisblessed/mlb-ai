#!/bin/bash

set -e

echo "Fetching pitcher game logs …"
python3 statsapi_pitcher_game_logs.py

echo "Fetching batter game logs …"
python3 statsapi_batter_game_logs.py

echo "All done." 