import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load pitcher game logs
gamelogs = pd.read_csv('data/2024/pitchers_gamelogs_2024_statsapi.csv', low_memory=False)

# Select relevant numeric columns for correlation
cols = [
    'strikeOuts', 'baseOnBalls', 'earnedRuns', 'inningsPitched', 'hits', 'homeRuns',
    'runs', 'outs', 'numberOfPitches', 'battersFaced', 'rbi', 'gamesPitched', 'wins', 'losses', 'saves', 'blownSaves', 'holds', 'completeGames', 'shutouts', 'noDecisions'
]
# Only keep columns that exist in the file
cols = [c for c in cols if c in gamelogs.columns]

# Calculate outs from IP if not present
def ip_to_outs(ip):
    if pd.isnull(ip):
        return 0
    try:
        ip = float(ip)
        return int(ip) * 3 + round((ip - int(ip)) * 10)
    except:
        return 0
if 'outs' not in gamelogs.columns and 'inningsPitched' in gamelogs.columns:
    gamelogs['outs'] = gamelogs['inningsPitched'].apply(ip_to_outs)
    cols.append('outs')

# Compute correlation matrix
corr = gamelogs[cols].corr()

# Plot heatmap
plt.figure(figsize=(12, 10))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', square=True)
plt.title('Pitcher Stat Correlation Heatmap (2024)')
plt.tight_layout()
plt.savefig('pitcher_correlation_heatmap.png')
plt.show()

# Print top 5 most predictive (highest absolute correlation) stat pairs
corr_pairs = corr.abs().unstack().sort_values(ascending=False)
# Remove self-correlation
corr_pairs = corr_pairs[corr_pairs < 1]
# Drop duplicate pairs (since matrix is symmetric)
seen = set()
top_pairs = []
for (a, b), val in corr_pairs.items():
    if (b, a) not in seen:
        top_pairs.append(((a, b), val))
        seen.add((a, b))
    if len(top_pairs) == 5:
        break
print('Top 5 most predictive pitcher stat pairs (by absolute correlation):')
for (a, b), val in top_pairs:
    print(f'{a} <-> {b}: {val:.2f}') 