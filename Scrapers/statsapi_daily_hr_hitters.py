#!/usr/bin/env python3
"""List all MLB home run hitters for a given date from StatsAPI batter game logs."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys


DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


def load_player_names(details_csv: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    with details_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            player_id = row.get("player_id", "").strip()
            if not player_id:
                continue
            names[player_id] = (
                row.get("fullName", "").strip()
                or row.get("nameFirstLast", "").strip()
                or player_id
            )
    return names


def hr_hitters_for_date(game_logs_csv: Path, player_names: dict[str, str], target_date: str) -> list[tuple[str, int]]:
    hr_totals: defaultdict[str, int] = defaultdict(int)

    with game_logs_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date") != target_date:
                continue
            try:
                home_runs = int(float(row.get("homeRuns", "0") or 0))
            except ValueError:
                home_runs = 0
            if home_runs <= 0:
                continue
            player_id = (row.get("player_id") or "").strip()
            player_name = player_names.get(player_id, player_id or "Unknown Player")
            hr_totals[player_name] += home_runs

    return sorted(hr_totals.items(), key=lambda item: (-item[1], item[0]))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show all home run hitters for a given date from local StatsAPI game logs."
    )
    parser.add_argument("--date", required=True, help="Date to query in YYYY-MM-DD format.")
    parser.add_argument("--year", type=int, help="Season year (auto-detected from date if omitted).")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Base data directory (default: {DEFAULT_DATA_DIR}).",
    )
    args = parser.parse_args()

    year = args.year if args.year is not None else int(args.date.split("-")[0])
    game_logs_csv = args.data_dir / str(year) / f"batters_gamelogs_{year}_statsapi.csv"
    details_csv = args.data_dir / str(year) / f"batters_details_{year}_statsapi.csv"

    if not game_logs_csv.exists() or not details_csv.exists():
        print("Missing required files:", file=sys.stderr)
        print(f"- {game_logs_csv}", file=sys.stderr)
        print(f"- {details_csv}", file=sys.stderr)
        return 1

    player_names = load_player_names(details_csv)
    hr_hitters = hr_hitters_for_date(game_logs_csv, player_names, args.date)

    print(f"Home run hitters for {args.date}")
    print("=" * (23 + len(args.date)))

    if not hr_hitters:
        print("No home runs found for this date.")
        return 0

    for name, home_runs in hr_hitters:
        suffix = "HR" if home_runs == 1 else "HRs"
        print(f"{name}: {home_runs} {suffix}")

    print(f"\nTotal HR hitters: {len(hr_hitters)}")
    print(f"Total HRs: {sum(count for _, count in hr_hitters)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
