from __future__ import annotations

import argparse
import math
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
REPORTS_DIR = SCRIPT_DIR.parent / "Reports"
ET = ZoneInfo("America/New_York")
SEASON = 2026
PICK_LIMIT = 50

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
BOVADA_URL = (
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/"
    "baseball/mlb?lang=en"
)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

TEAM_CODES = {
    "Arizona Diamondbacks": "ARI",
    "Athletics": "ATH",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WAS",
}
CODE_TO_TEAM = {v: k for k, v in TEAM_CODES.items()}

BALLPARKS = {
    "Progressive Field": {
        "lat": 41.4962,
        "lon": -81.6852,
        "cf_bearing": 17,
        "hr_factor": 1.01,
        "roof": False,
    },
    "PNC Park": {
        "lat": 40.4469,
        "lon": -80.0057,
        "cf_bearing": 23,
        "hr_factor": 0.92,
        "roof": False,
    },
    "Rogers Centre": {
        "lat": 43.6414,
        "lon": -79.3894,
        "cf_bearing": 31,
        "hr_factor": 1.05,
        "roof": True,
    },
    "Target Field": {
        "lat": 44.9817,
        "lon": -93.2776,
        "cf_bearing": 61,
        "hr_factor": 0.97,
        "roof": False,
    },
    "Rate Field": {
        "lat": 41.8300,
        "lon": -87.6339,
        "cf_bearing": 15,
        "hr_factor": 1.08,
        "roof": False,
    },
    "Globe Life Field": {
        "lat": 32.7473,
        "lon": -97.0842,
        "cf_bearing": 35,
        "hr_factor": 1.02,
        "roof": True,
    },
    "Petco Park": {
        "lat": 32.7073,
        "lon": -117.1566,
        "cf_bearing": 28,
        "hr_factor": 0.91,
        "roof": False,
    },
    "Dodger Stadium": {
        "lat": 34.0739,
        "lon": -118.2400,
        "cf_bearing": 39,
        "hr_factor": 1.08,
        "roof": False,
    },
}


