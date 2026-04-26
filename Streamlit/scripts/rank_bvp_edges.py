"""
rank_bvp_edges.py
=================

Reads the daily BvP CSVs produced by scrape_bvp_today.py and computes per-
matchup *edge* scores designed for handicappers betting batter props.

For each batter-pitcher pair we estimate four rate edges:

    HIT_EDGE   = E[H/PA | BvP, prior]      vs season hit rate            (1+ hits)
    HR_EDGE    = E[HR/PA | BvP, prior]     vs season HR rate             (HR props)
    OBP_EDGE   = E[(H+BB+HBP)/PA | BvP]    vs season OBP                 (hit+walk)
    K_AVOID    = 1 - E[K/PA | BvP, prior]  vs (1 - season K rate)        (no-K props)

All four use *Beta-Binomial empirical-Bayes shrinkage*: the BvP rate is
shrunk toward the batter's season rate with shrinkage weight inversely
proportional to BvP plate appearances. Posterior:

    p_post = (alpha + x) / (alpha + beta + n)
    where (alpha, beta) parameterize the prior on the batter's season rate
    and (x, n) are observed BvP successes / trials.

The "prior strength" k = alpha+beta defaults to 60 PA, which means a 60-PA
career BvP sample is weighted equally with the season prior -- a reasonable
choice for hitter rates (h/PA, HR/PA) given typical season volume.

A composite EDGE_SCORE z-scores each component over today's slate and
weights them per the user's profile (default tuned for hits/HR plays).

Outputs:
    data/<YYYY-MM-DD>/bvp/bvp_edges.csv     # ranked, all qualified rows
    data/<YYYY-MM-DD>/bvp/bvp_edges.html    # self-contained interactive report

Usage:
    python scripts/rank_bvp_edges.py
    python scripts/rank_bvp_edges.py 2026-04-26 --min-pa 10
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def daily_dir(date_str: str) -> Path:
    return repo_root() / "data" / date_str / "bvp"


# ---------------------------------------------------------------------------
# League fallbacks (used when batter has no season prior at all)
# ---------------------------------------------------------------------------
LEAGUE_PRIORS = {
    "h_rate":   0.231,   # H/PA league avg
    "hr_rate":  0.029,   # HR/PA
    "obp":      0.318,
    "k_rate":   0.225,   # K/PA
}


# ---------------------------------------------------------------------------
# Empirical-Bayes shrinkage
# ---------------------------------------------------------------------------
def shrink(x: float, n: float, prior_rate: float, k: float = 60.0) -> float:
    """Beta-Binomial shrinkage of x successes in n trials toward prior_rate.

    k is the *equivalent prior sample size* (alpha + beta).
    """
    if pd.isna(prior_rate):
        prior_rate = 0.0
    if pd.isna(x):
        x = 0
    if pd.isna(n) or n is None:
        n = 0
    alpha = prior_rate * k
    beta = (1.0 - prior_rate) * k
    return float((alpha + x) / (alpha + beta + n))


# ---------------------------------------------------------------------------
# Compute edges
# ---------------------------------------------------------------------------
def compute_edges(
    bvp: pd.DataFrame,
    season: pd.DataFrame,
    games: pd.DataFrame,
    min_pa: int = 10,
    prior_k: float = 60.0,
) -> pd.DataFrame:
    """Return one row per batter-pitcher pair with edges + composite score."""

    # --- Normalize season-prior rates per batter ---
    # Use a TWO-YEAR weighted prior: current season + prior season, weighted
    # by PA. This stabilizes the prior for the early-season window when many
    # hitters have <50 PA on the year. League-average fallback if both are 0.
    s = season.copy()
    def _num(col):
        raw = s.get(col)
        if raw is None:
            return 0.0
        return pd.to_numeric(raw, errors="coerce").fillna(0)

    pa_cur, pa_prv = _num("plateAppearances"), _num("plateAppearances_prev")
    h_cur,  h_prv  = _num("hits"),             _num("hits_prev")
    hr_cur, hr_prv = _num("homeRuns"),         _num("homeRuns_prev")
    bb_cur, bb_prv = _num("baseOnBalls"),      _num("baseOnBalls_prev")
    k_cur,  k_prv  = _num("strikeOuts"),       _num("strikeOuts_prev")
    hbp_cur, hbp_prv = _num("hitByPitch"),     _num("hitByPitch_prev")
    tb_cur, tb_prv = _num("totalBases"),       _num("totalBases_prev")

    # Weighted: current season carries 1.5x weight per PA (more recent)
    w_cur, w_prv = 1.5, 1.0
    pa_eff = w_cur * pa_cur + w_prv * pa_prv
    h_eff  = w_cur * h_cur  + w_prv * h_prv
    hr_eff = w_cur * hr_cur + w_prv * hr_prv
    bb_eff = w_cur * bb_cur + w_prv * bb_prv
    k_eff  = w_cur * k_cur  + w_prv * k_prv
    hbp_eff = w_cur * hbp_cur + w_prv * hbp_prv
    tb_eff = w_cur * tb_cur  + w_prv * tb_prv

    s["season_pa"] = pa_eff
    s["season_h_rate"]  = np.where(pa_eff > 0, h_eff  / pa_eff, LEAGUE_PRIORS["h_rate"])
    s["season_hr_rate"] = np.where(pa_eff > 0, hr_eff / pa_eff, LEAGUE_PRIORS["hr_rate"])
    s["season_obp"]     = np.where(pa_eff > 0,
                                   (h_eff + bb_eff + hbp_eff) / pa_eff,
                                   LEAGUE_PRIORS["obp"])
    s["season_k_rate"]  = np.where(pa_eff > 0, k_eff  / pa_eff, LEAGUE_PRIORS["k_rate"])
    s["season_iso"]     = np.where(pa_eff > 0, (tb_eff - h_eff) / pa_eff, 0.150)

    keep_cols = ["batter_id", "season_pa", "season_h_rate", "season_hr_rate",
                 "season_obp", "season_k_rate", "season_iso"]
    for opt in ("batSide", "primaryPosition", "team_name"):
        if opt in s.columns:
            keep_cols.append(opt)
    s_keep = s[keep_cols]

    # --- Merge ---
    df = bvp.merge(s_keep, on="batter_id", how="left")
    df = df.merge(
        games[["game_id", "game_datetime", "venue_name", "away_name", "home_name",
               "away_pitcher_id", "away_pitcher_hand",
               "home_pitcher_id", "home_pitcher_hand"]],
        on="game_id", how="left"
    )

    # Pitcher hand = the hand of the pitcher this batter is FACING (not their own team's)
    df["opp_pitcher_hand"] = np.where(
        df["side"] == "away", df["home_pitcher_hand"], df["away_pitcher_hand"]
    )

    # --- Numeric coerce ---
    for c in ["plateAppearances", "atBats", "hits", "homeRuns", "baseOnBalls",
              "strikeOuts", "hitByPitch", "totalBases", "doubles", "triples"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce").fillna(0)

    df["bvp_h_rate_raw"]  = np.where(df["plateAppearances"] > 0,
                                     df["hits"] / df["plateAppearances"], np.nan)
    df["bvp_hr_rate_raw"] = np.where(df["plateAppearances"] > 0,
                                     df["homeRuns"] / df["plateAppearances"], np.nan)
    df["bvp_obp_raw"]     = np.where(df["plateAppearances"] > 0,
                                     (df["hits"] + df["baseOnBalls"] + df["hitByPitch"])
                                     / df["plateAppearances"], np.nan)
    df["bvp_k_rate_raw"]  = np.where(df["plateAppearances"] > 0,
                                     df["strikeOuts"] / df["plateAppearances"], np.nan)
    df["bvp_iso_raw"]     = np.where(df["plateAppearances"] > 0,
                                     (df["totalBases"] - df["hits"]) / df["plateAppearances"], np.nan)

    # --- Shrunk posteriors ---
    df["p_h"]  = df.apply(lambda r: shrink(r["hits"],     r["plateAppearances"],
                                           r["season_h_rate"],  prior_k), axis=1)
    df["p_hr"] = df.apply(lambda r: shrink(r["homeRuns"], r["plateAppearances"],
                                           r["season_hr_rate"], prior_k), axis=1)
    df["p_obp"] = df.apply(lambda r: shrink(r["hits"] + r["baseOnBalls"] + r["hitByPitch"],
                                            r["plateAppearances"],
                                            r["season_obp"], prior_k), axis=1)
    df["p_k"]  = df.apply(lambda r: shrink(r["strikeOuts"], r["plateAppearances"],
                                           r["season_k_rate"], prior_k), axis=1)

    # --- Edges (posterior - prior) ---
    df["hit_edge"]    = df["p_h"]   - df["season_h_rate"]
    df["hr_edge"]     = df["p_hr"]  - df["season_hr_rate"]
    df["obp_edge"]    = df["p_obp"] - df["season_obp"]
    df["k_avoid_edge"] = df["season_k_rate"] - df["p_k"]   # positive = batter strikes out LESS than usual vs this pitcher

    # --- Posterior std-dev (Beta-Binomial) for confidence sizing ---
    def _beta_std(p, n_eff):
        return float(np.sqrt(p * (1 - p) / max(n_eff, 1)))

    df["n_eff"] = df["plateAppearances"] + prior_k
    df["p_h_std"]  = df.apply(lambda r: _beta_std(r["p_h"],  r["n_eff"]), axis=1)
    df["p_hr_std"] = df.apply(lambda r: _beta_std(r["p_hr"], r["n_eff"]), axis=1)

    # 1+ hit prob in N PA. Default N = 4 (typical games started PA volume).
    pa_per_game = 4.0
    df["p_1plus_hit"] = 1.0 - (1.0 - df["p_h"]) ** pa_per_game
    df["p_1plus_hr"]  = 1.0 - (1.0 - df["p_hr"]) ** pa_per_game

    # baseline (using season rate alone)
    df["p_1plus_hit_base"] = 1.0 - (1.0 - df["season_h_rate"]) ** pa_per_game
    df["p_1plus_hr_base"]  = 1.0 - (1.0 - df["season_hr_rate"]) ** pa_per_game

    df["edge_1plus_hit"] = df["p_1plus_hit"] - df["p_1plus_hit_base"]
    df["edge_1plus_hr"]  = df["p_1plus_hr"]  - df["p_1plus_hr_base"]

    # --- Filter to qualified BvP samples ---
    qualified = df[df["plateAppearances"] >= min_pa].copy()

    # --- Composite EDGE_SCORE (z-scored over today's qualified slate) ---
    def _z(series):
        m, sd = series.mean(), series.std(ddof=0)
        if not sd or np.isnan(sd):
            return pd.Series(0.0, index=series.index)
        return (series - m) / sd

    if not qualified.empty:
        z_hit = _z(qualified["hit_edge"])
        z_hr  = _z(qualified["hr_edge"])
        z_obp = _z(qualified["obp_edge"])
        z_k   = _z(qualified["k_avoid_edge"])
        # User-selected: hits + HR + OBP + K-avoidance, weight hits & HR most
        qualified["edge_score"] = (
            0.40 * z_hit + 0.30 * z_hr + 0.20 * z_obp + 0.10 * z_k
        )
        # Sub-scores for prop-specific lists
        qualified["score_hits"] = 0.7 * z_hit + 0.3 * z_obp
        qualified["score_hr"]   = z_hr
        qualified["score_obp"]  = 0.6 * z_obp + 0.4 * z_hit
        qualified["score_no_k"] = z_k
    else:
        for c in ["edge_score", "score_hits", "score_hr", "score_obp", "score_no_k"]:
            qualified[c] = np.nan

    qualified = qualified.sort_values("edge_score", ascending=False)
    return qualified, df


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------
HTML_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BvP Edge Report — {date}</title>
<style>
  :root {{
    --bg: #0f1216; --panel: #161b22; --border: #2a313a;
    --text: #e6edf3; --muted: #8b949e; --good: #3fb950; --bad: #f85149;
    --accent: #58a6ff; --warn: #d29922;
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px; }}
  h1 {{ margin: 0 0 4px 0; font-size: 22px; }}
  h2 {{ margin: 28px 0 8px 0; font-size: 16px; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 18px; }}
  .controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 14px 0 18px; }}
  .controls input, .controls select {{ background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 6px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; background: var(--panel); border-radius: 6px; overflow: hidden; }}
  th {{ text-align: left; background: #1c2129; color: var(--muted); font-weight: 600; padding: 8px 10px; cursor: pointer; user-select: none; position: sticky; top: 0; }}
  th:hover {{ color: var(--text); }}
  td {{ padding: 7px 10px; border-top: 1px solid var(--border); }}
  tr:hover td {{ background: #1b2027; }}
  .pos {{ color: var(--good); }} .neg {{ color: var(--bad); }}
  .pa-badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px; background: #1c2530; color: var(--accent); font-size: 11px; font-weight: 600; }}
  .meta {{ color: var(--muted); font-size: 12px; }}
  .legend {{ background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin-top: 24px; font-size: 12.5px; line-height: 1.55; color: var(--muted); }}
  .legend code {{ color: var(--text); background: #1c2530; padding: 1px 5px; border-radius: 3px; }}
</style>
</head>
<body>

<h1>BvP Edge Report — {date}</h1>
<div class="sub">{n_qualified} qualified matchups (≥{min_pa} PA) across {n_games} games · prior k={prior_k} PA · generated {generated_at}</div>

<h2>🔝 Top Composite Edges (hits + HR + OBP + K-avoidance)</h2>
{table_top}

<h2>⚾ Top Hit Plays (1+/2+ hit props)</h2>
{table_hits}

<h2>💣 Top HR Plays</h2>
{table_hr}

<h2>🎯 Top OBP / Walk-or-Hit Plays</h2>
{table_obp}

<h2>🛡️ Top K-Avoidance Plays (under-Ks / contact)</h2>
{table_no_k}

<div class="legend">
  <strong>Methodology.</strong> For every batter on each team's active roster vs the opposing probable starter, we pull career head-to-head splits from the official MLB Stats API (<code>vsPlayerTotal</code> hydrate). Rates are shrunk toward each batter's <code>{prior_season}</code> season rates using a Beta-Binomial empirical-Bayes posterior with prior strength <code>k=60 PA</code>:
  <code>p_post = (α + x) / (α + β + n)</code> where <code>α = season_rate · k</code>, <code>β = (1−season_rate) · k</code>, and <code>(x, n)</code> are observed BvP successes/trials. Edges are <code>p_post − season_rate</code>; <code>edge_1+ hit</code> uses <code>1 − (1−p_h)<sup>4</sup></code> for a typical 4-PA game. <code>EDGE_SCORE</code> is a z-weighted blend (40% hits / 30% HR / 20% OBP / 10% K-avoid) over today's qualified pool. Min-PA filter excludes BvP samples below {min_pa} PA. Sources: MLB Stats API · scripts/scrape_bvp_today.py · scripts/rank_bvp_edges.py.
</div>

<script>
  // simple click-to-sort
  document.querySelectorAll('table').forEach(table => {{
    table.querySelectorAll('th').forEach((th, idx) => {{
      th.addEventListener('click', () => {{
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.rows);
        const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
        th.dataset.dir = dir;
        rows.sort((a, b) => {{
          const av = a.cells[idx].dataset.v ?? a.cells[idx].textContent;
          const bv = b.cells[idx].dataset.v ?? b.cells[idx].textContent;
          const an = parseFloat(av); const bn = parseFloat(bv);
          if (!isNaN(an) && !isNaN(bn)) return dir === 'asc' ? an - bn : bn - an;
          return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
        }});
        rows.forEach(r => tbody.appendChild(r));
      }});
    }});
  }});
</script>
</body>
</html>"""


