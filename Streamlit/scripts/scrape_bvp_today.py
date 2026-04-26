"""
scrape_bvp_today.py
===================

Pulls today's MLB slate and, for every batter on each team's active roster,
pulls career Batter-vs-Pitcher (BvP) splits against the opposing probable
starter, plus each batter's current-season hitting line (used as a Bayesian
shrinkage prior in rank_bvp_edges.py).

Designed for professional handicappers / data scientists. No HTML scraping --
direct MLB Stats API via python-mlb-statsapi with the `vsPlayerTotal`
hydrate, which returns the canonical career head-to-head split.

Output (per run):
    data/<YYYY-MM-DD>/bvp/games_index.csv          # game/pitcher metadata
    data/<YYYY-MM-DD>/bvp/bvp_career.csv           # one row per batter-pitcher pair
    data/<YYYY-MM-DD>/bvp/batter_season.csv        # one row per batter (prior)
    data/<YYYY-MM-DD>/bvp/_run_meta.json           # provenance + counts

Usage:
    python scripts/scrape_bvp_today.py                  # today
    python scripts/scrape_bvp_today.py 2026-04-26       # specific date
    python scripts/scrape_bvp_today.py --season-prior 2025
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import statsapi


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    # scripts/ lives at repo root
    return here.parent


def data_dir() -> Path:
    root = repo_root()
    d = root / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# StatsAPI helpers (raw hydrate route -- more reliable than the helper fns)
# ---------------------------------------------------------------------------
def _safe_get(d: dict, *path, default=None):
    cur = d
    for p in path:
        if cur is None:
            return default
        if isinstance(cur, list):
            try:
                cur = cur[p]
            except Exception:
                return default
        else:
            cur = cur.get(p) if hasattr(cur, "get") else default
    return cur if cur is not None else default


def lookup_pitcher_id(name: str) -> int | None:
    """Resolve a pitcher's MLB person ID from their full name."""
    if not name:
        return None
    try:
        results = statsapi.lookup_player(name)
    except Exception:
        return None
    # Prefer position == P
    for r in results:
        pos = _safe_get(r, "primaryPosition", "code", default="")
        if pos == "1":
            return int(r["id"])
    return int(results[0]["id"]) if results else None


def get_person_meta(person_id: int) -> dict:
    """Fetch handedness + name."""
    try:
        data = statsapi.get("person", {"personId": person_id, "hydrate": "currentTeam"})
    except Exception:
        return {}
    person = _safe_get(data, "people", 0, default={}) or {}
    return {
        "id": person.get("id"),
        "fullName": person.get("fullName"),
        "pitchHand": _safe_get(person, "pitchHand", "code"),
        "batSide": _safe_get(person, "batSide", "code"),
        "primaryPosition": _safe_get(person, "primaryPosition", "code"),
    }


def get_bvp_career(batter_id: int, pitcher_id: int) -> dict | None:
    """Career BvP split for a specific batter vs pitcher.

    Returns the `stat` dict from the single split, or None if no PA exists.
    """
    hydrate = (
        "stats(group=[hitting],"
        f"type=[vsPlayerTotal],opposingPlayerId={pitcher_id},sportId=1)"
    )
    try:
        data = statsapi.get("person", {"personId": batter_id, "hydrate": hydrate})
    except Exception as e:
        return {"_error": str(e)}
    splits = _safe_get(data, "people", 0, "stats", 0, "splits", default=[]) or []
    if not splits:
        return None
    return splits[0].get("stat", {}) or {}


def get_season_hitting(batter_id: int, season: int) -> dict | None:
    hydrate = f"stats(group=[hitting],type=[season],season={season},sportId=1)"
    try:
        data = statsapi.get("person", {"personId": batter_id, "hydrate": hydrate})
    except Exception:
        return None
    splits = _safe_get(data, "people", 0, "stats", 0, "splits", default=[]) or []
    if not splits:
        return None
    return splits[0].get("stat", {}) or {}