def clean_name(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", "", text, flags=re.I)
    text = re.sub(r"[^a-zA-Z ]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def american_to_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"EVEN", "EV"}:
        return 100
    try:
        return int(text.replace("+", ""))
    except ValueError:
        return None


def implied_probability(american: int) -> float:
    if american < 0:
        return abs(american) / (abs(american) + 100)
    return 100 / (american + 100)


def profit_per_dollar(american: int) -> float:
    if american < 0:
        return 100 / abs(american)
    return american / 100


def expected_value(probability: float, american: int) -> float:
    return probability * profit_per_dollar(american) - (1 - probability)


def fair_american(probability: float) -> str:
    probability = min(max(probability, 0.001), 0.999)
    if probability >= 0.5:
        return f"-{round(probability / (1 - probability) * 100):.0f}"
    return f"+{round((1 - probability) / probability * 100):.0f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob_normal_greater(mean: float, sd: float, threshold: float) -> float:
    return 1 - norm_cdf((threshold - mean) / sd)


def poisson_ge(threshold: int, lam: float) -> float:
    if threshold <= 0:
        return 1.0
    lam = max(lam, 0.05)
    term = math.exp(-lam)
    cdf = term
    for k in range(1, threshold):
        term *= lam / k
        cdf += term
    return max(0.0, min(1.0, 1 - cdf))


def parse_player_team(description: str) -> tuple[str, str | None]:
    match = re.match(r"(.+?)\s+\(([A-Z]{2,3})\)$", description.strip())
    if not match:
        return description.strip(), None
    return match.group(1).strip(), match.group(2).strip()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def fetch_json(url: str, params: dict | None = None) -> dict | list:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_today_schedule(report_date: date) -> list[dict]:
    data = fetch_json(
        MLB_SCHEDULE_URL,
        {
            "sportId": 1,
            "date": report_date.isoformat(),
            "hydrate": "probablePitcher,team,venue",
        },
    )
    games = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            away = game["teams"]["away"]
            home = game["teams"]["home"]
            games.append(
                {
                    "gamePk": game["gamePk"],
                    "start_et": datetime.fromisoformat(
                        game["gameDate"].replace("Z", "+00:00")
                    ).astimezone(ET),
                    "away_team": away["team"]["name"],
                    "home_team": home["team"]["name"],
                    "away_probable": away.get("probablePitcher", {}).get("fullName"),
                    "home_probable": home.get("probablePitcher", {}).get("fullName"),
                    "away_probable_id": away.get("probablePitcher", {}).get("id"),
                    "home_probable_id": home.get("probablePitcher", {}).get("id"),
                    "venue": game.get("venue", {}).get("name", ""),
                    "venue_id": game.get("venue", {}).get("id"),
                    "status": game.get("status", {}).get("detailedState", ""),
                }
            )
    return games


def ballpark_profile(venue_name: str) -> dict:
    if venue_name in BALLPARKS:
        return BALLPARKS[venue_name]
    if "Dodger Stadium" in venue_name:
        return BALLPARKS["Dodger Stadium"]
    return {
        "lat": None,
        "lon": None,
        "cf_bearing": 0,
        "hr_factor": 1.0,
        "roof": False,
    }


def angular_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def fetch_game_weather(games: list[dict], report_date: date) -> dict[str, dict]:
    weather = {}
    for game in games:
        profile = ballpark_profile(game["venue"])
        if profile["lat"] is None or profile["roof"]:
            factor = float(profile["hr_factor"])
            weather[game["gamePk"]] = {
                "temp_f": None,
                "wind_mph": None,
                "wind_dir": None,
                "precip_pct": None,
                "wind_out": 0.0,
                "weather_factor": 1.0,
                "park_factor": factor,
                "total_hr_factor": factor,
                "note": "roof/indoor neutral weather"
                if profile["roof"]
                else "weather unavailable",
            }
            continue
        try:
            forecast = fetch_json(
                OPEN_METEO_URL,
                {
                    "latitude": profile["lat"],
                    "longitude": profile["lon"],
                    "hourly": (
                        "temperature_2m,wind_speed_10m,wind_direction_10m,"
                        "precipitation_probability"
                    ),
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "timezone": "America/New_York",
                    "start_date": report_date.isoformat(),
                    "end_date": report_date.isoformat(),
                },
            )
            hourly = forecast.get("hourly", {})
            times = [
                datetime.fromisoformat(value).replace(tzinfo=ET)
                for value in hourly.get("time", [])
            ]
            if not times:
                raise ValueError("forecast hours missing")
            start = game["start_et"]
            idx = min(range(len(times)), key=lambda i: abs(times[i] - start))
            temp = float(hourly["temperature_2m"][idx])
            wind_mph = float(hourly["wind_speed_10m"][idx])
            wind_dir = float(hourly["wind_direction_10m"][idx])
            precip = float(hourly.get("precipitation_probability", [0] * len(times))[idx])
            wind_toward = (wind_dir + 180) % 360
            out_component = math.cos(
                math.radians(angular_diff(wind_toward, profile["cf_bearing"]))
            )
            temp_adj = max(-0.05, min(0.07, (temp - 70) * 0.003))
            wind_adj = max(-0.08, min(0.08, wind_mph * out_component * 0.006))
            precip_adj = -0.02 if precip >= 35 else 0.0
            weather_factor = max(0.86, min(1.16, 1 + temp_adj + wind_adj + precip_adj))
            total_factor = max(0.78, min(1.26, weather_factor * profile["hr_factor"]))
            if out_component > 0.35:
                wind_note = "wind helping carry"
            elif out_component < -0.35:
                wind_note = "wind suppressing carry"
            else:
                wind_note = "cross/neutral wind"
            weather[game["gamePk"]] = {
                "temp_f": temp,
                "wind_mph": wind_mph,
                "wind_dir": wind_dir,
                "precip_pct": precip,
                "wind_out": out_component,
                "weather_factor": weather_factor,
                "park_factor": profile["hr_factor"],
                "total_hr_factor": total_factor,
                "note": f"{wind_note}, {temp:.0f}F",
            }
        except Exception as exc:
            weather[game["gamePk"]] = {
                "temp_f": None,
                "wind_mph": None,
                "wind_dir": None,
                "precip_pct": None,
                "wind_out": 0.0,
                "weather_factor": 1.0,
                "park_factor": float(profile["hr_factor"]),
                "total_hr_factor": float(profile["hr_factor"]),
                "note": f"weather fallback: {exc}",
            }
    return weather


def fetch_recent_team_results(report_date: date) -> pd.DataFrame:
    start_date = date(report_date.year, 3, 1)
    end_date = report_date - timedelta(days=1)
    if end_date < start_date:
        return pd.DataFrame()
    data = fetch_json(
        MLB_SCHEDULE_URL,
        {
            "sportId": 1,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "gameType": "R",
        },
    )
    rows = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            if game.get("status", {}).get("detailedState") != "Final":
                continue
            home = game["teams"]["home"]
            away = game["teams"]["away"]
            if "score" not in home or "score" not in away:
                continue
            game_date = pd.to_datetime(game["officialDate"])
            sides = [
                (home, away, True),
                (away, home, False),
            ]
            for team, opp, is_home in sides:
                runs_for = float(team["score"])
                runs_against = float(opp["score"])
                rows.append(
                    {
                        "date": game_date,
                        "team": team["team"]["name"],
                        "opponent": opp["team"]["name"],
                        "is_home": is_home,
                        "runs_for": runs_for,
                        "runs_against": runs_against,
                        "win": int(runs_for > runs_against),
                    }
                )
    return pd.DataFrame(rows)


def fetch_bovada_events(report_date: date) -> tuple[list[dict], list[dict]]:
    data = fetch_json(BOVADA_URL)
    all_events = []
    rows = []
    for group in data:
        for event in group.get("events", []):
            start_et = datetime.fromtimestamp(
                event["startTime"] / 1000, tz=timezone.utc
            ).astimezone(ET)
            if start_et.date() != report_date:
                continue
            competitors = event.get("competitors", [])
            home_team = next((c["name"] for c in competitors if c.get("home")), "")
            away_team = next((c["name"] for c in competitors if not c.get("home")), "")
            event_info = {
                "event_id": event["id"],
                "description": event.get("description", ""),
                "start_et": start_et,
                "home_team": home_team,
                "away_team": away_team,
            }
            all_events.append({**event_info, "event": event})
            for display_group in event.get("displayGroups", []):
                for market in display_group.get("markets", []):
                    period = market.get("period", {})
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price", {})
                        american = american_to_int(price.get("american"))
                        if american is None:
                            continue
                        rows.append(
                            {
                                **event_info,
                                "display_group": display_group.get("description", ""),
                                "market": market.get("description", ""),
                                "period": period.get("description", ""),
                                "period_main": bool(period.get("main")),
                                "outcome": outcome.get("description", ""),
                                "outcome_type": outcome.get("type", ""),
                                "american": american,
                                "handicap": pd.to_numeric(
                                    price.get("handicap"), errors="coerce"
                                ),
                            }
                        )
    return all_events, rows


def build_team_metrics(results: pd.DataFrame) -> tuple[dict[str, dict], dict]:
    if results.empty:
        return {}, {"league_runs": 4.4, "league_runs_allowed": 4.4}
    metrics = {}
    league_runs = results["runs_for"].mean()
    for team, group in results.sort_values("date").groupby("team"):
        last10 = group.tail(10)
        home = group[group["is_home"]]
        away = group[~group["is_home"]]
        metrics[team] = {
            "games": len(group),
            "win_pct": group["win"].mean(),
            "runs_for": group["runs_for"].mean(),
            "runs_against": group["runs_against"].mean(),
            "run_diff": (group["runs_for"] - group["runs_against"]).mean(),
            "last10_win_pct": last10["win"].mean() if len(last10) else group["win"].mean(),
            "last10_runs_for": last10["runs_for"].mean()
            if len(last10)
            else group["runs_for"].mean(),
            "last10_runs_against": last10["runs_against"].mean()
            if len(last10)
            else group["runs_against"].mean(),
            "home_runs_for": home["runs_for"].mean() if len(home) else group["runs_for"].mean(),
            "away_runs_for": away["runs_for"].mean() if len(away) else group["runs_for"].mean(),
        }
    return metrics, {"league_runs": league_runs, "league_runs_allowed": league_runs}


def load_player_data(report_date: date) -> dict:
    season_dir = DATA_DIR / str(SEASON)
    prev_dir = DATA_DIR / str(SEASON - 1)
    pitch_logs = read_csv(season_dir / f"pitchers_gamelogs_{SEASON}_statsapi.csv")
    bat_logs = read_csv(season_dir / f"batters_gamelogs_{SEASON}_statsapi.csv")
    pitch_details = read_csv(season_dir / f"pitchers_details_{SEASON}_statsapi.csv")
    bat_details = read_csv(season_dir / f"batters_details_{SEASON}_statsapi.csv")
    prev_pitch_logs = read_csv(prev_dir / f"pitchers_gamelogs_{SEASON - 1}_statsapi.csv")
    prev_bat_logs = read_csv(prev_dir / f"batters_gamelogs_{SEASON - 1}_statsapi.csv")

    for df in [pitch_logs, bat_logs, prev_pitch_logs, prev_bat_logs]:
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df.drop(df[df["date"].dt.date >= report_date].index, inplace=True)

    pitch_logs = numeric(
        pitch_logs,
        [
            "gamesStarted",
            "strikeOuts",
            "battersFaced",
            "outs",
            "earnedRuns",
            "runs",
            "hits",
            "homeRuns",
            "totalBases",
            "atBats",
            "baseOnBalls",
        ],
    )
    prev_pitch_logs = numeric(
        prev_pitch_logs,
        [
            "gamesStarted",
            "strikeOuts",
            "battersFaced",
            "outs",
            "earnedRuns",
            "runs",
            "hits",
            "homeRuns",
            "totalBases",
            "atBats",
            "baseOnBalls",
        ],
    )
    bat_logs = numeric(
        bat_logs,
        [
            "plateAppearances",
            "atBats",
            "hits",
            "homeRuns",
            "totalBases",
            "runs",
            "rbi",
            "strikeOuts",
        ],
    )
    prev_bat_logs = numeric(
        prev_bat_logs,
        [
            "plateAppearances",
            "atBats",
            "hits",
            "homeRuns",
            "totalBases",
            "runs",
            "rbi",
            "strikeOuts",
        ],
    )

    name_to_batter = {}
    if not bat_details.empty:
        for _, row in bat_details.iterrows():
            name_to_batter[clean_name(row.get("fullName"))] = int(row["player_id"])
    name_to_pitcher = {}
    if not pitch_details.empty:
        for _, row in pitch_details.iterrows():
            name_to_pitcher[clean_name(row.get("fullName"))] = int(row["player_id"])

    return {
        "pitch_logs": pitch_logs,
        "bat_logs": bat_logs,
        "pitch_details": pitch_details,
        "bat_details": bat_details,
        "prev_pitch_logs": prev_pitch_logs,
        "prev_bat_logs": prev_bat_logs,
        "name_to_batter": name_to_batter,
        "name_to_pitcher": name_to_pitcher,
    }


def fetch_pitcher_gamelog(player_id: int, report_date: date) -> pd.DataFrame:
    try:
        data = fetch_json(
            f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
            {
                "stats": "gameLog",
                "season": SEASON,
                "group": "pitching",
                "gameType": "R",
            },
        )
    except Exception:
        return pd.DataFrame()
    stats = data.get("stats") or []
    if not stats:
        return pd.DataFrame()
    rows = []
    for split in stats[0].get("splits", []):
        if pd.to_datetime(split.get("date")).date() >= report_date:
            continue
        rows.append(
            {
                "player_id": player_id,
                "date": split.get("date"),
                "team": split.get("team", {}).get("name", ""),
                "opponent": split.get("opponent", {}).get("name", ""),
                **split.get("stat", {}),
            }
        )
    df = pd.DataFrame(rows)
    return numeric(
        df,
        [
            "gamesStarted",
            "strikeOuts",
            "battersFaced",
            "outs",
            "earnedRuns",
            "runs",
            "hits",
            "homeRuns",
            "totalBases",
            "atBats",
            "baseOnBalls",
        ],
    )


def pitcher_metrics(
    player_id: int | None,
    name: str | None,
    data: dict,
    report_date: date,
    live_cache: dict[int, pd.DataFrame],
) -> dict:
    if player_id is None and name:
        player_id = data["name_to_pitcher"].get(clean_name(name))
    current = pd.DataFrame()
    if player_id is not None:
        if player_id not in live_cache:
            live_cache[player_id] = fetch_pitcher_gamelog(player_id, report_date)
        current = live_cache[player_id]
        if current.empty:
            current = data["pitch_logs"][data["pitch_logs"].get("player_id") == player_id]
    previous = pd.DataFrame()
    if player_id is not None and not data["prev_pitch_logs"].empty:
        previous = data["prev_pitch_logs"][
            data["prev_pitch_logs"].get("player_id") == player_id
        ]

    starts = (
        current[current["gamesStarted"] > 0].copy()
        if "gamesStarted" in current.columns
        else pd.DataFrame()
    )
    prev_starts = (
        previous[previous["gamesStarted"] > 0].copy()
        if "gamesStarted" in previous.columns
        else pd.DataFrame()
    )
    sample = starts if not starts.empty else current
    if sample.empty:
        sample = prev_starts
    if sample.empty:
        return {
            "player_id": player_id,
            "starts": 0,
            "bf_avg": 22.0,
            "outs_avg": 14.0,
            "k_avg": 4.2,
            "er_avg": 2.4,
            "k_per_bf": 0.19,
            "hits_per_ab": 0.245,
            "slg_allowed": 0.390,
            "hr_per_bf": 0.030,
            "last3_k": 4.2,
            "last3_outs": 14.0,
        }

    def safe_div(a: float, b: float, default: float) -> float:
        return default if b == 0 else a / b

    last3 = sample.sort_values("date").tail(3)
    bf = sample["battersFaced"].sum()
    at_bats = sample["atBats"].sum()
    metrics = {
        "player_id": player_id,
        "starts": int(len(starts)) if not starts.empty else int(len(sample)),
        "bf_avg": sample["battersFaced"].mean() if sample["battersFaced"].sum() else 22.0,
        "outs_avg": sample["outs"].mean() if sample["outs"].sum() else 14.0,
        "k_avg": sample["strikeOuts"].mean(),
        "er_avg": sample["earnedRuns"].mean(),
        "k_per_bf": safe_div(sample["strikeOuts"].sum(), bf, 0.19),
        "hits_per_ab": safe_div(sample["hits"].sum(), at_bats, 0.245),
        "slg_allowed": safe_div(sample["totalBases"].sum(), at_bats, 0.390),
        "hr_per_bf": safe_div(sample["homeRuns"].sum(), bf, 0.030),
        "last3_k": last3["strikeOuts"].mean(),
        "last3_outs": last3["outs"].mean(),
    }
    if len(starts) < 3 and not prev_starts.empty:
        prev_bf = prev_starts["battersFaced"].sum()
        prev_ab = prev_starts["atBats"].sum()
        metrics["k_per_bf"] = 0.55 * metrics["k_per_bf"] + 0.45 * safe_div(
            prev_starts["strikeOuts"].sum(), prev_bf, metrics["k_per_bf"]
        )
        metrics["hits_per_ab"] = 0.55 * metrics["hits_per_ab"] + 0.45 * safe_div(
            prev_starts["hits"].sum(), prev_ab, metrics["hits_per_ab"]
        )
        metrics["slg_allowed"] = 0.55 * metrics["slg_allowed"] + 0.45 * safe_div(
            prev_starts["totalBases"].sum(), prev_ab, metrics["slg_allowed"]
        )
        metrics["hr_per_bf"] = 0.55 * metrics["hr_per_bf"] + 0.45 * safe_div(
            prev_starts["homeRuns"].sum(), prev_bf, metrics["hr_per_bf"]
        )
    return metrics


def build_batter_context(data: dict) -> dict:
    bat_logs = data["bat_logs"]
    if bat_logs.empty:
        return {
            "league_k_pa": 0.225,
            "league_hit_rate": 0.66,
            "league_tb2_rate": 0.36,
            "league_hr_pa": 0.030,
            "team_k_pa": {},
            "team_hr_pa": {},
        }
    pa = bat_logs["plateAppearances"].replace(0, pd.NA)
    league_k_pa = (bat_logs["strikeOuts"].sum() / bat_logs["plateAppearances"].sum())
    game_rows = bat_logs[bat_logs["plateAppearances"] > 0].copy()
    team_totals = game_rows.groupby("team")[["strikeOuts", "plateAppearances"]].sum()
    team_k_pa = (
        team_totals["strikeOuts"] / team_totals["plateAppearances"].clip(lower=1)
    ).to_dict()
    team_hr_pa = (
        team_totals.reindex(columns=["plateAppearances"]).assign(
            homeRuns=game_rows.groupby("team")["homeRuns"].sum()
        )["homeRuns"]
        / team_totals["plateAppearances"].clip(lower=1)
    ).to_dict()
    league_hr_pa = game_rows["homeRuns"].sum() / max(game_rows["plateAppearances"].sum(), 1)
    return {
        "league_k_pa": league_k_pa if math.isfinite(league_k_pa) else 0.225,
        "league_hit_rate": (game_rows["hits"] >= 1).mean(),
        "league_tb2_rate": (game_rows["totalBases"] >= 2).mean(),
        "league_hr_pa": league_hr_pa if math.isfinite(league_hr_pa) else 0.030,
        "team_k_pa": team_k_pa,
        "team_hr_pa": team_hr_pa,
    }


def blended_rate(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    predicate,
    league_rate: float,
) -> tuple[float, int, int]:
    current = current[current["plateAppearances"] > 0].sort_values("date")
    previous = previous[previous["plateAppearances"] > 0].sort_values("date")
    parts = []
    if len(current):
        parts.append((predicate(current).mean(), min(len(current), 35)))
        last10 = current.tail(10)
        parts.append((predicate(last10).mean(), min(len(last10), 10) * 1.25))
    if len(previous):
        parts.append((predicate(previous).mean(), min(len(previous), 100) * 0.20))
    parts.append((league_rate, 10))
    weight = sum(w for _, w in parts)
    value = sum(rate * w for rate, w in parts) / weight
    return float(max(0.02, min(0.98, value))), len(current), len(previous)


def batter_prop_probability(
    player_name: str,
    prop: str,
    line: float | None,
    player_team: str | None,
    opposing_pitcher: dict | None,
    team_projected_runs: float | None,
    data: dict,
    context: dict,
) -> tuple[float | None, str]:
    player_id = data["name_to_batter"].get(clean_name(player_name))
    if player_id is None:
        return None, "No local hitter match"
    current = data["bat_logs"][data["bat_logs"].get("player_id") == player_id]
    previous = data["prev_bat_logs"][data["prev_bat_logs"].get("player_id") == player_id]
    if current.empty and previous.empty:
        return None, "No game-log sample"

    lg_hit = context.get("league_hit_rate", 0.66)
    lg_tb2 = context.get("league_tb2_rate", 0.36)
    lg_run = 0.40
    lg_rbi = 0.35

    if prop == "hit":
        prob, n_cur, n_prev = blended_rate(current, previous, lambda df: df["hits"] >= 1, lg_hit)
        if opposing_pitcher:
            prob += (opposing_pitcher["hits_per_ab"] - 0.245) * 0.32
    elif prop == "2hits":
        prob, n_cur, n_prev = blended_rate(current, previous, lambda df: df["hits"] >= 2, 0.20)
        if opposing_pitcher:
            prob += (opposing_pitcher["hits_per_ab"] - 0.245) * 0.20
    elif prop == "tb_over":
        threshold = 2 if line is None else int(math.floor(line + 1))
        prob, n_cur, n_prev = blended_rate(
            current,
            previous,
            lambda df: df["totalBases"] >= threshold,
            lg_tb2 if threshold == 2 else 0.22,
        )
        if opposing_pitcher:
            prob += (opposing_pitcher["slg_allowed"] - 0.390) * 0.26
    elif prop == "hrrbi_over":
        threshold = 1 if line is None else int(math.floor(line + 1))
        prob, n_cur, n_prev = blended_rate(
            current,
            previous,
            lambda df: (df["hits"] + df["runs"] + df["rbi"]) >= threshold,
            0.52 if threshold == 1 else 0.34,
        )
        if team_projected_runs is not None:
            prob += (team_projected_runs - 4.4) * 0.025
    elif prop == "run":
        prob, n_cur, n_prev = blended_rate(current, previous, lambda df: df["runs"] >= 1, lg_run)
        if team_projected_runs is not None:
            prob += (team_projected_runs - 4.4) * 0.030
    elif prop == "rbi":
        prob, n_cur, n_prev = blended_rate(current, previous, lambda df: df["rbi"] >= 1, lg_rbi)
        if team_projected_runs is not None:
            prob += (team_projected_runs - 4.4) * 0.025
    else:
        return None, "Unsupported hitter prop"

    prob = float(max(0.02, min(0.96, prob)))
    note = f"{n_cur} current games, {n_prev} prior-year games"
    return prob, note


def project_games(
    games: list[dict],
    team_metrics: dict[str, dict],
    league: dict,
    data: dict,
    report_date: date,
) -> tuple[dict[str, dict], dict[int, pd.DataFrame]]:
    live_pitcher_cache: dict[int, pd.DataFrame] = {}
    starter_samples = []
    for game in games:
        for side in ["away", "home"]:
            starter_samples.append(
                pitcher_metrics(
                    game.get(f"{side}_probable_id"),
                    game.get(f"{side}_probable"),
                    data,
                    report_date,
                    live_pitcher_cache,
                )
            )
    league_starter_er = (
        sum(m["er_avg"] for m in starter_samples) / max(len(starter_samples), 1)
    )
    league_starter_er = league_starter_er if league_starter_er else 2.4

    projections = {}
    league_runs = league.get("league_runs", 4.4)

    def team_runs(team: str, opp: str, starter: dict, is_home: bool) -> float:
        tm = team_metrics.get(team, {})
        om = team_metrics.get(opp, {})
        base = (
            0.36 * tm.get("runs_for", league_runs)
            + 0.24 * tm.get("last10_runs_for", tm.get("runs_for", league_runs))
            + 0.26 * om.get("runs_against", league_runs)
            + 0.14 * om.get("last10_runs_against", om.get("runs_against", league_runs))
        )
        starter_adj = (starter.get("er_avg", league_starter_er) - league_starter_er) * 0.34
        home_adj = 0.12 if is_home else -0.03
        return float(max(2.2, min(7.0, base + starter_adj + home_adj)))

    for game in games:
        away_starter = pitcher_metrics(
            game.get("away_probable_id"),
            game.get("away_probable"),
            data,
            report_date,
            live_pitcher_cache,
        )
        home_starter = pitcher_metrics(
            game.get("home_probable_id"),
            game.get("home_probable"),
            data,
            report_date,
            live_pitcher_cache,
        )
        away_runs = team_runs(game["away_team"], game["home_team"], home_starter, False)
        home_runs = team_runs(game["home_team"], game["away_team"], away_starter, True)
        margin = home_runs - away_runs
        projections[game["gamePk"]] = {
            **game,
            "away_runs": away_runs,
            "home_runs": home_runs,
            "total_runs": away_runs + home_runs,
            "home_margin": margin,
            "home_win_prob": max(0.08, min(0.92, norm_cdf(margin / 4.15))),
            "away_starter_metrics": away_starter,
            "home_starter_metrics": home_starter,
        }
    return projections, live_pitcher_cache


def match_projection(event: dict, projections: dict[str, dict]) -> dict | None:
    for projection in projections.values():
        if (
            projection["home_team"] == event["home_team"]
            and projection["away_team"] == event["away_team"]
        ):
            return projection
    return None


def no_vig_probs(rows: list[dict]) -> dict[int, float]:
    implied = {i: implied_probability(row["american"]) for i, row in enumerate(rows)}
    total = sum(implied.values())
    if total <= 0:
        return {}
    return {i: val / total for i, val in implied.items()}


def add_pick(
    picks: list[dict],
    market: str,
    selection: str,
    game: str,
    line: str,
    american: int,
    model_p: float,
    market_p: float,
    rationale: str,
    source: str,
    sample: str,
) -> None:
    if not (0.01 <= model_p <= 0.99):
        return
    edge = model_p - market_p
    ev = expected_value(model_p, american)
    if ev < -0.03:
        return
    if american < -350 or american > 900:
        return
    if edge < -0.015:
        return
    if edge >= 0.09 and ev >= 0.09:
        confidence = "A"
    elif edge >= 0.055 and ev >= 0.055:
        confidence = "B"
    elif edge >= 0.025 and ev >= 0.025:
        confidence = "C"
    else:
        confidence = "Lean"
    if american >= 650 and confidence in {"A", "B"}:
        confidence = "C"
    elif american >= 450 and confidence == "A":
        confidence = "B"
    picks.append(
        {
            "market": market,
            "selection": selection,
            "game": game,
            "line": line,
            "odds": f"{american:+d}" if american != 100 else "+100",
            "model_p": model_p,
            "market_p": market_p,
            "edge": edge,
            "ev": ev,
            "fair_odds": fair_american(model_p),
            "confidence": confidence,
            "rationale": rationale,
            "source": source,
            "sample": sample,
            "score": ev * 100 + edge * 45 + (0.8 if confidence == "A" else 0),
        }
    )


def entity_key(pick: dict) -> str:
    selection = pick["selection"]
    if pick["market"] == "Pitcher strikeouts":
        match = re.match(r"(.+?)\s+(?:Over|Under|\d+\+ Strikeouts)", selection)
        return f"pitcher:{clean_name(match.group(1) if match else selection)}"
    if pick["market"] == "Player prop":
        name = re.sub(
            r"\s+(?:1\+ Hit|2\+ Hits|Run|RBI|Over .*|Under .*)$",
            "",
            selection,
        )
        return f"player:{clean_name(name)}"
    if pick["market"] in {"Moneyline", "Runline", "Total"}:
        return f"game:{pick['game']}:{pick['market']}"
    return clean_name(selection)


def curate_top_picks(picks: list[dict], limit: int = 20) -> list[dict]:
    curated: list[dict] = []
    seen_entities: set[str] = set()
    seen_exact: set[str] = set()
    game_counts: dict[str, int] = {}

    for pick in picks:
        key = entity_key(pick)
        exact = f"{pick['market']}:{pick['selection']}:{pick['game']}"
        if exact in seen_exact:
            continue
        if key in seen_entities:
            continue
        if game_counts.get(pick["game"], 0) >= 4:
            continue
        curated.append(pick)
        seen_entities.add(key)
        seen_exact.add(exact)
        game_counts[pick["game"]] = game_counts.get(pick["game"], 0) + 1
        if len(curated) == limit:
            return curated

    for pick in picks:
        exact = f"{pick['market']}:{pick['selection']}:{pick['game']}"
        if exact in seen_exact:
            continue
        if game_counts.get(pick["game"], 0) >= 4:
            continue
        curated.append(pick)
        seen_exact.add(exact)
        game_counts[pick["game"]] = game_counts.get(pick["game"], 0) + 1
        if len(curated) == limit:
            break
    if len(curated) < limit:
        for pick in picks:
            exact = f"{pick['market']}:{pick['selection']}:{pick['game']}"
            if exact in seen_exact:
                continue
            curated.append(pick)
            seen_exact.add(exact)
            if len(curated) == limit:
                break
    return curated


def score_game_markets(market_rows: list[dict], projections: dict[str, dict]) -> list[dict]:
    picks: list[dict] = []
    df = pd.DataFrame(market_rows)
    if df.empty:
        return picks
    game_lines = df[
        (df["display_group"] == "Game Lines")
        & (df["period"] == "Game")
        & (df["period_main"])
        & (df["market"].isin(["Moneyline", "Runline", "Total"]))
    ]
    for event_id, event_rows in game_lines.groupby("event_id"):
        event = event_rows.iloc[0].to_dict()
        projection = match_projection(event, projections)
        if projection is None:
            continue
        game_label = f"{event['away_team']} @ {event['home_team']}"
        for market, group in event_rows.groupby("market"):
            rows = group.to_dict("records")
            market_probs = no_vig_probs(rows) if len(rows) == 2 else {}
            for idx, row in enumerate(rows):
                team = row["outcome"]
                if market == "Moneyline":
                    if team == projection["home_team"]:
                        model_p = projection["home_win_prob"]
                    elif team == projection["away_team"]:
                        model_p = 1 - projection["home_win_prob"]
                    else:
                        continue
                    line = "ML"
                    rationale = (
                        f"Projected {projection['away_team']} {projection['away_runs']:.1f}, "
                        f"{projection['home_team']} {projection['home_runs']:.1f}; "
                        f"season/last-10 run blend supports {team}."
                    )
                elif market == "Runline":
                    handicap = float(row["handicap"])
                    if team == projection["home_team"]:
                        mean_margin = projection["home_margin"]
                    elif team == projection["away_team"]:
                        mean_margin = -projection["home_margin"]
                    else:
                        continue
                    model_p = prob_normal_greater(mean_margin, 4.2, -handicap)
                    line = f"{handicap:+.1f}"
                    rationale = (
                        f"Projected margin {mean_margin:+.2f} for {team}; "
                        f"run environment {projection['total_runs']:.1f}."
                    )
                else:
                    total_line = float(row["handicap"])
                    if row["outcome"] == "Over":
                        model_p = prob_normal_greater(projection["total_runs"], 3.35, total_line)
                    elif row["outcome"] == "Under":
                        model_p = 1 - prob_normal_greater(
                            projection["total_runs"], 3.35, total_line
                        )
                    else:
                        continue
                    line = f"{row['outcome']} {total_line:.1f}"
                    rationale = (
                        f"Projected total {projection['total_runs']:.1f}; starter and recent "
                        "team run rates drive the number."
                    )
                add_pick(
                    picks,
                    market,
                    team if market != "Total" else f"{row['outcome']} {row['handicap']:.1f}",
                    game_label,
                    line,
                    int(row["american"]),
                    model_p,
                    market_probs.get(idx, implied_probability(int(row["american"]))),
                    rationale,
                    "Bovada game lines",
                    "StatsAPI team form through yesterday",
                )
    return picks


def score_pitcher_props(
    market_rows: list[dict],
    projections: dict[str, dict],
    data: dict,
    context: dict,
    report_date: date,
    live_pitcher_cache: dict[int, pd.DataFrame],
) -> list[dict]:
    picks: list[dict] = []
    df = pd.DataFrame(market_rows)
    if df.empty:
        return picks
    props = df[df["display_group"] == "Pitcher Props"]
    probable_by_name = {}
    pitcher_team = {}
    for projection in projections.values():
        probable_by_name[clean_name(projection.get("away_probable"))] = (
            projection.get("away_probable_id"),
            projection,
            projection["home_team"],
        )
        probable_by_name[clean_name(projection.get("home_probable"))] = (
            projection.get("home_probable_id"),
            projection,
            projection["away_team"],
        )
        pitcher_team[clean_name(projection.get("away_probable"))] = projection["away_team"]
        pitcher_team[clean_name(projection.get("home_probable"))] = projection["home_team"]

    for event_id, event_rows in props.groupby("event_id"):
        event = event_rows.iloc[0].to_dict()
        game_label = f"{event['away_team']} @ {event['home_team']}"
        projection = match_projection(event, projections)
        if projection is None:
            continue
        for market, group in event_rows.groupby("market"):
            total_match = re.match(r"Total Strikeouts - (.+?) \(([A-Z]{2,3})\)", market)
            alt_match = re.match(r"Alternate Strikeouts - (.+?) \(([A-Z]{2,3})\)", market)
            if not total_match and not alt_match:
                continue
            pitcher_name = (total_match or alt_match).group(1)
            key = clean_name(pitcher_name)
            player_id, matched_projection, opponent = probable_by_name.get(
                key, (data["name_to_pitcher"].get(key), projection, None)
            )
            if opponent is None:
                team = CODE_TO_TEAM.get((total_match or alt_match).group(2))
                if team == projection["away_team"]:
                    opponent = projection["home_team"]
                elif team == projection["home_team"]:
                    opponent = projection["away_team"]
            metrics = pitcher_metrics(player_id, pitcher_name, data, report_date, live_pitcher_cache)
            if metrics["starts"] < 3:
                continue
            opp_k_rate = context["team_k_pa"].get(opponent, context["league_k_pa"])
            projected_bf = 0.58 * metrics["bf_avg"] + 0.42 * (
                metrics["last3_outs"] / max(metrics["outs_avg"], 1) * metrics["bf_avg"]
            )
            projected_bf = max(13, min(30, projected_bf))
            projected_k_rate = metrics["k_per_bf"] + (opp_k_rate - context["league_k_pa"]) * 0.62
            projected_k_rate = max(0.10, min(0.37, projected_k_rate))
            projected_ks = projected_bf * projected_k_rate
            sample = (
                f"{metrics['starts']} starts, last3 {metrics['last3_k']:.1f} K, "
                f"opp K/PA {opp_k_rate:.1%}"
            )

            rows = group.to_dict("records")
            market_probs = no_vig_probs(rows) if total_match and len(rows) == 2 else {}
            for idx, row in enumerate(rows):
                if total_match:
                    line_value = float(row["handicap"])
                    threshold = int(math.floor(line_value) + 1)
                    over_p = poisson_ge(threshold, projected_ks)
                    model_p = over_p if row["outcome"] == "Over" else 1 - over_p
                    line = f"{row['outcome']} {line_value:.1f} K"
                    selection = f"{pitcher_name} {line}"
                    market_p = market_probs.get(idx, implied_probability(int(row["american"])))
                else:
                    match = re.match(r"(\d+)\+\s+Strikeouts", row["outcome"])
                    if not match:
                        continue
                    threshold = int(match.group(1))
                    model_p = poisson_ge(threshold, projected_ks)
                    line = f"{threshold}+ K"
                    selection = f"{pitcher_name} {threshold}+ Strikeouts"
                    market_p = implied_probability(int(row["american"]))
                rationale = (
                    f"Projected {projected_ks:.2f} Ks from {projected_bf:.1f} BF; "
                    f"pitcher K/BF {metrics['k_per_bf']:.1%} vs opponent K/PA {opp_k_rate:.1%}."
                )
                add_pick(
                    picks,
                    "Pitcher strikeouts",
                    selection,
                    game_label,
                    line,
                    int(row["american"]),
                    model_p,
                    market_p,
                    rationale,
                    "Bovada pitcher props",
                    sample,
                )
    return picks


def score_player_props(
    market_rows: list[dict],
    projections: dict[str, dict],
    data: dict,
    context: dict,
    report_date: date,
    live_pitcher_cache: dict[int, pd.DataFrame],
) -> list[dict]:
    picks: list[dict] = []
    df = pd.DataFrame(market_rows)
    if df.empty:
        return picks
    props = df[df["display_group"] == "Player Props"]
    projection_by_event = {
        row["event_id"]: match_projection(row, projections)
        for row in props.drop_duplicates("event_id").to_dict("records")
    }

    for event_id, event_rows in props.groupby("event_id"):
        event = event_rows.iloc[0].to_dict()
        projection = projection_by_event.get(event_id)
        if projection is None:
            continue
        game_label = f"{event['away_team']} @ {event['home_team']}"
        team_projected = {
            event["away_team"]: projection["away_runs"],
            event["home_team"]: projection["home_runs"],
        }
        starters = {
            event["away_team"]: pitcher_metrics(
                projection.get("away_probable_id"),
                projection.get("away_probable"),
                data,
                report_date,
                live_pitcher_cache,
            ),
            event["home_team"]: pitcher_metrics(
                projection.get("home_probable_id"),
                projection.get("home_probable"),
                data,
                report_date,
                live_pitcher_cache,
            ),
        }

        for market, group in event_rows.groupby("market"):
            rows = group.to_dict("records")
            market_probs = no_vig_probs(rows) if len(rows) == 2 and rows[0]["outcome"] in {"Over", "Under"} else {}
            for idx, row in enumerate(rows):
                player_name = None
                prop = None
                line_value = None
                side_prefix = ""
                if market == "Player to record a Hit":
                    player_name, team_code = parse_player_team(row["outcome"])
                    prop = "hit"
                    side_prefix = "1+ Hit"
                elif market == "Player to record 2+ Hits":
                    player_name, team_code = parse_player_team(row["outcome"])
                    prop = "2hits"
                    side_prefix = "2+ Hits"
                elif market == "Player to record a Run":
                    player_name, team_code = parse_player_team(row["outcome"])
                    prop = "run"
                    side_prefix = "Run"
                elif market == "Player to record a RBI":
                    player_name, team_code = parse_player_team(row["outcome"])
                    prop = "rbi"
                    side_prefix = "RBI"
                else:
                    tb_match = re.match(r"Total Bases - (.+?) \(([A-Z]{2,3})\)", market)
                    hrrbi_match = re.match(
                        r"Total Hits, Runs and RBIs - (.+?) \(([A-Z]{2,3})\)", market
                    )
                    if tb_match:
                        player_name, team_code = tb_match.group(1), tb_match.group(2)
                        prop = "tb_over"
                        line_value = float(row["handicap"])
                        side_prefix = f"{row['outcome']} {line_value:.1f} TB"
                    elif hrrbi_match:
                        player_name, team_code = hrrbi_match.group(1), hrrbi_match.group(2)
                        prop = "hrrbi_over"
                        line_value = float(row["handicap"])
                        side_prefix = f"{row['outcome']} {line_value:.1f} H+R+RBI"
                    else:
                        continue
                    if row["outcome"] != "Over":
                        continue
                player_team = CODE_TO_TEAM.get(team_code)
                if player_team == event["away_team"]:
                    opposing_team = event["home_team"]
                elif player_team == event["home_team"]:
                    opposing_team = event["away_team"]
                else:
                    opposing_team = None
                opposing_pitcher = starters.get(opposing_team) if opposing_team else None
                prob, sample = batter_prop_probability(
                    player_name,
                    prop,
                    line_value,
                    player_team,
                    opposing_pitcher,
                    team_projected.get(player_team),
                    data,
                    context,
                )
                if prob is None:
                    continue
                market_p = market_probs.get(idx, implied_probability(int(row["american"])))
                rationale = (
                    f"{sample}; adjusted for opposing starter contact profile and "
                    f"{player_team or 'team'} projected runs."
                )
                add_pick(
                    picks,
                    "Player prop",
                    f"{player_name} {side_prefix}",
                    game_label,
                    side_prefix,
                    int(row["american"]),
                    prob,
                    market_p,
                    rationale,
                    "Bovada player props",
                    sample,
                )
    return picks


def blended_hr_rate(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    league_hr_pa: float,
) -> tuple[float, dict]:
    current = current[current["plateAppearances"] > 0].sort_values("date")
    previous = previous[previous["plateAppearances"] > 0].sort_values("date")
    last10 = current.tail(10)

    def rate(df: pd.DataFrame) -> float:
        return df["homeRuns"].sum() / max(df["plateAppearances"].sum(), 1)

    parts = [(league_hr_pa, 180)]
    if len(previous):
        parts.append((rate(previous), min(previous["plateAppearances"].sum(), 500) * 0.12))
    if len(current):
        parts.append((rate(current), min(current["plateAppearances"].sum(), 150) * 0.65))
    if len(last10):
        parts.append((rate(last10), min(last10["plateAppearances"].sum(), 45) * 0.30))

    total_weight = sum(weight for _, weight in parts)
    blended = sum(value * weight for value, weight in parts) / max(total_weight, 1)
    if len(current) < 25 and current["plateAppearances"].sum() < 80:
        blended = 0.65 * blended + 0.35 * league_hr_pa
    return (
        max(0.002, min(0.085, float(blended))),
        {
            "current_games": int(len(current)),
            "previous_games": int(len(previous)),
            "current_hr": int(current["homeRuns"].sum()) if len(current) else 0,
            "previous_hr": int(previous["homeRuns"].sum()) if len(previous) else 0,
            "current_pa": int(current["plateAppearances"].sum()) if len(current) else 0,
            "previous_pa": int(previous["plateAppearances"].sum()) if len(previous) else 0,
            "last10_hr": int(last10["homeRuns"].sum()) if len(last10) else 0,
            "current_hr_pa": rate(current) if len(current) else league_hr_pa,
            "last10_hr_pa": rate(last10) if len(last10) else league_hr_pa,
        },
    )


def score_home_run_batters(
    market_rows: list[dict],
    projections: dict[str, dict],
    data: dict,
    context: dict,
    weather_by_game: dict[str, dict],
    report_date: date,
    live_pitcher_cache: dict[int, pd.DataFrame],
) -> list[dict]:
    df = pd.DataFrame(market_rows)
    if df.empty:
        return []
    hr_rows = df[
        (df["display_group"] == "Player Props")
        & (df["market"] == "Player to hit a Home Run")
    ]
    if hr_rows.empty:
        return []

    league_hr_pa = max(context.get("league_hr_pa", 0.030), 0.015)
    league_pitcher_hr_bf = max(data["pitch_logs"]["homeRuns"].sum() / max(data["pitch_logs"]["battersFaced"].sum(), 1), 0.020)
    picks = []

    for _, row in hr_rows.iterrows():
        event = row.to_dict()
        projection = match_projection(event, projections)
        if projection is None:
            continue
        player_name, team_code = parse_player_team(row["outcome"])
        player_team = CODE_TO_TEAM.get(team_code)
        if player_team not in {event["away_team"], event["home_team"]}:
            continue
        opposing_team = event["home_team"] if player_team == event["away_team"] else event["away_team"]
        opposing_pitcher_id = (
            projection.get("home_probable_id")
            if player_team == event["away_team"]
            else projection.get("away_probable_id")
        )
        opposing_pitcher_name = (
            projection.get("home_probable")
            if player_team == event["away_team"]
            else projection.get("away_probable")
        )
        opposing_pitcher = pitcher_metrics(
            opposing_pitcher_id,
            opposing_pitcher_name,
            data,
            report_date,
            live_pitcher_cache,
        )
        player_id = data["name_to_batter"].get(clean_name(player_name))
        if player_id is None:
            continue
        current = data["bat_logs"][data["bat_logs"].get("player_id") == player_id]
        previous = data["prev_bat_logs"][data["prev_bat_logs"].get("player_id") == player_id]
        if current.empty and previous.empty:
            continue

        base_hr_pa, sample = blended_hr_rate(current, previous, league_hr_pa)
        combined_hr = sample["current_hr"] + sample["previous_hr"]
        combined_pa = sample["current_pa"] + sample["previous_pa"]
        if combined_hr == 0:
            continue
        if sample["current_hr"] == 0 and sample["previous_hr"] < 8:
            continue
        if combined_pa >= 120 and combined_hr < 2:
            continue
        if base_hr_pa < league_hr_pa * 0.48 and sample["last10_hr"] == 0:
            continue
        projected_team_runs = (
            projection["away_runs"]
            if player_team == event["away_team"]
            else projection["home_runs"]
        )
        projected_pa = max(3.65, min(4.85, 4.18 + (projected_team_runs - 4.4) * 0.10))
        pitcher_hr_factor = max(
            0.82,
            min(1.32, 0.82 + 0.18 * opposing_pitcher["hr_per_bf"] / league_pitcher_hr_bf),
        )
        pitcher_slg_factor = max(
            0.92,
            min(1.12, 1 + (opposing_pitcher["slg_allowed"] - 0.390) * 0.18),
        )
        team_power_factor = max(
            0.90,
            min(
                1.12,
                1
                + (
                    context["team_hr_pa"].get(player_team, league_hr_pa)
                    - league_hr_pa
                )
                * 1.2,
            ),
        )
        run_env_factor = max(0.91, min(1.10, 1 + (projected_team_runs - 4.4) * 0.020))
        weather = weather_by_game.get(projection["gamePk"], {})
        park_weather_factor = 1 + (float(weather.get("total_hr_factor", 1.0)) - 1) * 0.75
        matchup_hr_pa = (
            base_hr_pa
            * pitcher_hr_factor
            * pitcher_slg_factor
            * team_power_factor
            * run_env_factor
            * park_weather_factor
        )
        model_p = max(0.006, min(0.23, 1 - math.exp(-projected_pa * matchup_hr_pa)))
        combined_hr_pa = combined_hr / max(combined_pa, 1)
        if combined_pa >= 180 and combined_hr_pa < league_hr_pa * 0.60:
            model_p = min(model_p, 0.065)
        elif combined_pa >= 180 and combined_hr_pa < league_hr_pa * 0.80:
            model_p = min(model_p, 0.085)
        american = int(row["american"])
        market_p = implied_probability(american)
        edge = model_p - market_p
        ev = expected_value(model_p, american)
        weather_note = weather.get("note", "weather neutral")
        rationale = (
            f"{sample['current_hr']} HR in {sample['current_games']} current games, "
            f"{sample['previous_hr']} prior-year HR, {sample['last10_hr']} HR last 10; "
            f"starter HR/BF "
            f"{opposing_pitcher['hr_per_bf']:.1%}, SLG allowed "
            f"{opposing_pitcher['slg_allowed']:.3f}; {projection['venue']} "
            f"{park_weather_factor:.2f}x HR context ({weather_note})."
        )
        if american >= 1000:
            confidence = "Spec"
        elif american <= 600 and edge >= 0.025 and ev >= 0.15:
            confidence = "A"
        elif edge >= 0.012 and ev >= 0.10:
            confidence = "B"
        elif edge >= 0.004 and ev >= 0.02:
            confidence = "C"
        else:
            confidence = "Lean"
        if edge <= 0 or ev <= 0:
            continue
        picks.append(
            {
                "market": "Home run",
                "selection": f"{player_name} HR",
                "game": f"{event['away_team']} @ {event['home_team']}",
                "team": player_team,
                "opposing_pitcher": opposing_pitcher_name or "TBD",
                "venue": projection["venue"],
                "odds": f"{american:+d}" if american != 100 else "+100",
                "model_p": model_p,
                "market_p": market_p,
                "edge": edge,
                "ev": ev,
                "fair_odds": fair_american(model_p),
                "confidence": confidence,
                "hr_pa": matchup_hr_pa,
                "park_weather_factor": park_weather_factor,
                "weather": weather_note,
                "rationale": rationale,
                "score": (
                    ev * 55
                    + edge * 75
                    + model_p * 115
                    + min(sample["current_hr"], 6) * 1.2
                    + sample["last10_hr"] * 1.5
                    + (park_weather_factor - 1) * 8
                    - (8 if american >= 1000 else 0)
                    - (5 if sample["current_hr"] == 0 else 0)
                ),
            }
        )

    picks = sorted(picks, key=lambda pick: pick["score"], reverse=True)
    curated = []
    seen_players = set()
    game_counts: dict[str, int] = {}
    for pick in picks:
        key = clean_name(pick["selection"])
        if key in seen_players:
            continue
        if game_counts.get(pick["game"], 0) >= 4:
            continue
        curated.append(pick)
        seen_players.add(key)
        game_counts[pick["game"]] = game_counts.get(pick["game"], 0) + 1
        if len(curated) == PICK_LIMIT:
            break
    if len(curated) < PICK_LIMIT:
        for pick in picks:
            key = clean_name(pick["selection"])
            if key in seen_players:
                continue
            curated.append(pick)
            seen_players.add(key)
            if len(curated) == PICK_LIMIT:
                break
    return curated


def write_report(
    report_date: date,
    run_time: datetime,
    games: list[dict],
    bovada_events: list[dict],
    projections: dict[str, dict],
    picks: list[dict],
    hr_picks: list[dict],
    candidate_count: int,
    output_md: Path,
    output_csv: Path,
    hr_output_csv: Path,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    top = picks[:PICK_LIMIT]
    pd.DataFrame(top).to_csv(output_csv, index=False)
    pd.DataFrame(hr_picks[:PICK_LIMIT]).to_csv(hr_output_csv, index=False)

    lines = [
        f"# Daily MLB Betting Edge Report - {report_date:%B %-d, %Y}",
        "",
        f"Generated: {run_time:%Y-%m-%d %I:%M %p %Z}",
        "",
        "## Executive Summary",
        "",
        (
            f"- Slate checked: {len(games)} MLB scheduled games from MLB StatsAPI; "
            f"{len(bovada_events)} Bovada events matched for today's date."
        ),
        (
            f"- Candidates scored: {candidate_count}; top {len(top)} are curated by "
            "model EV, probability edge, sample quality, and correlation control."
        ),
        "- Core inputs: current-season team form, probable starters, pitcher K/BF, opponent K/PA, hitter game-log hit/TB/H+R+RBI rates, and live Bovada prices.",
        "- Practical note: verify lineups, scratches, pitcher changes, weather, and price movement before betting.",
        "",
        f"## Top {PICK_LIMIT} Bets And Props",
        "",
        "| # | Confidence | Market | Pick | Odds | Model | Implied | Edge | EV/$ | Fair | Why |",
        "|---:|:---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, pick in enumerate(top, 1):
        why = pick["rationale"].replace("|", "/")
        lines.append(
            f"| {i} | {pick['confidence']} | {pick['market']} | "
            f"{pick['selection']} ({pick['game']}) | {pick['odds']} | "
            f"{pct(pick['model_p'])} | {pct(pick['market_p'])} | "
            f"{pick['edge'] * 100:+.1f} pts | {pick['ev']:+.2f} | "
            f"{pick['fair_odds']} | {why} |"
        )

    lines.extend(
        [
            "",
            f"## Top {PICK_LIMIT} Home Run Batter Bets",
            "",
            "This is a separate HR-only card from the custom handicapper model. It uses live HR prices plus hitter power form, opposing starter damage profile, projected team runs, ballpark HR tendency, and forecast-hour weather.",
            "",
            "| # | Confidence | Batter | Odds | Model | Implied | Edge | EV/$ | Fair | Matchup Context |",
            "|---:|:---:|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for i, pick in enumerate(hr_picks[:PICK_LIMIT], 1):
        why = pick["rationale"].replace("|", "/")
        lines.append(
            f"| {i} | {pick['confidence']} | {pick['selection']} "
            f"({pick['game']}) | {pick['odds']} | {pct(pick['model_p'])} | "
            f"{pct(pick['market_p'])} | {pick['edge'] * 100:+.1f} pts | "
            f"{pick['ev']:+.2f} | {pick['fair_odds']} | {why} |"
        )

    lines.extend(
        [
            "",
            "## Game Projection Board",
            "",
            "| Game | Probables | Bovada ML/Total context | Model Score | Win Lean | Total Lean |",
            "|---|---|---|---:|---|---|",
        ]
    )
    market_df = pd.DataFrame()
    if output_csv.exists():
        market_df = pd.read_csv(output_csv)
    for projection in projections.values():
        game = f"{projection['away_team']} @ {projection['home_team']}"
        probables = (
            f"{projection.get('away_probable') or 'TBD'} vs "
            f"{projection.get('home_probable') or 'TBD'}"
        )
        score = f"{projection['away_runs']:.1f}-{projection['home_runs']:.1f}"
        win_lean = (
            projection["home_team"]
            if projection["home_win_prob"] >= 0.5
            else projection["away_team"]
        )
        win_prob = max(projection["home_win_prob"], 1 - projection["home_win_prob"])
        total_lean = f"{projection['total_runs']:.1f} projected runs"
        lines.append(
            f"| {game} | {probables} | Bovada feed captured in model | "
            f"{score} | {win_lean} {pct(win_prob)} | {total_lean} |"
        )

    lines.extend(
        [
            "",
            "## Method Notes",
            "",
            "- Game sides/totals: blended season and last-10 team run creation/prevention, home-field bump, and probable-starter run prevention.",
            "- Pitcher strikeouts: Poisson tail from projected batters faced, pitcher K/BF, last-three workload, and opponent K/PA.",
            "- Hitter props: current-season game-log rates blended with prior-year rates and league priors, adjusted for opposing starter contact profile and projected team runs.",
            "- Home run card: HR/PA blend from current season, last-10 form, prior-year sample, league prior, opposing starter HR/BF and SLG allowed, team HR/PA, game run environment, ballpark factor, and live forecast-hour weather.",
            "- Implied probabilities are no-vig for paired two-way markets and raw implied for one-sided player/alternate markets.",
            "",
            "## Source URLs",
            "",
            f"- MLB StatsAPI schedule: {MLB_SCHEDULE_URL}",
            f"- Bovada MLB JSON feed: {BOVADA_URL}",
            f"- Open-Meteo forecast API: {OPEN_METEO_URL}",
            "",
        ]
    )
    output_md.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily MLB betting edge report.")
    parser.add_argument(
        "--date",
        default=datetime.now(ET).date().isoformat(),
        help="Report date in YYYY-MM-DD, Eastern time.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_date = date.fromisoformat(args.date)
    run_time = datetime.now(ET)

    games = fetch_today_schedule(report_date)
    team_results = fetch_recent_team_results(report_date)
    team_metrics, league = build_team_metrics(team_results)
    data = load_player_data(report_date)
    context = build_batter_context(data)
    projections, live_pitcher_cache = project_games(
        games, team_metrics, league, data, report_date
    )
    weather_by_game = fetch_game_weather(games, report_date)
    bovada_events, market_rows = fetch_bovada_events(report_date)

    game_picks = score_game_markets(market_rows, projections)
    pitcher_picks = score_pitcher_props(
        market_rows, projections, data, context, report_date, live_pitcher_cache
    )
    player_picks = score_player_props(
        market_rows, projections, data, context, report_date, live_pitcher_cache
    )
    hr_picks = score_home_run_batters(
        market_rows,
        projections,
        data,
        context,
        weather_by_game,
        report_date,
        live_pitcher_cache,
    )

    all_picks = game_picks + pitcher_picks + player_picks
    all_picks = sorted(all_picks, key=lambda p: p["score"], reverse=True)
    top_picks = curate_top_picks(all_picks, limit=PICK_LIMIT)
    output_md = REPORTS_DIR / f"daily_mlb_report_{report_date.isoformat()}.md"
    output_csv = REPORTS_DIR / f"daily_mlb_report_{report_date.isoformat()}_top50.csv"
    hr_output_csv = REPORTS_DIR / f"daily_mlb_report_{report_date.isoformat()}_hr_top50.csv"
    write_report(
        report_date,
        run_time,
        games,
        bovada_events,
        projections,
        top_picks,
        hr_picks,
        len(all_picks),
        output_md,
        output_csv,
        hr_output_csv,
    )

    print(f"Report written: {output_md}")
    print(f"Top-{PICK_LIMIT} CSV written: {output_csv}")
    print(f"HR top-{PICK_LIMIT} CSV written: {hr_output_csv}")
    print(f"MLB games: {len(games)}")
    print(f"Bovada events: {len(bovada_events)}")
    print(f"Candidates scored: {len(all_picks)}")
    print(f"HR top-{PICK_LIMIT} picks: {len(hr_picks)}")
    print("Top 5:")
    for i, pick in enumerate(top_picks[:5], 1):
        print(
            f"{i}. {pick['selection']} {pick['odds']} | "
            f"model {pct(pick['model_p'])}, implied {pct(pick['market_p'])}, "
            f"edge {pick['edge'] * 100:+.1f} pts, EV {pick['ev']:+.2f}"
        )
    print("Top 5 HR:")
    for i, pick in enumerate(hr_picks[:5], 1):
        print(
            f"{i}. {pick['selection']} {pick['odds']} | "
            f"model {pct(pick['model_p'])}, implied {pct(pick['market_p'])}, "
            f"edge {pick['edge'] * 100:+.1f} pts, EV {pick['ev']:+.2f}"
        )


if __name__ == "__main__":
    main()
