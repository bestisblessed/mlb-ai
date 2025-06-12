import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load batter game logs
gamelogs = pd.read_csv('data/2024/batters_gamelogs_2024_statsapi.csv')

# If player name is not available, use player_id and map to names from details file
if 'fullName' in gamelogs.columns:
    gamelogs['Player'] = gamelogs['fullName']
else:
    details = pd.read_csv('data/2024/batters_details_2024_statsapi.csv')
    id_to_name = dict(zip(details['player_id'], details['fullName']))
    gamelogs['Player'] = gamelogs['player_id'].map(id_to_name)

# Group by player and calculate prop hit rates
def prop_rate(df, col, thresh):
    return (df[col] >= thresh).sum() / len(df) if len(df) > 0 else 0

props = []
for player, df in gamelogs.groupby('Player'):
    props.append({
        'Player': player,
        'Games': len(df),
        'Pct_1plus_Hit': prop_rate(df, 'hits', 1),
        'Pct_2plus_Hit': prop_rate(df, 'hits', 2),
        'Pct_1plus_HR': prop_rate(df, 'homeRuns', 1),
        'Pct_2plus_TB': prop_rate(df, 'totalBases', 2),
    })
props_df = pd.DataFrame(props)

# Only keep players with a reasonable number of games (e.g., >= 30)
props_df = props_df[props_df['Games'] >= 30]

# Plot top/bottom 10 for each prop
for col, label in [
    ('Pct_1plus_Hit', '1+ Hit'),
    ('Pct_2plus_Hit', '2+ Hits'),
    ('Pct_1plus_HR', '1+ HR'),
    ('Pct_2plus_TB', '2+ Total Bases'),
]:
    plt.figure(figsize=(10, 6))
    top = props_df.sort_values(col, ascending=False).head(10)
    sns.barplot(data=top, x=col, y='Player', hue='Player', palette='crest', legend=False)
    plt.title(f'Top 10 Players: % of Games with {label}')
    plt.xlabel(f'% of Games with {label}')
    plt.tight_layout()
    plt.savefig(f'top10_{col}.png')
    plt.show()

    plt.figure(figsize=(10, 6))
    bottom = props_df.sort_values(col, ascending=True).head(10)
    sns.barplot(data=bottom, x=col, y='Player', hue='Player', palette='flare', legend=False)
    plt.title(f'Bottom 10 Players: % of Games with {label}')
    plt.xlabel(f'% of Games with {label}')
    plt.tight_layout()
    plt.savefig(f'bottom10_{col}.png')
    plt.show()