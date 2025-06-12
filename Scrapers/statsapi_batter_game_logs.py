import requests
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path
import os

BASE_URL = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 20
MAX_WORKERS = 6
RETRY_DELAY = 5
MAX_RETRIES = 3
YEAR = 2025  # Single variable to control year throughout script

def get_json(endpoint, params=None):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

def fetch_batter_gamelog(player_id, season):
    endpoint = f"people/{player_id}/stats"
    params = {
        "stats": "gameLog",
        "season": season,
        "group": "hitting"
    }
    try:
        data = get_json(endpoint, params)
        if not data.get('stats') or len(data['stats']) == 0:
            return []

        splits = data['stats'][0].get('splits', [])
        records = []
        for game in splits:
            stat = game['stat']
            record = {
                "player_id": player_id,
                "date": game['date'],
                "team": game['team']['name'],
                "opponent": game.get('opponent', {}).get('name', ''),
                **stat  # Dynamically include all stat fields
            }
            records.append(record)
        return records
    except Exception as e:
        print(f"Error fetching logs for player {player_id}: {e}")
        return []

def fetch_batter_details(player_id):
    try:
        data = get_json(f"people/{player_id}")
        player_data = data['people'][0]
        return {
            "player_id": player_id,
            **player_data  # Dynamically include all player fields
        }
    except Exception as e:
        print(f"Error fetching details for player {player_id}: {e}")
        return None

def fetch_all_batters_gamelogs(season):
    print("Fetching all MLB teams...")
    teams_data = get_json("teams?sportId=1")

    batter_ids = set()
    print("Collecting batter IDs from team rosters...")
    for team in tqdm(teams_data['teams'], desc="Teams"):
        roster_data = get_json(f"teams/{team['id']}/roster?season={season}")
        for player in roster_data.get('roster', []):
            if player['position']['abbreviation'] != "P":  # All non-pitchers
                batter_ids.add(player['person']['id'])

    print(f"Found {len(batter_ids)} batters. Fetching details and game logs...")
    all_records = []
    batter_details = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_batter_details, pid): pid for pid in batter_ids}
        futures.update({executor.submit(fetch_batter_gamelog, pid, season): pid for pid in batter_ids})
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            result = future.result()
            if isinstance(result, list):
                all_records.extend(result)
            elif isinstance(result, dict):
                batter_details.append(result)

    df_batters = pd.DataFrame(all_records)
    df_batter_details = pd.DataFrame(batter_details)
    
    os.makedirs(f"data/{YEAR}", exist_ok=True)
    df_batters.to_csv(f"data/{YEAR}/batters_gamelogs_{YEAR}_statsapi.csv", index=False)
    df_batter_details.to_csv(f"data/{YEAR}/batters_details_{YEAR}_statsapi.csv", index=False)
    
    return df_batters, df_batter_details

if __name__ == "__main__":
    df_batters, df_batter_details = fetch_all_batters_gamelogs(YEAR)
    print(f"Saved {len(df_batters)} batter game logs.")
    print(f"Saved {len(df_batter_details)} batter details.")
    print(df_batters.head())
    print(df_batter_details.head())