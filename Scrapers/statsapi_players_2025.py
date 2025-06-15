import requests
import pandas as pd

# Use the /api/v1/sports/1/players endpoint to get all MLB players
url = "https://statsapi.mlb.com/api/v1/sports/1/players"
response = requests.get(url)
data = response.json()

players = data.get('people', [])

df = pd.json_normalize(players, sep='_', max_level=None)
df.to_csv('all_mlb_players_2025.csv', index=False)
print(f"Saved {len(df)} players to all_mlb_players_2025.csv") 