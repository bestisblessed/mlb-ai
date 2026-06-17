import mlbstatsapi
import statsapi
import csv
import os
import re
from collections import defaultdict
import datetime
import concurrent.futures
import time
import random

mlb = mlbstatsapi.Mlb()
today = datetime.date.today().strftime("%Y-%m-%d")
data_dir = f"data/{today}"
os.makedirs(data_dir, exist_ok=True)
matchups_file = f"{data_dir}/matchups.csv"

MAX_RETRIES = 5
BASE_DELAY = 2
MAX_DELAY = 60

def safe_filename(s):
    return re.sub(r'[^A-Za-z0-9_]', '', s.replace(' ', '_'))

def get_player_splits_with_retry(batter_id, pitcher_id):
    """Get yearly Batter-vs-Pitcher splits with exponential backoff retry logic."""
    hydrate = (
        "stats(group=[hitting],"
        f"type=[vsPlayer],opposingPlayerId={int(pitcher_id)},sportId=1)"
    )
    for attempt in range(MAX_RETRIES):
        try:
            data = statsapi.get("person", {"personId": int(batter_id), "hydrate": hydrate})
            people = data.get("people") or []
            stats = people[0].get("stats") if people else []
            return (stats[0].get("splits") if stats else []) or []
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                print(f"Attempt {attempt + 1} failed for batter {batter_id} vs pitcher {pitcher_id}: {e}")
                print(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                continue
            print(f"Failed to fetch stats for batter {batter_id} vs pitcher {pitcher_id} after {MAX_RETRIES} attempts: {e}")
            return []

games = defaultdict(list)
with open(matchups_file, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = (row['Team'], row['Pitcher'], row['PitcherID'])
        games[key].append(row)

summary = []
for (team, pitcher, pitcher_id), matchups in games.items():
    all_rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(
            lambda row: (
                row,
                get_player_splits_with_retry(row['BatterID'], row['PitcherID'])
                if row['BatterID'].isdigit() and row['PitcherID'].isdigit() else []
            ),
            matchups
        ))
        for row, splits in results:
            if not splits:
                print(f"No splits found for batter {row['Batter']} vs pitcher {pitcher}")
                continue
            for split in splits:
                stat = split.get('stat') or {}
                rowdata = {k.lower(): v for k, v in stat.items() if v not in (None, '', 0, '-.--')}
                rowdata['year'] = split.get('season') or ''
                rowdata['batter'] = row['Batter']
                rowdata['batter_id'] = int(row['BatterID'])
                rowdata['pitcher'] = pitcher
                rowdata['pitcher_id'] = int(pitcher_id)
                all_rows.append(rowdata)
    if all_rows:
        all_keys = set()
        for r in all_rows:
            all_keys.update(r.keys())
        all_keys = sorted(all_keys)
        fname = f"{data_dir}/bvp_{safe_filename(team)}_vs_{safe_filename(pitcher)}.csv".lower()
        with open(fname, 'w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=all_keys)
            writer.writeheader()
            for r in all_rows:
                writer.writerow({k: r.get(k, '') for k in all_keys})
        print(f"Saved: {fname}")
        summary.append(fname)

print(f"\nDone. {len(summary)} game-level CSVs written.")
print(f"Processed {len(games)} pitcher matchups total.") 