# ---------------------------------------------------------------------------
# Main scrape
# ---------------------------------------------------------------------------
HITTING_STAT_COLS = [
    "plateAppearances", "atBats", "hits", "doubles", "triples", "homeRuns",
    "baseOnBalls", "intentionalWalks", "strikeOuts", "hitByPitch",
    "sacFlies", "sacBunts", "totalBases", "rbi", "groundIntoDoublePlay",
    "avg", "obp", "slg", "ops", "babip", "atBatsPerHomeRun",
    "numberOfPitches", "groundOuts", "airOuts",
]


def scrape(target_date: str, season_prior: int, max_workers: int = 8) -> dict:
    games = statsapi.schedule(start_date=target_date, end_date=target_date)
    print(f"[scrape_bvp] {target_date}: {len(games)} games on schedule")

    if not games:
        return {"games": 0, "matchups": 0}

    # 1. Build games index + resolve probable pitcher IDs
    games_rows: list[dict] = []
    pitcher_meta: dict[int, dict] = {}
    for g in games:
        ap = g.get("away_probable_pitcher") or ""
        hp = g.get("home_probable_pitcher") or ""
        ap_id = g.get("away_probable_pitcher_id") or lookup_pitcher_id(ap)
        hp_id = g.get("home_probable_pitcher_id") or lookup_pitcher_id(hp)

        if ap_id and ap_id not in pitcher_meta:
            pitcher_meta[int(ap_id)] = get_person_meta(int(ap_id))
        if hp_id and hp_id not in pitcher_meta:
            pitcher_meta[int(hp_id)] = get_person_meta(int(hp_id))

        games_rows.append({
            "game_id": g["game_id"],
            "game_datetime": g.get("game_datetime"),
            "status": g.get("status"),
            "away_id": g.get("away_id"),
            "away_name": g.get("away_name"),
            "home_id": g.get("home_id"),
            "home_name": g.get("home_name"),
            "venue_name": g.get("venue_name"),
            "away_pitcher": ap,
            "away_pitcher_id": ap_id,
            "away_pitcher_hand": pitcher_meta.get(int(ap_id), {}).get("pitchHand") if ap_id else None,
            "home_pitcher": hp,
            "home_pitcher_id": hp_id,
            "home_pitcher_hand": pitcher_meta.get(int(hp_id), {}).get("pitchHand") if hp_id else None,
        })

    # 2. For each game, pull boxscore (active roster) and queue BvP fetches
    bvp_jobs: list[tuple] = []  # (game_id, side, batter_id, batter_name, pitcher_id, pitcher_name)
    batter_ids: set[int] = set()
    batter_meta: dict[int, dict] = {}

    for g_row in games_rows:
        gid = g_row["game_id"]
        ap_id = g_row["away_pitcher_id"]
        hp_id = g_row["home_pitcher_id"]
        if not ap_id or not hp_id:
            print(f"  - {gid}: missing probable pitcher, skipping")
            continue
        try:
            box = statsapi.boxscore_data(gid)
        except Exception as e:
            print(f"  - {gid}: boxscore err: {e}")
            continue

        # Away batters vs home pitcher
        for p in (box.get("away", {}).get("players") or {}).values():
            if _safe_get(p, "position", "code") == "1":
                continue
            pid = _safe_get(p, "person", "id")
            pname = _safe_get(p, "person", "fullName")
            if not pid:
                continue
            batter_ids.add(int(pid))
            batter_meta[int(pid)] = {
                "fullName": pname,
                "team_id": g_row["away_id"],
                "team_name": g_row["away_name"],
                "batSide": _safe_get(p, "person", "batSide", "code") or _safe_get(p, "batSide", "code"),
                "primaryPosition": _safe_get(p, "position", "abbreviation"),
            }
            bvp_jobs.append((gid, "away", int(pid), pname, int(hp_id), g_row["home_pitcher"]))

        # Home batters vs away pitcher
        for p in (box.get("home", {}).get("players") or {}).values():
            if _safe_get(p, "position", "code") == "1":
                continue
            pid = _safe_get(p, "person", "id")
            pname = _safe_get(p, "person", "fullName")
            if not pid:
                continue
            batter_ids.add(int(pid))
            batter_meta[int(pid)] = {
                "fullName": pname,
                "team_id": g_row["home_id"],
                "team_name": g_row["home_name"],
                "batSide": _safe_get(p, "person", "batSide", "code") or _safe_get(p, "batSide", "code"),
                "primaryPosition": _safe_get(p, "position", "abbreviation"),
            }
            bvp_jobs.append((gid, "home", int(pid), pname, int(ap_id), g_row["away_pitcher"]))

    print(f"[scrape_bvp] {len(bvp_jobs)} BvP fetches across {len(batter_ids)} unique batters")

    # 3. Pull BvP in parallel
    bvp_rows: list[dict] = []

    def _do_bvp(job):
        gid, side, bid, bname, pid, pname = job
        stat = get_bvp_career(bid, pid)
        return job, stat

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_do_bvp, j) for j in bvp_jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            (gid, side, bid, bname, pid, pname), stat = fut.result()
            row = {
                "game_id": gid,
                "side": side,           # 'away' batter vs home pitcher, etc
                "batter_id": bid,
                "batter_name": bname,
                "pitcher_id": pid,
                "pitcher_name": pname,
            }
            if stat is None:
                row["pa"] = 0
                bvp_rows.append(row)
                continue
            if "_error" in stat:
                row["pa"] = 0
                row["error"] = stat["_error"]
                bvp_rows.append(row)
                continue
            for c in HITTING_STAT_COLS:
                row[c] = stat.get(c)
            bvp_rows.append(row)
            if i % 50 == 0:
                print(f"  ... {i}/{len(futures)} ({time.time()-t0:.1f}s)")

    print(f"[scrape_bvp] BvP fetched in {time.time()-t0:.1f}s")

    # 4. Pull season prior for each batter (parallel)
    # Fetch BOTH current and prior season so rank_bvp_edges.py always has
    # _prev columns for the two-year weighted prior — matches scrape_one_game() schema.
    season_rows: list[dict] = []

    def _do_season(bid):
        cur = get_season_hitting(bid, season_prior) or {}
        prv = get_season_hitting(bid, season_prior - 1) or {}
        return bid, cur, prv

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_do_season, b) for b in batter_ids]
        for i, fut in enumerate(as_completed(futures), 1):
            bid, cur, prv = fut.result()
            meta = batter_meta.get(bid, {})
            row = {
                "batter_id": bid,
                "batter_name": meta.get("fullName"),
                "team_id": meta.get("team_id"),
                "team_name": meta.get("team_name"),
                "batSide": meta.get("batSide"),
                "primaryPosition": meta.get("primaryPosition"),
                "season": season_prior,
            }
            for c in HITTING_STAT_COLS:
                row[c] = cur.get(c) if cur else None
            for c in HITTING_STAT_COLS:
                row[f"{c}_prev"] = prv.get(c) if prv else None
            row["season_prev"] = season_prior - 1
            season_rows.append(row)
            if i % 50 == 0:
                print(f"  ... {i}/{len(futures)} season ({time.time()-t0:.1f}s)")

    print(f"[scrape_bvp] Season priors fetched in {time.time()-t0:.1f}s")

    # 5. Persist
    out_dir = data_dir() / target_date / "bvp"
    out_dir.mkdir(parents=True, exist_ok=True)

    games_df = pd.DataFrame(games_rows)
    bvp_df = pd.DataFrame(bvp_rows)
    season_df = pd.DataFrame(season_rows)

    games_df.to_csv(out_dir / "games_index.csv", index=False)
    bvp_df.to_csv(out_dir / "bvp_career.csv", index=False)
    season_df.to_csv(out_dir / "batter_season.csv", index=False)

    meta = {
        "target_date": target_date,
        "season_prior": season_prior,
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
        "games": len(games_rows),
        "batters": len(season_rows),
        "bvp_rows": len(bvp_rows),
        "bvp_with_pa": int((bvp_df.get("plateAppearances", pd.Series(dtype=float)).fillna(0) > 0).sum()) if not bvp_df.empty else 0,
    }
    with open(out_dir / "_run_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[scrape_bvp] wrote {len(bvp_rows)} bvp / {len(season_rows)} season rows to {out_dir}")
    return meta


