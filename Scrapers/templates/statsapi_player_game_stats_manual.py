'''
Endpoint: person_stats
URL: https://statsapi.mlb.com/api/{ver}/people/{personId}/stats/game/{gamePk}
'''

import requests
import pandas as pd
import sys

if len(sys.argv) != 3:
    print("Usage: python statsapi_person_game_stats.py <personId> <gamePk>")
    sys.exit(1)

personId = sys.argv[1]
gamePk = sys.argv[2]

url = f"https://statsapi.mlb.com/api/v1/people/{personId}/stats/game/{gamePk}"
response = requests.get(url)
data = response.json()

# Flatten all data under the root
# The structure may vary, so we try to flatten the whole response
try:
    df = pd.json_normalize(data, sep='_', max_level=None)
except Exception:
    # If the root is not a list, try to flatten the 'stats' key if present
    if 'stats' in data:
        df = pd.json_normalize(data['stats'], sep='_', max_level=None)
    else:
        df = pd.DataFrame([data])

outfile = f"person_{personId}_game_{gamePk}_stats.csv"
df.to_csv(outfile, index=False)
print(f"Saved {len(df)} rows with {len(df.columns)} columns")
print("Columns:", df.columns.tolist()) 