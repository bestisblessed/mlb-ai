# MLB StatsAPI Data Collection

## Script Overview

### Team Game Logs
- **Scripts**: `statsapi_team_game_logs.py`, `statsapi_team_game_logs_loop.py`
- **Purpose**: Collect team-level game logs for entire MLB season
- **Endpoints**:
  - `GET /api/v1/schedule` (with teamId/sportId/season params)
  - `GET /api/v1/teams` (team IDs)
- **Features**:
  - _loop version accepts year as CLI argument
  - Captures perspective-specific columns (home/away, scores, result)
- **Columns**:
  - *Core Fields*: gameDate, gamePk, teams.home.team.id, teams.away.team.id
  - *Perspective Columns*:
    - perspective_team_id
    - perspective_is_home (bool)
    - perspective_opponent_id
    - perspective_team_runs
    - perspective_opp_runs  
    - perspective_result (W/L/T)
  - *Game Context*: venue.id, venue.name, status.detailedState
  - *Full flattening*: All available fields from schedule endpoint

### Pitcher Game Logs
- **Scripts**: `statsapi_pitcher_game_logs.py`, `statsapi_pitcher_game_logs_loop.py` 
- **Purpose**: Gather pitcher-specific game logs and player details
- **Endpoints**:
  - `GET /api/v1/people/{player_id}/stats` (group=pitching)
  - `GET /api/v1/teams/{team_id}/roster` (pitcher IDs)
  - `GET /api/v1/people/{player_id}` (metadata)
- **Outputs**:
  - Pitcher game logs CSV
  - Pitcher details CSV
- **Columns**:
  - *Identifier*: player_id, date, team, opponent
  - *Pitching Stats*:
    - inningsPitched, hits, runs, earnedRuns
    - homeRuns, baseOnBalls, strikeOuts
    - pitchesThrown, battersFaced
  - *Advanced*: groundOuts, airOuts, numberOfPitches
  - *Full stat spread*: 35+ metrics from pitching splits

### Batter Game Logs  
- **Scripts**: `statsapi_batter_game_logs.py`, `statsapi_batter_game_logs_loop.py`
- **Purpose**: Collect batter game logs and player details
- **Endpoints**:
  - `GET /api/v1/people/{player_id}/stats` (group=hitting)
  - `GET /api/v1/teams/{team_id}/roster` (non-pitcher IDs)
  - `GET /api/v1/people/{player_id}` (metadata)
- **Outputs**:
  - Batter game logs CSV  
  - Batter details CSV
- **Columns**:
  - *Identifier*: player_id, date, team, opponent
  - *Batting Stats*:
    - atBats, hits, homeRuns, rbi
    - totalBases, strikeOuts, baseOnBalls
    - leftOnBase, ops, avg
  - *Situational*: flyOuts, groundOuts, sacBunts
  - *Full stat spread*: 25+ metrics from hitting splits

### Player Details (Both Pitchers/Batters)
- **Columns**:
  - *Bio*: fullName, birthDate, height, weight
  - *Team*: currentTeam.id, primaryPosition.abbreviation
  - *Status*: active, rosterStatus, mlbDebutDate
  - *IDs*: id, link, firstName, lastName
  - *Full profile*: 40+ fields from people endpoint

## Execution Scripts

### run_scraper_statsapi.sh
```bash
#!/bin/bash
# Runs current year (2025) scrapers sequentially:
python statsapi_team_game_logs.py
python statsapi_pitcher_game_logs.py  
python statsapi_batter_game_logs.py
```

### run_scraper_statsapi_loop.sh  
```bash
#!/bin/bash
# Historical data collection (2010-2024):
for YEAR in {2010..2024}; do
  python statsapi_team_game_logs_loop.py $YEAR
  python statsapi_pitcher_game_logs_loop.py $YEAR
  python statsapi_batter_game_logs_loop.py $YEAR
done
```

## Common Features
- ThreadPoolExecutor for parallel requests (max 6 workers)
- Retry logic with exponential backoff (3 retries)
- Pandas DataFrames for CSV output
- Organized output structure: `data/{YEAR}/*.csv`
- Progress tracking with tqdm

## Usage
```bash
# Single year (2025)
./run_scraper_statsapi.sh

# Historical data (2010-2024)
./run_scraper_statsapi_loop.sh
```

> **Note**: All scripts use base endpoint `https://statsapi.mlb.com/api/v1`. Requires Python 3.8+ with requests, pandas, and tqdm. 