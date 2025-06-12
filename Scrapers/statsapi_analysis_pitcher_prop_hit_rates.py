import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load pitcher game logs
gamelogs = pd.read_csv('data/2024/pitchers_gamelogs_2024_statsapi.csv', low_memory=False)

# If player name is not available, use player_id and map to names from details file
if 'fullName' in gamelogs.columns:
    gamelogs['Pitcher'] = gamelogs['fullName']
else:
    details = pd.read_csv('data/2024/pitchers_details_2024_statsapi.csv')
    id_to_name = dict(zip(details['player_id'], details['fullName']))
    gamelogs['Pitcher'] = gamelogs['player_id'].map(id_to_name)

# Calculate outs from IP if not present
def ip_to_outs(ip):
    if pd.isnull(ip):
        return 0
    try:
        ip = float(ip)
        return int(ip) * 3 + round((ip - int(ip)) * 10)
    except:
        return 0
if 'outs' not in gamelogs.columns:
    gamelogs['outs'] = gamelogs['inningsPitched'].apply(ip_to_outs)

# Group by pitcher and calculate prop hit rates
def prop_rate(df, col, thresh, leq=False):
    if leq:
        return (df[col] <= thresh).sum() / len(df) if len(df) > 0 else 0
    else:
        return (df[col] >= thresh).sum() / len(df) if len(df) > 0 else 0

props = []
for pitcher, df in gamelogs.groupby('Pitcher'):
    props.append({
        'Pitcher': pitcher,
        'Games': len(df),
        'Pct_5plus_K': prop_rate(df, 'strikeOuts', 5),
        'Pct_6plus_K': prop_rate(df, 'strikeOuts', 6),
        'Pct_18plus_Outs': prop_rate(df, 'outs', 18),
        'Pct_2orFewer_ER': prop_rate(df, 'earnedRuns', 2, leq=True),
    })
props_df = pd.DataFrame(props)

# Only keep pitchers with a reasonable number of games (e.g., >= 10)
props_df = props_df[props_df['Games'] >= 10]

# Plot top/bottom 10 for each prop
for col, label in [
    ('Pct_5plus_K', '5+ Strikeouts'),
    ('Pct_6plus_K', '6+ Strikeouts'),
    ('Pct_18plus_Outs', '18+ Outs (6+ IP)'),
    ('Pct_2orFewer_ER', '2 or Fewer Earned Runs'),
]:
    plt.figure(figsize=(10, 6))
    top = props_df.sort_values(col, ascending=False).head(10)
    sns.barplot(data=top, x=col, y='Pitcher', hue='Pitcher', palette='crest', legend=False)
    plt.title(f'Top 10 Pitchers: % of Games with {label}')
    plt.xlabel(f'% of Games with {label}')
    plt.tight_layout()
    plt.savefig(f'top10_{col}.png')
    plt.show()

    plt.figure(figsize=(10, 6))
    bottom = props_df.sort_values(col, ascending=True).head(10)
    sns.barplot(data=bottom, x=col, y='Pitcher', hue='Pitcher', palette='flare', legend=False)
    plt.title(f'Bottom 10 Pitchers: % of Games with {label}')
    plt.xlabel(f'% of Games with {label}')
    plt.tight_layout()
    plt.savefig(f'bottom10_{col}.png')
    plt.show() 