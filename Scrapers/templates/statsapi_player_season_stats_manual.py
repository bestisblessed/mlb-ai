'''
Endpoint: person_stats
URL: https://statsapi.mlb.com/api/{ver}/people/{personId}/stats
'''

import requests
import pandas as pd
import sys

if len(sys.argv) != 3:
    print("Usage: python statsapi_person_season_stats.py <personId> <season>")
    sys.exit(1)

personId = sys.argv[1]
season = sys.argv[2]

url = f"https://statsapi.mlb.com/api/v1/people/{personId}/stats"
params = {'stats': 'season', 'season': season}
response = requests.get(url, params=params)
data = response.json()

# Try to flatten the 'stats' key if present
if 'stats' in data:
    df = pd.json_normalize(data['stats'], sep='_', max_level=None)
else:
    df = pd.DataFrame([data])

outfile = f"person_{personId}_season_{season}_stats.csv"
df.to_csv(outfile, index=False)
print(f"Saved {len(df)} rows with {len(df.columns)} columns")
print("Columns:", df.columns.tolist()) 