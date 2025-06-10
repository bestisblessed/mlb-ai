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

def get_batter_props(event_id):
    """Get batter home run, stolen base, hits, and total bases props for a specific game"""
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us,us2,eu',
        'markets': 'batter_home_runs,batter_stolen_bases,batter_hits,batter_total_bases,batter_hits_alternate',
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
        # print(f"No batter props/bookmakers for game {event_id}")
        pass
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
    games = get_mlb_games()  # Already filtered for today in Eastern Time
    
    # Deduplicate games by (home_team, away_team, commence_time)
    unique_games = []
    seen = set()
    for game in games:
        key = (game['home_team'], game['away_team'], game['commence_time'])
        if key not in seen:
            unique_games.append(game)
            seen.add(key)
    for game in unique_games:
        print(f"Processing game: {game['home_team']} vs {game['away_team']} ({game['id']})")
        props = get_batter_props(game['id'])
        if props:
            props_data = extract_batter_props(game, props)
            all_props.extend(props_data)
        else:
            print(f"Skipped game {game['id']} due to error or no data")
        time.sleep(3)
    if all_props:
        df = pd.DataFrame(all_props)
        date_str = datetime.now().strftime('%Y-%m-%d')
        os.makedirs(f"data/{date_str}", exist_ok=True)
        # filename = f"data/{date_str}/theoddsapi_batter_props_{date_str}.csv"
        # df.to_csv(filename, index=False)
        # print(f"\nSaved batter props to {filename}")

        # Save home runs, stolen bases, hits, total bases, and alternate hits to separate files
        hr_df = df[df['market'] == 'batter_home_runs']
        sb_df = df[df['market'] == 'batter_stolen_bases']
        hits_df = df[df['market'] == 'batter_hits']
        tb_df = df[df['market'] == 'batter_total_bases']
        hits_alt_df = df[df['market'] == 'batter_hits_alternate']
        hr_filename = f"data/{date_str}/theoddsapi_batter_home_runs_{date_str}.csv"
        sb_filename = f"data/{date_str}/theoddsapi_batter_stolen_bases_{date_str}.csv"
        hits_filename = f"data/{date_str}/theoddsapi_batter_hits_{date_str}.csv"
        tb_filename = f"data/{date_str}/theoddsapi_batter_total_bases_{date_str}.csv"
        hits_alt_filename = f"data/{date_str}/theoddsapi_batter_hits_alternate_{date_str}.csv"
        hr_df.to_csv(hr_filename, index=False)
        sb_df.to_csv(sb_filename, index=False)
        hits_df.to_csv(hits_filename, index=False)
        tb_df.to_csv(tb_filename, index=False)
        hits_alt_df.to_csv(hits_alt_filename, index=False)

        # ANSI color codes
        GREEN = "\033[92m"
        CYAN = "\033[96m"
        YELLOW = "\033[93m"
        MAGENTA = "\033[95m"
        BLUE = "\033[94m"
        RESET = "\033[0m"

        print(f"{GREEN}Saved home run props to {hr_filename}{RESET}")
        print(f"{CYAN}Saved stolen base props to {sb_filename}{RESET}")
        print(f"{YELLOW}Saved hits props to {hits_filename}{RESET}")
        print(f"{MAGENTA}Saved total bases props to {tb_filename}{RESET}")
        print(f"{BLUE}Saved alternate hits props to {hits_alt_filename}{RESET}\n")
    else:
        print("No batter props data found")

if __name__ == "__main__":
    main() 