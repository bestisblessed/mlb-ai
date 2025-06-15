import requests
import pandas as pd
import os

# Get raw schedule data
response = requests.get("https://statsapi.mlb.com/api/v1/schedule", params={'sportId': 1, 'season': 2025})
data = response.json()

# Extract and fully flatten all game data
games = [game for date in data['dates'] for game in date['games']]
df = pd.json_normalize(games, sep='_', max_level=None)
df.to_csv('2025_mlb_schedule_full_columns.csv', index=False)
print(f"Saved {len(df)} games with {len(df.columns)} columns")
print("Columns:", df.columns.tolist())