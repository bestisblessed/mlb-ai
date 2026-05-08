#!/usr/bin/env python3
"""Live MLB home run hitters for a given date, fetched directly from StatsAPI."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import requests

BASE_URL = "https://statsapi.mlb.com/api/v1"
TIMEOUT = 15


def get_json(url, params=None):
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_games_for_date(target_date: str) -> list[dict]:
    data = get_json(f"{BASE_URL}/schedule", params={
        "date": target_date,
        "sportId": 1,
        "gameType": "R,F,D,L,W",
    })
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            status = g.get("status", {}).get("abstractGameState", "")
            games.append({"gamePk": g["gamePk"], "status": status})
    return games


def extract_hr_from_boxscore(game_pk: int) -> list[dict]:
    data = get_json(f"{BASE_URL}/game/{game_pk}/boxscore")
    hitters = []
    for side in ("away", "home"):
        team_name = data["teams"][side]["team"]["name"]
        players = data["teams"][side].get("players", {})
        for player_data in players.values():
            stats = player_data.get("stats", {}).get("batting", {})
            hr = stats.get("homeRuns", 0)
            if hr > 0:
                name = player_data["person"]["fullName"]
                hitters.append({"name": name, "team": team_name, "hr": hr})
    return hitters


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live: show all home run hitters for a date via StatsAPI."
    )
    parser.add_argument(
        "--date",
        default=str(date.today()),
        help="Date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--yesterday", action="store_true",
        help="Shortcut to check yesterday's games",
    )
    args = parser.parse_args()

    target_date = str(date.today() - timedelta(days=1)) if args.yesterday else args.date

    games = get_games_for_date(target_date)
    if not games:
        print(f"No games scheduled for {target_date}.")
        return

    final_count = sum(1 for g in games if g["status"] == "Final")
    live_count = sum(1 for g in games if g["status"] == "Live")
    preview_count = sum(1 for g in games if g["status"] == "Preview")

    hr_totals: defaultdict[tuple[str, str], int] = defaultdict(int)

    finished_pks = [g["gamePk"] for g in games if g["status"] in ("Final", "Live")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(extract_hr_from_boxscore, pk): pk for pk in finished_pks}
        for future in as_completed(futures):
            for h in future.result():
                hr_totals[(h["name"], h["team"])] += h["hr"]

    sorted_rows = sorted(hr_totals.items(), key=lambda x: (-x[1], x[0][0]))

    print(f"Home run hitters for {target_date}")
    print(f"Games: {final_count} Final, {live_count} Live, {preview_count} Preview")
    print("-" * 45)

    if not sorted_rows:
        print("No home runs found (yet).")
    else:
        for (name, team), hr in sorted_rows:
            print(f"{name} ({team}): {hr}")
        print("-" * 45)
        print(f"Players with HR: {len(sorted_rows)}")
        print(f"Total HR hit: {sum(hr for _, hr in sorted_rows)}")


if __name__ == "__main__":
    main()
