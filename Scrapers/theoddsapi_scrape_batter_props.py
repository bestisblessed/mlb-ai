import requests
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('THEODDSAPI_KEY')

def get_mlb_games():
    """Get and save today's MLB games"""
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us,us2,eu',
        'markets': 'h2h',
        'oddsFormat': 'american'
    }
    with requests.Session() as session:
        response = session.get(url, params=params, timeout=(3.05, 27))
    if response.status_code != 200:
        print(f"Error getting games: {response.status_code}")
        return []
    games = response.json()
    if games:
        game_df = pd.DataFrame(games)
        date_str = datetime.now().strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        game_filename = f"data/{date_str}/theoddsapi_game_links.csv"
        game_df.to_csv(game_filename, index=False)
        print(f"\nSaved game list to {game_filename}")
    else:
        print("No games found")
    return games

def get_batter_props(event_id):
    """Get batter home run and stolen base props for a specific game"""
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us,us2,eu',
        'markets': 'batter_home_runs,batter_stolen_bases',
        'oddsFormat': 'american',
        'bookmakers': 'betonlineag,fanduel,draftkings,bovada,hardrockbet,fliff,pinnacle,mybookieag'
    }
    with requests.Session() as session:
        response = session.get(url, params=params, timeout=(3.05, 27))
    if response.status_code != 200:
        print(f"Error getting batter props for game {event_id}: {response.status_code}")
        return None
    data = response.json()
    if not data or 'bookmakers' not in data or not data['bookmakers']:
        print(f"No batter props/bookmakers for game {event_id}")
    return data

def extract_batter_props(game_data, props_data):
    """Extract relevant batter prop data into list of dictionaries"""
    props_list = []
    if not props_data or 'bookmakers' not in props_data or not props_data['bookmakers']:
        return props_list
    game_time = datetime.fromisoformat(game_data['commence_time'].replace('Z', '+00:00'))
    home_team = game_data['home_team']
    away_team = game_data['away_team']
    for bookmaker in props_data['bookmakers']:
        for market in bookmaker['markets']:
            for outcome in market['outcomes']:
                props_list.append({
                    'game_time': game_time,
                    'home_team': home_team,
                    'away_team': away_team,
                    'player_name': outcome.get('description', outcome.get('name', '')),
                    'market': market['key'],
                    'line': outcome.get('point', ''),
                    'side': outcome.get('name', ''),
                    'price': outcome['price'],
                    'bookmaker': bookmaker['key']
                })
    return props_list

def main():
    all_props = []
    games = get_mlb_games()
    for game in games:
        print(f"Processing game: {game['home_team']} vs {game['away_team']} ({game['id']})")
        props = get_batter_props(game['id'])
        if props:
            props_data = extract_batter_props(game, props)
            all_props.extend(props_data)
        else:
            print(f"Skipped game {game['id']} due to error or no data")
        time.sleep(3)
        print()
    if all_props:
        df = pd.DataFrame(all_props)
        date_str = datetime.now().strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        filename = f"data/{date_str}/theoddsapi_batter_props_{date_str}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved batter props to {filename}\n")

        # Save home runs and stolen bases to separate files
        hr_df = df[df['market'] == 'batter_home_runs']
        sb_df = df[df['market'] == 'batter_stolen_bases']
        hr_filename = f"data/{date_str}/theoddsapi_batter_home_runs_{date_str}.csv"
        sb_filename = f"data/{date_str}/theoddsapi_batter_stolen_bases_{date_str}.csv"
        hr_df.to_csv(hr_filename, index=False)
        sb_df.to_csv(sb_filename, index=False)
        print(f"Saved home run props to {hr_filename}")
        print(f"Saved stolen base props to {sb_filename}\n")
    else:
        print("No batter props data found")

if __name__ == "__main__":
    main() 