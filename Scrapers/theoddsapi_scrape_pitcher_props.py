import requests
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv
import os
from zoneinfo import ZoneInfo

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
    
    all_games = response.json()
    if not all_games:
        print("No games found")
        return []
    
    # Filter games for today (in Eastern Time)
    eastern = ZoneInfo("America/New_York")
    today_eastern = datetime.now(eastern).date()
    today_games = [
        g for g in all_games
        if datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00')).astimezone(eastern).date() == today_eastern
    ]
    
    # Save only today's games to CSV
    if today_games:
        date_str = today_eastern.strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        game_df = pd.DataFrame(today_games)
        game_filename = f"data/{date_str}/theoddsapi_game_links.csv"
        game_df.to_csv(game_filename, index=False)
        print(f"Saved {len(today_games)} games for today ({today_eastern}) to {game_filename}")
    else:
        print(f"No games found for today ({today_eastern})")
    
    return today_games  # Return only today's games

def get_pitcher_props(event_id):
    """Get pitcher props for specific game"""
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us,us2,eu',
        #'markets': 'pitcher_strikeouts,pitcher_strikeouts_alternate',
        'markets': 'pitcher_strikeouts_alternate',
        'oddsFormat': 'american',
        #'bookmakers': 'fanduel'
        'bookmakers': 'betonlineag,fanduel,draftkings,bovada,hardrockbet,fliff,pinnacle,mybookieag'
        #'bookmakers': 'williamhill_us,fanatics'
    }
    with requests.Session() as session:
        response = session.get(url, params=params, timeout=(3.05, 27))
    if response.status_code != 200:
        print(f"Error getting props for game {event_id}: {response.status_code}")
        return None
    #return response.json()
    data = response.json()
    if not data or 'bookmakers' not in data or not data['bookmakers']:
        print(f"No props/bookmakers for game {event_id}")
    return data

def extract_props(game_data, props_data):
    """Extract relevant prop data into list of dictionaries"""
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
                    'pitcher_name': outcome['name'],
                    'market': market['key'],
                    'line': outcome.get('point', ''),
                    'side': outcome.get('description', ''),
                    'price': outcome['price'],
                    'bookmaker': bookmaker['key']
                })
    return props_list

def main():
    all_props = []
    games = get_mlb_games()  # Already filtered for today in Eastern Time
    
    for game in games:
        print(f"Processing game: {game['home_team']} vs {game['away_team']} ({game['id']})")
        props = get_pitcher_props(game['id'])
        if props:
            props_data = extract_props(game, props)
            all_props.extend(props_data)
        else:
            print(f"Skipped game {game['id']} due to error or no data")
        time.sleep(3)
    if all_props:
        df = pd.DataFrame(all_props)
        date_str = datetime.now().strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        filename = f"data/{date_str}/theoddsapi_all_pitcher_props_{date_str}.csv"
        df.to_csv(filename, index=False)

        # ANSI color code for orange (use 33 for yellow/orange-like)
        ORANGE = "\033[33m"
        RESET = "\033[0m"
        print(f"{ORANGE}Saved pitcher props to {filename}{RESET}")
    else:
        print("No props data found")
        
if __name__ == "__main__":
    main()