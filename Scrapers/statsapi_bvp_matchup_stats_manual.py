import mlbstatsapi
import csv

mlb = mlbstatsapi.Mlb()
batter = mlb.get_people_id('Ty France')[0]
pitcher = mlb.get_people_id('Shohei Ohtani')[0]
stats = mlb.get_player_stats(batter, stats=['vsPlayer'], groups=['hitting'], opposingPlayerId=pitcher)
vs = stats['hitting']['vsplayer']

rows = []
if vs and vs.splits:
    for split in vs.splits:
        row = {k: v for k, v in split.stat.__dict__.items() if v not in (None, '', 0, '-.--')}
        year = getattr(split, 'season', '') or getattr(split, 'seasonyear', '')
        row['year'] = year
        rows.append(row)

if rows:
    all_keys = set()
    for row in rows:
        all_keys.update(row.keys())
    all_keys = sorted(all_keys)
    with open('bvp_tyfrance_vs_ohtani.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in all_keys})
    print("Saved to bvp_tyfrance_vs_ohtani.csv")
else:
    print('No BvP data found.') 