def _fmt_pct(x):
    if pd.isna(x): return ""
    return f"{x*100:+.1f}%"


def _fmt_rate(x):
    if pd.isna(x): return ""
    return f"{x:.3f}".lstrip("0") if abs(x) < 1 else f"{x:.3f}"


def _td(val, cls=""):
    if pd.isna(val): return f'<td class="{cls}"></td>'
    if isinstance(val, (int, np.integer)):
        return f'<td class="{cls}" data-v="{val}">{val}</td>'
    if isinstance(val, float):
        return f'<td class="{cls}" data-v="{val:.6f}">{val}</td>'
    return f'<td class="{cls}">{val}</td>'


def _render_table(df, columns, n=20):
    head = "<thead><tr>" + "".join(f"<th>{label}</th>" for _, label in columns) + "</tr></thead>"
    body_rows = []
    for _, r in df.head(n).iterrows():
        cells = []
        for col, _ in columns:
            v = r.get(col)
            if col in ("hit_edge", "hr_edge", "obp_edge", "k_avoid_edge",
                       "edge_1plus_hit", "edge_1plus_hr"):
                if pd.isna(v):
                    cells.append('<td></td>')
                else:
                    cls = "pos" if v > 0 else ("neg" if v < 0 else "")
                    cells.append(f'<td class="{cls}" data-v="{v:.6f}">{_fmt_pct(v)}</td>')
            elif col in ("p_h", "p_hr", "p_obp", "p_k", "season_h_rate",
                         "season_hr_rate", "season_obp", "season_k_rate",
                         "p_1plus_hit", "p_1plus_hr",
                         "bvp_h_rate_raw", "bvp_hr_rate_raw"):
                if pd.isna(v):
                    cells.append('<td></td>')
                else:
                    cells.append(f'<td data-v="{v:.6f}">{_fmt_rate(v)}</td>')
            elif col in ("plateAppearances", "atBats", "hits", "homeRuns",
                         "baseOnBalls", "strikeOuts"):
                iv = int(v) if pd.notna(v) else 0
                if col == "plateAppearances":
                    cells.append(f'<td data-v="{iv}"><span class="pa-badge">{iv}</span></td>')
                else:
                    cells.append(f'<td data-v="{iv}">{iv}</td>')
            elif col in ("edge_score", "score_hits", "score_hr", "score_obp", "score_no_k"):
                if pd.isna(v):
                    cells.append('<td></td>')
                else:
                    cls = "pos" if v > 0 else ("neg" if v < 0 else "")
                    cells.append(f'<td class="{cls}" data-v="{v:.4f}"><strong>{v:+.2f}</strong></td>')
            else:
                cells.append(_td(v))
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table>{head}<tbody>{''.join(body_rows)}</tbody></table>"