def scrape_one_game(target_date: str, season_prior: int, game_idx: int,
                    max_workers: int = 12, append: bool = True) -> dict:
    """Chunked variant: scrape a single game and append to daily CSVs.

    Useful in environments where each shell call has a tight time budget --
    you can loop `--game-index 0..N-1` across multiple invocations and the
    output accretes. Idempotent (dedupe handled by the edge engine).
    """
    games = statsapi.schedule(start_date=target_date, end_date=target_date)
    if not games or game_idx >= len(games):
        return {"games": 0, "matchups": 0, "skipped": True}

    g = games[game_idx]
    print(f"[scrape_bvp][{game_idx+1}/{len(games)}] {g['away_name']} @ {g['home_name']} ({g['game_id']})", flush=True)

    out_dir = data_dir() / target_date / "bvp"
    out_dir.mkdir(parents=True, exist_ok=True)
    games_path = out_dir / "games_index.csv"
    bvp_path = out_dir / "bvp_career.csv"
    season_path = out_dir / "batter_season.csv"

    # --- 1. Game row + pitcher metadata ---
    ap = g.get("away_probable_pitcher") or ""
    hp = g.get("home_probable_pitcher") or ""
    ap_id = g.get("away_probable_pitcher_id") or lookup_pitcher_id(ap)
    hp_id = g.get("home_probable_pitcher_id") or lookup_pitcher_id(hp)
    if not ap_id or not hp_id:
        print("  - missing probable pitcher; skipping", flush=True)
        return {"games": 0, "skipped": True}

    ap_meta = get_person_meta(int(ap_id))
    hp_meta = get_person_meta(int(hp_id))

    game_row = {
        "game_id": g["game_id"],
        "game_datetime": g.get("game_datetime"),
        "status": g.get("status"),
        "away_id": g.get("away_id"),
        "away_name": g.get("away_name"),
        "home_id": g.get("home_id"),
        "home_name": g.get("home_name"),
        "venue_name": g.get("venue_name"),
        "away_pitcher": ap,
        "away_pitcher_id": ap_id,
        "away_pitcher_hand": ap_meta.get("pitchHand"),
        "home_pitcher": hp,
        "home_pitcher_id": hp_id,
        "home_pitcher_hand": hp_meta.get("pitchHand"),
    }
    games_df = pd.DataFrame([game_row])
    if append and games_path.exists():
        existing = pd.read_csv(games_path)
        existing = existing[existing["game_id"] != game_row["game_id"]]
        games_df = pd.concat([existing, games_df], ignore_index=True)
    games_df.to_csv(games_path, index=False)

    # --- 2. Roster ---
    try:
        box = statsapi.boxscore_data(g["game_id"])
    except Exception as e:
        print(f"  - boxscore err: {e}", flush=True)
        return {"games": 0, "error": str(e)}

    bvp_jobs = []
    batter_meta: dict[int, dict] = {}

    for p in (box.get("away", {}).get("players") or {}).values():
        if _safe_get(p, "position", "code") == "1":
            continue
        pid = _safe_get(p, "person", "id")
        pname = _safe_get(p, "person", "fullName")
        if not pid:
            continue
        batter_meta[int(pid)] = {
            "fullName": pname,
            "team_id": g.get("away_id"), "team_name": g.get("away_name"),
            "batSide": _safe_get(p, "person", "batSide", "code") or _safe_get(p, "batSide", "code"),
            "primaryPosition": _safe_get(p, "position", "abbreviation"),
        }
        bvp_jobs.append((g["game_id"], "away", int(pid), pname, int(hp_id), hp))

    for p in (box.get("home", {}).get("players") or {}).values():
        if _safe_get(p, "position", "code") == "1":
            continue
        pid = _safe_get(p, "person", "id")
        pname = _safe_get(p, "person", "fullName")
        if not pid:
            continue
        batter_meta[int(pid)] = {
            "fullName": pname,
            "team_id": g.get("home_id"), "team_name": g.get("home_name"),
            "batSide": _safe_get(p, "person", "batSide", "code") or _safe_get(p, "batSide", "code"),
            "primaryPosition": _safe_get(p, "position", "abbreviation"),
        }
        bvp_jobs.append((g["game_id"], "home", int(pid), pname, int(ap_id), ap))

    print(f"  - {len(bvp_jobs)} BvP fetches", flush=True)

    # --- 3. BvP fetch ---
    bvp_rows = []
    def _do_bvp(job):
        gid, side, bid, bname, pid, pname = job
        return job, get_bvp_career(bid, pid)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for fut in as_completed([ex.submit(_do_bvp, j) for j in bvp_jobs]):
            (gid, side, bid, bname, pid, pname), stat = fut.result()
            row = {"game_id": gid, "side": side, "batter_id": bid, "batter_name": bname,
                   "pitcher_id": pid, "pitcher_name": pname}
            if stat and "_error" not in stat:
                for c in HITTING_STAT_COLS:
                    row[c] = stat.get(c)
            else:
                row["plateAppearances"] = 0
            bvp_rows.append(row)
    print(f"  - BvP fetched in {time.time()-t0:.1f}s", flush=True)

    new_bvp = pd.DataFrame(bvp_rows)
    if append and bvp_path.exists():
        existing = pd.read_csv(bvp_path)
        # remove any prior rows for this game
        existing = existing[existing["game_id"] != game_row["game_id"]]
        new_bvp = pd.concat([existing, new_bvp], ignore_index=True)
    new_bvp.to_csv(bvp_path, index=False)

    # --- 4. Season prior for new batters only ---
    # We pull BOTH the current season AND the prior season so the edge engine
    # can build a stable two-year weighted prior (critical in April when
    # many hitters have <50 PA on the current year).
    existing_season_df = pd.read_csv(season_path) if (append and season_path.exists()) else pd.DataFrame()
    have_ids = set(existing_season_df["batter_id"].astype(int).tolist()) if not existing_season_df.empty else set()
    new_batters = [bid for bid in batter_meta if bid not in have_ids]

    season_rows = []
    def _do_season(bid):
        cur = get_season_hitting(bid, season_prior) or {}
        prv = get_season_hitting(bid, season_prior - 1) or {}
        return bid, cur, prv

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for fut in as_completed([ex.submit(_do_season, bid) for bid in new_batters]):
            bid, cur, prv = fut.result()
            meta = batter_meta[bid]
            row = {"batter_id": bid, "batter_name": meta["fullName"],
                   "team_id": meta["team_id"], "team_name": meta["team_name"],
                   "batSide": meta["batSide"], "primaryPosition": meta["primaryPosition"],
                   "season": season_prior}
            for c in HITTING_STAT_COLS:
                row[c] = cur.get(c) if cur else None
            # Suffix prior-season columns with _prev
            for c in HITTING_STAT_COLS:
                row[f"{c}_prev"] = prv.get(c) if prv else None
            row["season_prev"] = season_prior - 1
            season_rows.append(row)
    print(f"  - {len(new_batters)} season priors in {time.time()-t0:.1f}s", flush=True)

    if season_rows:
        df_new = pd.DataFrame(season_rows)
        full = pd.concat([existing_season_df, df_new], ignore_index=True) if not existing_season_df.empty else df_new
        full.to_csv(season_path, index=False)

    meta = {
        "target_date": target_date,
        "season_prior": season_prior,
        "game_id": g["game_id"],
        "matchup": f"{g['away_name']} @ {g['home_name']}",
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
        "bvp_rows": len(bvp_rows),
        "new_batters": len(new_batters),
    }
    return meta


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("date", nargs="?", default=None,
                   help="YYYY-MM-DD (default: today)")
    p.add_argument("--season-prior", type=int, default=None,
                   help="Season to use for shrinkage prior (default: current year)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--game-index", type=int, default=None,
                   help="If set, scrape only the Nth game (0-based). Used for chunked runs.")
    p.add_argument("--append", action="store_true",
                   help="Append to existing daily CSVs instead of overwriting.")
    args = p.parse_args()

    target = args.date or datetime.now().strftime("%Y-%m-%d")
    season = args.season_prior or int(target[:4])

    if args.game_index is not None:
        scrape_one_game(target, season, args.game_index,
                        max_workers=args.workers, append=args.append)
    else:
        scrape(target, season, max_workers=args.workers)


if __name__ == "__main__":
    main()
