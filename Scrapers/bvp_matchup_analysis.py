import pandas as pd
from pathlib import Path

# Dates with clean matchup data
DATES = [
    '2025-04-25',
    '2025-04-26',
    '2025-04-27',
    '2025-04-28',
    '2025-04-29',
]

base_dir = Path('Scrapers/data')
frames = []
for date in DATES:
    csv_path = base_dir / f'{date}/matchups.csv'
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df['date'] = date
        frames.append(df)

# Combine all data
matchups = pd.concat(frames, ignore_index=True)

# Compute average run creation (RC) for each batter vs pitcher matchup
summary = (
    matchups.groupby(['Batter', 'Pitcher'])
    .agg(
        at_bats=('AtBats', 'sum'),
        mean_rc=('RC', 'mean'),
        mean_hr=('HR', 'mean'),
    )
    .reset_index()
)

# Show top matchups with highest mean RC
print('Top batter vs pitcher edges by Run Creation (RC)')
print(summary.sort_values('mean_rc', ascending=False).head(10))

# Show worst matchups
print('\nWorst batter vs pitcher edges by Run Creation (RC)')
print(summary.sort_values('mean_rc', ascending=True).head(10))
