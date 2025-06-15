import requests
import pandas as pd
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

BASE_URL = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 20
MAX_WORKERS = 6
RETRY_DELAY = 5
MAX_RETRIES = 3

BATTERS_FILE = 'data/2025/batters_details_2025_statsapi.csv'
PITCHERS_FILE = 'data/2025/pitchers_details_2025_statsapi.csv'
SEASON = '2025'

def get_json(url, params=None):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            print(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
            return None

def fetch_stats(personId):
    url = f"{BASE_URL}/people/{personId}/stats"
    params = {'stats': 'season', 'season': SEASON}
    data = get_json(url, params)
    if data and 'stats' in data and data['stats']:
        return pd.json_normalize(data['stats'], sep='_', max_level=None)
    return None

def fetch_all_stats(ids, label):
    stats = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_stats, pid): pid for pid in ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Fetching {label} stats"):
            result = future.result()
            if result is not None and not result.empty:
                stats.append(result)
    return stats

def save_stats(stats, out_path, label):
    if stats:
        all_stats = pd.concat(stats, ignore_index=True)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        all_stats.to_csv(out_path, index=False)
        print(f"Saved {out_path} ({len(all_stats)} {label}s)")
        print(all_stats.head())
    else:
        print(f"No {label} stats found for {SEASON}.")

if os.path.exists(BATTERS_FILE):
    print(f"Fetching batters' season stats for {SEASON} in parallel...")
    batters_df = pd.read_csv(BATTERS_FILE)
    batters_stats = fetch_all_stats(batters_df['id'], "batter")
    save_stats(batters_stats, f'data/2025/batters_season_2025_stats.csv', "batter")
else:
    print(f"{BATTERS_FILE} not found, skipping batters for {SEASON}.")

if os.path.exists(PITCHERS_FILE):
    print(f"Fetching pitchers' season stats for {SEASON} in parallel...")
    pitchers_df = pd.read_csv(PITCHERS_FILE)
    pitchers_stats = fetch_all_stats(pitchers_df['id'], "pitcher")
    save_stats(pitchers_stats, f'data/2025/pitchers_season_2025_stats.csv', "pitcher")
else:
    print(f"{PITCHERS_FILE} not found, skipping pitchers for {SEASON}.") 