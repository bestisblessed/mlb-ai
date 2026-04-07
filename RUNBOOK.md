# MLB AI Seasonal Restart Runbook

Use this checklist when a new MLB season starts and you need to refresh both scraped data and the Streamlit dashboard.

## 1) Environment setup (once per machine)

```bash
cd /workspace/mlb-ai
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r Streamlit/requirements.txt
python -m pip install requests pandas tqdm MLB-StatsAPI
```

## 2) Pull latest code

```bash
cd /workspace/mlb-ai
git pull
```

## 3) Generate season-long StatsAPI baselines

Current season only (defaults to current year if omitted):

```bash
cd /workspace/mlb-ai/Scrapers
bash run_scraper_statsapi.sh
```

Explicit year:

```bash
cd /workspace/mlb-ai/Scrapers
bash run_scraper_statsapi.sh 2026
```

Multi-year backfill (start/end inclusive):

```bash
cd /workspace/mlb-ai/Scrapers
bash run_scraper_statsapi_loop.sh 2020 2026
```

## 4) Generate daily game-level data (today's games)

```bash
cd /workspace/mlb-ai/Scrapers
python ballparkpal_headless.py
python ballparkpal_park_factors.py
python ballparkpal_pitching_alt_lines.py
python bovada_scrape_game_urls_playwright.py
python bovada_scrape_pitcher_props_playwright.py
python statsapi_bvp_matchup_stats.py
```

Outputs are written under `Scrapers/data/YYYY-MM-DD/`.

## 5) Sync daily data into Streamlit app data folder

```bash
cd /workspace/mlb-ai
cp -r Scrapers/data/20* Streamlit/data/
```

## 6) Run dashboard locally

```bash
cd /workspace/mlb-ai/Streamlit
streamlit run Home.py
```

## 7) Validate in UI before publishing

1. Open **Home** page and confirm the latest date appears in the sidebar date picker.
2. Verify at least one game card loads (teams, game time, projected runs, win %).
3. Open **Matchups** page and verify BvP table loads for a selected game.
4. Open **Odds Monitoring** page and confirm sportsbook files are detected.

## 8) Common seasonal rollover checks

- **Season naming:** MLB uses a single-year season label (`2026`), not `2026-2027`.
- **Year-specific files:** make sure `Scrapers/data/2026/*_2026_*.csv` exists after StatsAPI runs.
- **No stale date lock:** daily files must appear under today’s date (`Scrapers/data/YYYY-MM-DD`).
- **Site layout drift:** if BallparkPal/Bovada scripts fail, inspect selectors and update scraping logic in the corresponding script.

## 9) Quick smoke checks

```bash
cd /workspace/mlb-ai
python -m py_compile Scrapers/statsapi_team_game_logs.py \
  Scrapers/statsapi_pitcher_game_logs.py \
  Scrapers/statsapi_batter_game_logs.py \
  Scrapers/statsapi_player_season_stats.py
```

