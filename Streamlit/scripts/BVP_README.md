# Batter-vs-Pitcher (BvP) Edge System

Professional-grade daily BvP analysis for MLB hitter props.
Pulls career head-to-head splits from the official MLB Stats API, shrinks
them via empirical-Bayes against a two-year weighted hitter prior, and
ranks today's slate for hits / HR / OBP / K-avoidance edges.

---

## Components

```
scripts/
  scrape_bvp_today.py      # daily scraper -> data/<date>/bvp/*.csv
  rank_bvp_edges.py        # edge engine -> bvp_edges.csv + bvp_edges.html

pages/
  10_⚔️_BvP_Edges.py       # Streamlit UI (sortable / filterable / live re-rank)

data/<YYYY-MM-DD>/bvp/
  games_index.csv          # one row per game (teams, probable starters, hands)
  bvp_career.csv           # one row per batter-pitcher pair (career stat line)
  batter_season.csv        # one row per batter (current + prior season totals)
  bvp_edges.csv            # ranked output, one row per qualified matchup
  bvp_edges.html           # self-contained interactive HTML report
  _run_meta.json           # run provenance + counts
```

---

## Usage

### 1. Scrape today's slate

```bash
python scripts/scrape_bvp_today.py                # today
python scripts/scrape_bvp_today.py 2026-04-26     # specific date
python scripts/scrape_bvp_today.py --workers 16   # bump parallelism
```

Chunked mode (one game at a time, useful for tight time budgets):

```bash
for i in $(seq 0 15); do
  python scripts/scrape_bvp_today.py --game-index $i --append
done
```

### 2. Rank edges

```bash
python scripts/rank_bvp_edges.py                       # today
python scripts/rank_bvp_edges.py 2026-04-26            # specific date
python scripts/rank_bvp_edges.py --min-pa 20           # tighter sample cut
python scripts/rank_bvp_edges.py --prior-k 100         # heavier shrinkage
```

Outputs `bvp_edges.csv` (one row per qualified matchup) and a
self-contained `bvp_edges.html` report.

### 3. Streamlit UI

```bash
streamlit run Home.py
# nav -> "⚔️ BvP Edges" page
```

Sliders for `min_pa` and `prior_k` re-rank live without re-scraping.

---

## Methodology

### Data source

Official MLB Stats API via `python-mlb-statsapi`. We use the raw `person`
endpoint with the `vsPlayerTotal` hydrate to pull the canonical career
batter-vs-pitcher split:

```python
statsapi.get('person', {
    'personId': batter_id,
    'hydrate': f'stats(group=[hitting],type=[vsPlayerTotal],opposingPlayerId={pitcher_id})'
})
```

This returns the canonical career split with PA, AB, H, 2B, 3B, HR, BB,
HBP, SO, OBP, SLG, BABIP, etc. Active-roster batters (not just lineups)
come from `boxscore_data(game_id)` — works for scheduled games where
lineups haven't been posted.

### Two-year weighted prior

Many hitters have <50 PA in April, which makes the current-season rate
unreliable. We blend current + prior season weighted 1.5:1.0 by PA:

```
rate_prior = (1.5*x_cur + 1.0*x_prev) / (1.5*PA_cur + 1.0*PA_prev)
```

Falls back to league average if both seasons are 0 PA. (.231 H/PA,
.029 HR/PA, .318 OBP, .225 K/PA.)

### Empirical-Bayes shrinkage (Beta-Binomial)

For each rate (H/PA, HR/PA, OBP, K/PA) we shrink the BvP sample toward
the season prior:

```
α = rate_prior * k
β = (1 - rate_prior) * k
p_post = (α + x) / (α + β + n)
```

where `(x, n)` are observed BvP successes and trials, and `k` (default
60 PA) is the equivalent prior sample size. With 60 BvP PA the BvP sample
carries equal weight to the prior; with 10 BvP PA the prior carries ~6×
the weight. This is standard in baseball Bayesian rate estimation
(see Tango/Lichtman/Dolphin, *The Book*, ch. 1).

### Edge definition

```
edge = p_post − p_prior
```

A +5% hit edge means the model expects this batter to hit 5 percentage
points above his usual rate in this matchup. We also report game-level
"1+ hit" / "1+ HR" probabilities via:

```
P(≥1 in N PA) = 1 − (1 − p)^N      # default N=4
```

### Composite EDGE_SCORE

Z-scored components blended over today's qualified pool:

```
EDGE_SCORE = 0.40·z(hit_edge) + 0.30·z(hr_edge) + 0.20·z(obp_edge) + 0.10·z(k_avoid_edge)
```

Plus prop-specific sub-scores (`score_hits`, `score_hr`, `score_obp`,
`score_no_k`) for prop-targeted lists.

### Sample-size filter

Default `min_pa = 10`. Below this BvP samples are too noisy even after
shrinkage to surface as standalone plays. The UI exposes the slider so
strict (20+ PA) and looser (5+ PA) cuts are one click away.

---

## Caveats

- **BvP is partly noise.** Even 60-PA BvP samples have wide CIs. Treat
  the edge as one input among many — pair with park factors, weather,
  bullpen, lineup, recent form, market line.
- **Roster ≠ lineup.** We pull the active roster (26 men) since lineups
  aren't always posted. Edges for bench bats won't materialize if they
  don't start. Re-run after lineups drop for the cleanest picture.
- **Pitcher arsenal evolution.** Career BvP weights pitches/locations
  that may no longer reflect the pitcher's current arsenal. A separate
  Statcast pitch-mix model is the right complement.
- **Survivorship.** A hitter with 60 PA against the same pitcher has
  almost by definition been in the league a long time and started a lot
  of games against him — there's mild selection bias toward batters who
  hit lefties (or righties) well. The two-year prior partially controls
  for it but doesn't eliminate it.
- **Don't use this as your only model for HR props.** HR rates are very
  low and the variance is high. Pair with ISO + park-factor + weather.

---

## Files written per run

| Path | Rows | Purpose |
|---|---|---|
| `games_index.csv` | 1 per game | game_id, teams, venue, probable starters + hand |
| `bvp_career.csv` | ~50 per game | career H2H stats per batter-pitcher pair |
| `batter_season.csv` | 1 per unique batter | current + prior-year season hitting line |
| `bvp_edges.csv` | qualified matchups | ranked edges + scores |
| `bvp_edges.html` | — | self-contained dark-mode interactive report |
| `_run_meta.json` | — | scraped_at, counts, params |

---

## Validation

`shrink(22, 60, 0.227, 60)` returns `0.29683` exactly matching the
hand-calc `(0.227·60 + 22)/(60+60) = 35.62/120 = 0.29683`. Riley's
top-of-board placement at 60 PA / 22 H / 6 HR / .386 BA / .789 SLG
against Aaron Nola is consistent with public BvP databases.
