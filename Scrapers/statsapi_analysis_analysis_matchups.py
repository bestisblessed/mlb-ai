import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

base_dir = Path('data')
dates = sorted([p.name for p in base_dir.glob('2025-*') if (p/'matchups.csv').exists()])
frames = []
for date in dates:
    csv_path = base_dir / f'{date}/matchups.csv'
    df = pd.read_csv(csv_path)
    df['date'] = date
    frames.append(df)

matchups = pd.concat(frames, ignore_index=True)

# Ensure numeric types for calculations
for col in ['AtBats', 'RC', 'HR', 'XB', '1B', 'BB', 'K']:
    matchups[col] = pd.to_numeric(matchups[col], errors='coerce')

# Add rate stats
matchups['RC_per_AB'] = matchups['RC'] / matchups['AtBats']
matchups['HR_per_AB'] = matchups['HR'] / matchups['AtBats']
matchups['BB_per_AB'] = matchups['BB'] / matchups['AtBats']
matchups['K_per_AB'] = matchups['K'] / matchups['AtBats']
matchups['XB_per_AB'] = matchups['XB'] / matchups['AtBats']
matchups['1B_per_AB'] = matchups['1B'] / matchups['AtBats']

# Minimum sample filtering: only keep batter-pitcher pairs with >=10 AB
MIN_AB = 10
pair_ab = matchups.groupby(['Batter', 'Pitcher'])['AtBats'].sum().reset_index()
pair_ab = pair_ab[pair_ab['AtBats'] >= MIN_AB]
filtered = matchups.merge(pair_ab, on=['Batter', 'Pitcher'], suffixes=('', '_total'))

# Contextual comparison: batter vs pitcher vs batter overall
batter_overall = filtered.groupby('Batter')[['RC', 'AtBats']].sum().reset_index()
batter_overall['batter_RC_per_AB'] = batter_overall['RC'] / batter_overall['AtBats']

pitcher_overall = filtered.groupby('Pitcher')[['RC', 'AtBats']].sum().reset_index()
pitcher_overall['pitcher_RC_per_AB'] = pitcher_overall['RC'] / pitcher_overall['AtBats']

# Aggregate by batter-pitcher pair
pair_stats = filtered.groupby(['Batter', 'Pitcher']).agg(
    pair_RC=('RC', 'sum'),
    pair_AB=('AtBats', 'sum'),
    pair_RC_per_AB=('RC_per_AB', 'mean')
).reset_index()

# Merge in overall stats
pair_stats = pair_stats.merge(batter_overall[['Batter', 'batter_RC_per_AB']], on='Batter')
pair_stats = pair_stats.merge(pitcher_overall[['Pitcher', 'pitcher_RC_per_AB']], on='Pitcher')

# Calculate over/under performance
pair_stats['batter_vs_pitcher_edge'] = pair_stats['pair_RC_per_AB'] - pair_stats['batter_RC_per_AB']
pair_stats['pitcher_vs_batter_edge'] = pair_stats['pair_RC_per_AB'] - pair_stats['pitcher_RC_per_AB']

print('Top batter over-performers vs specific pitchers (RC/AB above their own average):')
print(pair_stats.sort_values('batter_vs_pitcher_edge', ascending=False).head(20))

print('\nTop batter under-performers vs specific pitchers (RC/AB below their own average):')
print(pair_stats.sort_values('batter_vs_pitcher_edge', ascending=True).head(20))

print('\nTop pitcher over-performers vs specific batters (RC/AB allowed below their own average):')
print(pair_stats.sort_values('pitcher_vs_batter_edge', ascending=True).head(20))

print('\nTop pitcher under-performers vs specific batters (RC/AB allowed above their own average):')
print(pair_stats.sort_values('pitcher_vs_batter_edge', ascending=False).head(20))

# --- Visualization Section ---
# Bar plot: Top 10 batter over-performers
plt.figure(figsize=(10, 6))
top_batters = pair_stats.sort_values('batter_vs_pitcher_edge', ascending=False).head(10)
sns.barplot(
    data=top_batters,
    x='batter_vs_pitcher_edge',
    y=top_batters['Batter'] + ' vs ' + top_batters['Pitcher'],
    palette='crest'
)
plt.title('Top 10 Batter Over-Performers vs Pitchers (RC/AB above own avg)')
plt.xlabel('RC/AB Edge')
plt.ylabel('Batter vs Pitcher')
plt.tight_layout()
plt.savefig('top_batter_overperformers.png')
plt.show()

# Bar plot: Top 10 batter under-performers
plt.figure(figsize=(10, 6))
worst_batters = pair_stats.sort_values('batter_vs_pitcher_edge', ascending=True).head(10)
sns.barplot(
    data=worst_batters,
    x='batter_vs_pitcher_edge',
    y=worst_batters['Batter'] + ' vs ' + worst_batters['Pitcher'],
    palette='flare'
)
plt.title('Top 10 Batter Under-Performers vs Pitchers (RC/AB below own avg)')
plt.xlabel('RC/AB Edge')
plt.ylabel('Batter vs Pitcher')
plt.tight_layout()
plt.savefig('top_batter_underperformers.png')
plt.show()

# Bar plot: Top 10 pitcher over-performers (lowest RC/AB allowed vs own avg)
plt.figure(figsize=(10, 6))
top_pitchers = pair_stats.sort_values('pitcher_vs_batter_edge', ascending=True).head(10)
sns.barplot(
    data=top_pitchers,
    x='pitcher_vs_batter_edge',
    y=top_pitchers['Pitcher'] + ' vs ' + top_pitchers['Batter'],
    palette='crest'
)
plt.title('Top 10 Pitcher Over-Performers vs Batters (RC/AB allowed below own avg)')
plt.xlabel('RC/AB Edge')
plt.ylabel('Pitcher vs Batter')
plt.tight_layout()
plt.savefig('top_pitcher_overperformers.png')
plt.show()

# Bar plot: Top 10 pitcher under-performers (highest RC/AB allowed vs own avg)
plt.figure(figsize=(10, 6))
worst_pitchers = pair_stats.sort_values('pitcher_vs_batter_edge', ascending=False).head(10)
sns.barplot(
    data=worst_pitchers,
    x='pitcher_vs_batter_edge',
    y=worst_pitchers['Pitcher'] + ' vs ' + worst_pitchers['Batter'],
    palette='flare'
)
plt.title('Top 10 Pitcher Under-Performers vs Batters (RC/AB allowed above own avg)')
plt.xlabel('RC/AB Edge')
plt.ylabel('Pitcher vs Batter')
plt.tight_layout()
plt.savefig('top_pitcher_underperformers.png')
plt.show()

# Scatter plot: All batter-pitcher edges
plt.figure(figsize=(8, 6))
sns.scatterplot(
    data=pair_stats,
    x='batter_vs_pitcher_edge',
    y='pitcher_vs_batter_edge',
    size='pair_AB',
    hue='pair_AB',
    palette='viridis',
    legend=False,
    alpha=0.7
)
plt.axhline(0, color='gray', linestyle='--', linewidth=1)
plt.axvline(0, color='gray', linestyle='--', linewidth=1)
plt.title('Batter vs Pitcher Edge vs Pitcher vs Batter Edge')
plt.xlabel('Batter Edge (RC/AB vs own avg)')
plt.ylabel('Pitcher Edge (RC/AB allowed vs own avg)')
plt.tight_layout()
plt.savefig('batter_pitcher_edge_scatter.png')
plt.show()