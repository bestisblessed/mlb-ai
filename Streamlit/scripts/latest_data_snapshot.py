#!/usr/bin/env python3
"""Print the latest available dashboard data date and game summary."""

from __future__ import annotations

import csv
import re
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parents[1] / "data"
    date_dirs = sorted(
        p for p in base.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
    )
    if not date_dirs:
        print("No dated folders found under Streamlit/data.")
        return

    latest = date_dirs[-1]
    sim_file = latest / "game_simulations.csv"
    if not sim_file.exists():
        print(f"Latest date folder: {latest.name}")
        print("No game_simulations.csv file found there.")
        return

    with sim_file.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    print(f"latest_date={latest.name}")
    print(f"games_count={len(rows)}")
    if rows:
        last = rows[-1]
        print(f"last_game_id={last.get('game_id', '')}")
        print(f"last_game={last.get('away_team', '')} @ {last.get('home_team', '')}")
        print(f"last_game_time={last.get('time', '')}")


if __name__ == "__main__":
    main()
