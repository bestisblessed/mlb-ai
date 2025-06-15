import requests
import pandas as pd
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
response = requests.get("https://statsapi.mlb.com/api/v1/schedule", params={'sportId': 1, 'date': today})
data = response.json()

if 'dates' in data and data['dates']:
    games = data['dates'][0]['games']
    df = pd.json_normalize(games, sep='_')
    df.to_csv(f'{today}_mlb_games.csv', index=False)
    print(f"Saved {len(games)} games for {today}")
else:
    print(f"No games found for {today}")