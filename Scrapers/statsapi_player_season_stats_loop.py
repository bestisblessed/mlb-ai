import requests
import pandas as pd
import os
import sys

if len(sys.argv) > 1:
    YEAR = int(sys.argv[1])
else:
    YEAR = 2025

print(f"Processing year {YEAR}...")
BATTERS_FILE = f'data/{YEAR}/batters_details_{YEAR}_statsapi.csv'
PITCHERS_FILE = f'data/{YEAR}/pitchers_details_{YEAR}_statsapi.csv'
SEASON = str(YEAR)

batters_stats = []
pitchers_stats = []

def fetch_stats(personId):
    url = f"https://statsapi.mlb.com/api/v1/people/{personId}/stats"
    params = {'stats': 'season', 'season': SEASON}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if 'stats' in data and data['stats']:
            return pd.json_normalize(data['stats'], sep='_', max_level=None)
    except Exception as e:
        print(f"Error for {personId} in {YEAR}: {e}")
    return None

if os.path.exists(BATTERS_FILE):
    print(f"Fetching batters' season stats for {YEAR}...")
    batters_df = pd.read_csv(BATTERS_FILE)
    for personId in batters_df['id']:
        stats_df = fetch_stats(personId)
        if stats_df is not None and not stats_df.empty:
            batters_stats.append(stats_df)
            print(f"Added batter {personId} for {YEAR}")
        else:
            print(f"No stats for batter {personId} in {YEAR}")
    if batters_stats:
        all_batters = pd.concat(batters_stats, ignore_index=True)
        all_batters.to_csv(f'data/{YEAR}/batters_season_{YEAR}_stats.csv', index=False)
        print(f"Saved data/{YEAR}/batters_season_{YEAR}_stats.csv")
    else:
        print(f"No batter stats found for {YEAR}.")
else:
    print(f"{BATTERS_FILE} not found, skipping batters for {YEAR}.")

if os.path.exists(PITCHERS_FILE):
    print(f"Fetching pitchers' season stats for {YEAR}...")
    pitchers_df = pd.read_csv(PITCHERS_FILE)
    for personId in pitchers_df['id']:
        stats_df = fetch_stats(personId)
        if stats_df is not None and not stats_df.empty:
            pitchers_stats.append(stats_df)
            print(f"Added pitcher {personId} for {YEAR}")
        else:
            print(f"No stats for pitcher {personId} in {YEAR}")
    if pitchers_stats:
        all_pitchers = pd.concat(pitchers_stats, ignore_index=True)
        all_pitchers.to_csv(f'data/{YEAR}/pitchers_season_{YEAR}_stats.csv', index=False)
        print(f"Saved data/{YEAR}/pitchers_season_{YEAR}_stats.csv")
    else:
        print(f"No pitcher stats found for {YEAR}.")
else:
    print(f"{PITCHERS_FILE} not found, skipping pitchers for {YEAR}.") 