def render_html(qualified: pd.DataFrame, date_str: str, min_pa: int,
                prior_k: float, n_games: int, prior_season) -> str:
    common = [
        ("batter_name", "Batter"),
        ("pitcher_name", "vs Pitcher"),
        ("opp_pitcher_hand", "Hand"),
        ("plateAppearances", "PA"),
        ("hits", "H"),
        ("homeRuns", "HR"),
        ("baseOnBalls", "BB"),
        ("strikeOuts", "K"),
        ("bvp_h_rate_raw", "BvP H/PA"),
        ("season_h_rate", "Season H/PA"),
        ("p_h", "p̂(H)"),
        ("hit_edge", "Hit Δ"),
        ("hr_edge", "HR Δ"),
        ("obp_edge", "OBP Δ"),
        ("k_avoid_edge", "K-Avoid Δ"),
        ("edge_score", "EDGE"),
        ("away_name", "Away"),
        ("home_name", "Home"),
    ]
    hits_cols = [
        ("batter_name", "Batter"),
        ("pitcher_name", "vs Pitcher"),
        ("plateAppearances", "PA"),
        ("hits", "H"),
        ("bvp_h_rate_raw", "BvP H/PA"),
        ("season_h_rate", "Season H/PA"),
        ("p_h", "p̂(H/PA)"),
        ("p_1plus_hit", "P(1+H)"),
        ("edge_1plus_hit", "1+H Δ"),
        ("score_hits", "HitScore"),
        ("away_name", "Away"),
        ("home_name", "Home"),
    ]
    hr_cols = [
        ("batter_name", "Batter"),
        ("pitcher_name", "vs Pitcher"),
        ("plateAppearances", "PA"),
        ("homeRuns", "HR"),
        ("bvp_hr_rate_raw", "BvP HR/PA"),
        ("season_hr_rate", "Season HR/PA"),
        ("p_hr", "p̂(HR/PA)"),
        ("p_1plus_hr", "P(1+HR)"),
        ("edge_1plus_hr", "HR Δ"),
        ("score_hr", "HR Score"),
        ("away_name", "Away"),
        ("home_name", "Home"),
    ]
    obp_cols = [
        ("batter_name", "Batter"),
        ("pitcher_name", "vs Pitcher"),
        ("plateAppearances", "PA"),
        ("hits", "H"),
        ("baseOnBalls", "BB"),
        ("p_obp", "p̂(OBP)"),
        ("season_obp", "Season OBP"),
        ("obp_edge", "OBP Δ"),
        ("score_obp", "OBP Score"),
        ("away_name", "Away"),
        ("home_name", "Home"),
    ]
    no_k_cols = [
        ("batter_name", "Batter"),
        ("pitcher_name", "vs Pitcher"),
        ("plateAppearances", "PA"),
        ("strikeOuts", "K"),
        ("p_k", "p̂(K/PA)"),
        ("season_k_rate", "Season K/PA"),
        ("k_avoid_edge", "K-Avoid Δ"),
        ("score_no_k", "K-Avoid Score"),
        ("away_name", "Away"),
        ("home_name", "Home"),
    ]

    return HTML_TMPL.format(
        date=date_str,
        n_qualified=len(qualified),
        n_games=n_games,
        min_pa=min_pa,
        prior_k=int(prior_k),
        prior_season=prior_season,
        generated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        table_top=_render_table(qualified.sort_values("edge_score", ascending=False), common, 25),
        table_hits=_render_table(qualified.sort_values("score_hits", ascending=False), hits_cols, 15),
        table_hr=_render_table(qualified.sort_values("score_hr", ascending=False), hr_cols, 15),
        table_obp=_render_table(qualified.sort_values("score_obp", ascending=False), obp_cols, 15),
        table_no_k=_render_table(qualified.sort_values("score_no_k", ascending=False), no_k_cols, 15),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("--min-pa", type=int, default=10)
    ap.add_argument("--prior-k", type=float, default=60.0)
    args = ap.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    d = daily_dir(date_str)

    bvp = pd.read_csv(d / "bvp_career.csv")
    season = pd.read_csv(d / "batter_season.csv")
    games = pd.read_csv(d / "games_index.csv")

    qualified, full = compute_edges(bvp, season, games,
                                    min_pa=args.min_pa, prior_k=args.prior_k)

    out_csv = d / "bvp_edges.csv"
    qualified.to_csv(out_csv, index=False)
    print(f"[rank_bvp_edges] {len(qualified)} qualified matchups -> {out_csv}")

    out_html = d / "bvp_edges.html"
    if "season" in season.columns and not season.empty and season["season"].notna().any():
        try:
            prior_season = f"{int(season['season'].dropna().mode().iloc[0])}+{int(season['season'].dropna().mode().iloc[0])-1}"
        except Exception:
            prior_season = date_str[:4]
    else:
        prior_season = date_str[:4]
    html = render_html(qualified, date_str, args.min_pa, args.prior_k,
                       n_games=len(games), prior_season=prior_season)
    with open(out_html, "w") as f:
        f.write(html)
    print(f"[rank_bvp_edges] report -> {out_html}")

    # Print top-10 to stdout for quick inspection
    cols = ["batter_name", "pitcher_name", "plateAppearances", "hits", "homeRuns",
            "season_h_rate", "p_h", "hit_edge", "hr_edge", "edge_score"]
    print("\nTop 10 composite edges:")
    print(qualified[cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
