# Automated Agents

## gen_bvp_reports.sh

Runs the full BvP (Batter-vs-Pitcher) pipeline. Usage:

```bash
./gen_bvp_reports.sh            # today
./gen_bvp_reports.sh 2026-04-25 # specific date
```

### Step 1: BvP Edges for Dashboard

Runs `scrape_bvp_today.py` then `rank_bvp_edges.py`. Commits and pushes data to GitHub (prompts y/n when run manually, auto-pushes from cron).

**Output:** `data/<date>/bvp/`

| File | Description |
|---|---|
| `games_index.csv` | One row per game: teams, venue, probable starters |
| `bvp_career.csv` | Career head-to-head stats per batter-pitcher pair |
| `batter_season.csv` | Current + prior season hitting stats per batter |
| `bvp_edges.csv` | Ranked edges and composite scores for qualified matchups |
| `bvp_edges.html` | Self-contained interactive HTML report |
| `_run_meta.json` | Run timestamp, counts, parameters |

### Step 2: BvP Home Run Reports

Runs `bvp_hr_reports.py`. Opens the PNGs on macOS.

**Output:** `reports/`

| File | Description |
|---|---|
| `report_top20_career_hr_<date>.png` | Top 20 matchups ranked by raw career HR total |
| `report_top20_hr_rate_<date>.png` | Top 20 matchups ranked by career HR rate (5+ AB) |

### Cron

```crontab
0 7 * * * /home/trinity/mlb-ai/Scrapers/run_scraper.sh >> /home/trinity/mlb-ai/Scrapers/cron.log 2>&1
0 8 * * * /home/trinity/mlb-ai/Streamlit/gen_bvp_reports.sh >> /home/trinity/mlb-ai/Scrapers/cron.log 2>&1
```
