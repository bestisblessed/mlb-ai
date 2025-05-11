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
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american',
        'bookmakers': 'fanduel'
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
        #game_filename = f"data/{date_str}/mlb_games_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        game_filename = f"data/{date_str}/theoddsapi_game_links.csv"
        game_df.to_csv(game_filename, index=False)
        print(f"Saved game list to {game_filename}")
    else:
        print("No games found")
    return games

def get_pitcher_props(event_id):
    """Get pitcher props for specific game"""
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': 'pitcher_strikeouts,pitcher_strikeouts_alternate',
        #'markets': 'pitcher_strikeouts_alternate',
        'oddsFormat': 'american',
        'bookmakers': 'fanduel'
    }
    with requests.Session() as session:
        response = session.get(url, params=params, timeout=(3.05, 27))
    if response.status_code != 200:
        print(f"Error getting props for game {event_id}: {response.status_code}")
        return None
    return response.json()

def extract_props(game_data, props_data):
    """Extract relevant prop data into list of dictionaries"""
    props_list = []
    if not props_data or 'bookmakers' not in props_data or not props_data['bookmakers']:
        return props_list
    game_time = datetime.fromisoformat(game_data['commence_time'].replace('Z', '+00:00'))
    home_team = game_data['home_team']
    away_team = game_data['away_team']
    for bookmaker in props_data['bookmakers']:
        if bookmaker['key'] != 'fanduel':
            continue
        for market in bookmaker['markets']:
            for outcome in market['outcomes']:
                props_list.append({
                    'game_time': game_time,
                    'home_team': home_team,
                    'away_team': away_team,
                    'pitcher_name': outcome['name'],
                    'market': market['key'],
                    'line': outcome.get('point', ''),
                    'over_price': outcome['price'] if outcome['name'].startswith('Over') else '',
                    'under_price': outcome['price'] if outcome['name'].startswith('Under') else ''
                })
    return props_list

def main():
    all_props = []
    games = get_mlb_games()
    for game in games:
        props = get_pitcher_props(game['id'])
        if props:
            props_data = extract_props(game, props)
            all_props.extend(props_data)
        time.sleep(1.2)  
    if all_props:
        df = pd.DataFrame(all_props)
        date_str = datetime.now().strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        #filename = f"data/{date_str}/mlb_pitcher_props_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        filename = f"data/{date_str}/theoddsapi_all_pitcher_props_{date_str}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved props to {filename}")
    else:
        print("No props data found")
        
if __name__ == "__main__":
    main()