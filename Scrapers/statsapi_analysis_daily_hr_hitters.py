#!/usr/bin/env python3
"""List MLB home run hitters for a given date from StatsAPI batter game logs."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_player_names(details_csv: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    with details_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_id = (row.get("player_id") or "").strip()
            if not player_id:
                continue
            names[player_id] = (row.get("fullName") or "").strip() or player_id
    return names


def collect_daily_home_runs(gamelogs_csv: Path, target_date: str) -> tuple[dict[str, int], dict[str, str]]:
    hr_by_player: defaultdict[str, int] = defaultdict(int)
    team_by_player: dict[str, str] = {}

    with gamelogs_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("date") or "").strip() != target_date:
                continue

            player_id = (row.get("player_id") or "").strip()
            if not player_id:
                continue

            home_runs_raw = (row.get("homeRuns") or "0").strip()
            try:
                home_runs = int(float(home_runs_raw))
            except ValueError:
                home_runs = 0

            if home_runs > 0:
                hr_by_player[player_id] += home_runs
                team_by_player[player_id] = (row.get("team") or "").strip() or "N/A"

    return dict(hr_by_player), team_by_player


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show all home run hitters for a single date from StatsAPI game logs."
    )
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format (e.g. 2026-04-29)")
    parser.add_argument("--year", type=int, default=None, help="Season year (defaults to year from --date)")
    parser.add_argument("--data-dir", default="Scrapers/data", help="Base data directory")
    args = parser.parse_args()

    year = args.year if args.year else int(args.date[:4])
    base_dir = Path(args.data_dir) / str(year)
    gamelogs_csv = base_dir / f"batters_gamelogs_{year}_statsapi.csv"
    details_csv = base_dir / f"batters_details_{year}_statsapi.csv"

    if not gamelogs_csv.exists():
        raise SystemExit(f"Missing game logs file: {gamelogs_csv}")
    if not details_csv.exists():
        raise SystemExit(f"Missing details file: {details_csv}")

    names = load_player_names(details_csv)
    hr_by_player, team_by_player = collect_daily_home_runs(gamelogs_csv, args.date)

    sorted_rows = sorted(
        (
            (names.get(player_id, player_id), team_by_player.get(player_id, "N/A"), total_hr)
            for player_id, total_hr in hr_by_player.items()
        ),
        key=lambda row: (-row[2], row[0]),
    )

    print(f"Home run hitters for {args.date}")
    print("-" * 40)
    if not sorted_rows:
        print("No home runs found for this date.")
        return

    for name, team, total_hr in sorted_rows:
        print(f"{name} ({team}): {total_hr}")

    print("-" * 40)
    print(f"Players with HR: {len(sorted_rows)}")
    print(f"Total HR hit: {sum(total_hr for _, _, total_hr in sorted_rows)}")


if __name__ == "__main__":
    main()
