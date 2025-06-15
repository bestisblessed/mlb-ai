import mlbstatsapi
import csv
import os
import re
from collections import defaultdict
import datetime
import concurrent.futures

mlb = mlbstatsapi.Mlb()
today = datetime.date.today().strftime("%Y-%m-%d")
data_dir = f"data/{today}"
os.makedirs(data_dir, exist_ok=True)
matchups_file = f"{data_dir}/matchups.csv"

def safe_filename(s):
    return re.sub(r'[^A-Za-z0-9_]', '', s.replace(' ', '_'))

games = defaultdict(list)
with open(matchups_file, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        key = (row['Team'], row['Pitcher'], row['PitcherID'])
        games[key].append(row)

summary = []
for (team, pitcher, pitcher_id), matchups in games.items():
    all_rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(
            lambda row: (
                row,
                mlb.get_player_stats(
                    int(row['BatterID']),
                    stats=['vsPlayer'],
                    groups=['hitting'],
                    opposingPlayerId=int(row['PitcherID'])
                ) if row['BatterID'].isdigit() and row['PitcherID'].isdigit() else None
            ),
            matchups
        ))
        for row, stats in results:
            if not stats or 'hitting' not in stats or 'vsplayer' not in stats['hitting']:
                continue
            vs = stats['hitting']['vsplayer']
            if vs and vs.splits:
                for split in vs.splits:
                    rowdata = {k: v for k, v in split.stat.__dict__.items() if v not in (None, '', 0, '-.--')}
                    year = getattr(split, 'season', '') or getattr(split, 'seasonyear', '')
                    rowdata['year'] = year
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