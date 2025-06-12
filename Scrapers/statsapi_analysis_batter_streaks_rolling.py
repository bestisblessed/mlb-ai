import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load batter game logs (sample a few players for speed)
gamelogs = pd.read_csv('data/2024/batters_gamelogs_2024_statsapi.csv')

# Pick a few well-known players (by name or ID)
# You can change these names/IDs as desired
star_players = ['Aaron Judge', 'Juan Soto', 'Shohei Ohtani', 'Mookie Betts']

# If player name is not available, use player_id and map to names from details file
if 'fullName' in gamelogs.columns:
    gamelogs['Player'] = gamelogs['fullName']
else:
    details = pd.read_csv('data/2024/batters_details_2024_statsapi.csv')
    id_to_name = dict(zip(details['player_id'], details['fullName']))
    gamelogs['Player'] = gamelogs['player_id'].map(id_to_name)

# Filter for star players
gamelogs = gamelogs[gamelogs['Player'].isin(star_players)]

# Ensure date is datetime
gamelogs['date'] = pd.to_datetime(gamelogs['date'], errors='coerce')

# Sort for rolling
players = gamelogs['Player'].unique()
for player in players:
    df = gamelogs[gamelogs['Player'] == player].sort_values('date')
    df['Hits_rolling7'] = df['hits'].rolling(7, min_periods=1).mean()
    df['HR_rolling7'] = df['homeRuns'].rolling(7, min_periods=1).mean()
    plt.figure(figsize=(12, 5))
    plt.plot(df['date'], df['Hits_rolling7'], label='7-game avg Hits')
    plt.plot(df['date'], df['HR_rolling7'], label='7-game avg HR')
    plt.title(f'{player} - 7-game Rolling Averages (2024)')
    plt.xlabel('Date')
    plt.ylabel('Rolling Average')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{player.replace(" ", "_")}_rolling_avgs.png')
    plt.show() 