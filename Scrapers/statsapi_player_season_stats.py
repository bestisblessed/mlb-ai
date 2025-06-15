import requests
import pandas as pd
import os

BATTERS_FILE = 'data/2025/batters_details_2025_statsapi.csv'
PITCHERS_FILE = 'data/2025/pitchers_details_2025_statsapi.csv'
SEASON = '2025'

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
        print(f"Error for {personId}: {e}")
    return None

print("Fetching batters' season stats...")
batters_df = pd.read_csv(BATTERS_FILE)
for personId in batters_df['id']:
    stats_df = fetch_stats(personId)
    if stats_df is not None and not stats_df.empty:
        batters_stats.append(stats_df)
        print(f"Added batter {personId}")
    else:
        print(f"No stats for batter {personId}")

if batters_stats:
    all_batters = pd.concat(batters_stats, ignore_index=True)
    all_batters.to_csv('batters_season_2025_stats.csv', index=False)
    print("Saved batters_season_2025_stats.csv")
else:
    print("No batter stats found.")

print("Fetching pitchers' season stats...")
pitchers_df = pd.read_csv(PITCHERS_FILE)
for personId in pitchers_df['id']:
    stats_df = fetch_stats(personId)
    if stats_df is not None and not stats_df.empty:
        pitchers_stats.append(stats_df)
        print(f"Added pitcher {personId}")
    else:
        print(f"No stats for pitcher {personId}")

if pitchers_stats:
    all_pitchers = pd.concat(pitchers_stats, ignore_index=True)
    all_pitchers.to_csv('pitchers_season_2025_stats.csv', index=False)
    print("Saved pitchers_season_2025_stats.csv")
else:
    print("No pitcher stats found.") 