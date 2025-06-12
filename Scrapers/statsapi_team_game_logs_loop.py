import requests
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path
import os
import sys

BASE_URL = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 10
MAX_WORKERS = 6
RETRY_DELAY = 5
MAX_RETRIES = 3


def get_json(endpoint: str, params: dict | None = None):
    """Helper to GET an endpoint with basic retry logic."""
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


def fetch_team_game_log(team_id: int, season: int):
    """Return list of game records (dicts) for one team and season."""
    # schedule endpoint: one call returns the entire regular season when season param provided.
    params = {
        "sportId": 1,
        "teamId": team_id,
        "season": season,
    }
    data = get_json("schedule", params)

    records: list[dict] = []

    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            # Determine if current team is home or away
            is_home = game["teams"]["home"]["team"]["id"] == team_id
            team_branch = "home" if is_home else "away"
            opp_branch = "away" if is_home else "home"

            # Flatten the entire game JSON to capture every field
            flat = pd.json_normalize(game, sep="_").iloc[0].to_dict()

            # Add perspective-specific columns (so we know which side this row represents)
            team_score = game["teams"][team_branch].get("score")
            opp_score = game["teams"][opp_branch].get("score")

            flat.update(
                {
                    "perspective_team_id": team_id,
                    "perspective_is_home": is_home,
                    "perspective_opponent_id": game["teams"][opp_branch]["team"]["id"],
                    "perspective_team_runs": team_score,
                    "perspective_opp_runs": opp_score,
                    "perspective_result": (
                        "W" if team_score is not None and opp_score is not None and team_score > opp_score
                        else ("L" if team_score is not None and opp_score is not None and team_score < opp_score
                        else ("T" if team_score is not None and opp_score is not None and team_score == opp_score
                        else None))
                    ),
                }
            )

            records.append(flat)

    return records


def fetch_all_teams_game_logs(season: int):
    print("Fetching all MLB teams...")
    teams_data = get_json("teams", {"sportId": 1})

    team_ids = [team["id"] for team in teams_data.get("teams", [])]
    print(f"Found {len(team_ids)} teams. Fetching game logs...")

    all_records: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_team_game_log, tid, season): tid for tid in team_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Teams"):
            team_records = future.result()
            all_records.extend(team_records)

    df_games = pd.DataFrame(all_records)

    # Save to CSV
    os.makedirs(f"data/{season}", exist_ok=True)
    df_games.to_csv(f"data/{season}/team_gamelogs_{season}_statsapi.csv", index=False)

    return df_games


def fetch_game_summary(game_pk: int, tries: int = 4) -> dict:
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    for n in range(tries):
        try:
            feed = requests.get(url, timeout=TIMEOUT).json()
            break
        except requests.exceptions.RequestException as exc:
            if n == tries - 1:
                raise RuntimeError(f"{game_pk} failed after {tries} tries") from exc
            time.sleep(2 ** n)      # 1s, 2s, 4s …


if __name__ == "__main__":
    if len(sys.argv) > 1:
        year = int(sys.argv[1])
    else:
        year = 2025
    df_games = fetch_all_teams_game_logs(year)
    print(f"Saved {len(df_games)} total team game records.")
    print(df_games.head()) 