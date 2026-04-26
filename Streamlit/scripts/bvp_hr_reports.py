#!/usr/bin/env python3
"""
bvp_hr_reports.py
-----------------
Generates two BvP HR reports for today's games:

  Report 1 — Top 20 by raw career HR total vs the opposing pitcher
  Report 2 — Top 20 by career HR rate (HR ÷ AB, all seasons) with 5+ AB filter

Run from anywhere:
    python3 bvp_hr_reports.py              # uses today's date
    python3 bvp_hr_reports.py 2026-04-26   # use a specific date

Outputs saved to:
    Streamlit/reports/report_top20_career_hr_<date>.png
    Streamlit/reports/report_top20_hr_rate_<date>.png
"""

import os, re, sys, glob
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter

# ── Team brand colors (primary) ──────────────────────────────────────────────
TEAM_COLORS = {
    'ATL':'#CE1141', 'BOS':'#BD3039', 'NYY':'#132448', 'NYM':'#002D72',
    'LAD':'#005A9C', 'PHI':'#E81828', 'HOU':'#002D62', 'CHC':'#0E3386',
    'STL':'#C41E3A', 'SFG':'#FD5A1E', 'SF':'#FD5A1E', 'SD':'#2F241D',
    'MIL':'#12284B', 'MIN':'#002B5C', 'TB': '#092C5C', 'DET':'#0C2C56',
    'CIN':'#C6011F', 'CLE':'#00385D', 'TOR':'#134A8E', 'COL':'#33006F',
    'WAS':'#AB0003', 'CHW':'#444444', 'PIT':'#FDB827', 'SEA':'#0C2C56',
    'TEX':'#003278', 'OAK':'#003831', 'ATH':'#003831', 'BAL':'#DF4601',
    'KC': '#004687', 'LAA':'#BA0021', 'MIA':'#00A3E0', 'ARI':'#A71930',
    'WSH':'#AB0003',
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_name(name):
    """Strip abbreviated-name artifacts like 'Ronald Acuna Jr. R. Acuna Jr.'"""
    return re.split(r'\s+[A-Z]\.\s+', str(name))[0].strip()


def find_data_dir(date_str):
    """Locate the Streamlit/data/<date> folder relative to this script or CWD."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', 'data', date_str),
        os.path.join(os.path.dirname(__file__), 'data', date_str),
        os.path.join('data', date_str),
        os.path.join('Streamlit', 'data', date_str),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    raise FileNotFoundError(
        f"Could not find data directory for {date_str}. Tried:\n" +
        "\n".join(f"  {os.path.abspath(c)}" for c in candidates)
    )


def find_reports_dir():
    """Locate (or create) the Streamlit/reports/ output directory."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', 'reports'),
        os.path.join('Streamlit', 'reports'),
        os.path.join('reports'),
    ]
    # Use the first candidate that is already inside a Streamlit folder,
    # or just the first one relative to this script.
    target = os.path.abspath(candidates[0])
    os.makedirs(target, exist_ok=True)
    return target


def load_bvp_data(data_dir):
    """Load all bvp_*.csv files from data_dir into a single DataFrame."""
    files = sorted(glob.glob(os.path.join(data_dir, 'bvp_*.csv')))
    if not files:
        raise FileNotFoundError(f"No bvp_*.csv files found in {data_dir}")

    frames = []
    for fpath in files:
        df = pd.read_csv(fpath)
        # Derive pitcher name from filename: bvp_<team>_vs_<pitcher>.csv
        basename = os.path.basename(fpath)           # e.g. bvp_bos_vs_bradish.csv
        parts = basename.replace('.csv','').split('_vs_')
        team_slug = parts[0].replace('bvp_','')
        pitcher_slug = parts[1] if len(parts) > 1 else 'unknown'
        df['file_team_slug'] = team_slug
        df['file_pitcher_slug'] = pitcher_slug
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined['batter'] = combined['batter'].apply(clean_name)
    for col in ['homeruns', 'atbats', 'hits', 'avg', 'year']:
        combined[col] = pd.to_numeric(combined[col], errors='coerce').fillna(0)
    return combined


def load_team_map(data_dir):
    """Return {batter_id_str: team_abbr} and {batter_name: team_abbr} dicts."""
    matchups_path = os.path.join(data_dir, 'matchups.csv')
    if not os.path.exists(matchups_path):
        return {}, {}
    df = pd.read_csv(matchups_path)
    df['batter_clean'] = df['Batter'].apply(clean_name)
    by_id   = dict(zip(df['BatterID'].astype(str), df['Team']))
    by_name = dict(zip(df['batter_clean'], df['Team']))
    return by_id, by_name


def get_team(row, by_id, by_name):
    bid = str(int(row['batter_id'])) if pd.notna(row.get('batter_id')) else ''
    return by_id.get(bid) or by_name.get(row['batter'], '???')


# ── Aggregate BvP stats ───────────────────────────────────────────────────────
def aggregate(combined, by_id, by_name):
    """
    Group by (batter, pitcher) across ALL seasons.
    Returns list of dicts with career totals and hr_rate.
    """
    results = []
    for (batter, pitcher), group in combined.groupby(['batter', 'pitcher']):
        total_hr = int(group['homeruns'].sum())
        total_ab = int(group['atbats'].sum())
        if total_ab == 0 or total_hr == 0:
            continue
        total_hits  = group['hits'].sum()
        career_avg  = round(total_hits / total_ab, 3)
        hr_rate     = round(total_hr / total_ab, 4)
        num_seasons = group['year'].nunique()
        hr_seasons  = sorted(group[group['homeruns'] > 0]['year'].astype(int).tolist())
        # team — use the first non-null batter_id row
        sample_row = group.iloc[0]
        team = get_team(sample_row, by_id, by_name)
        results.append({
            'batter':      batter,
            'pitcher':     pitcher,
            'team':        team,
            'career_hr':   total_hr,
            'career_ab':   total_ab,
            'career_avg':  career_avg,
            'hr_rate':     hr_rate,
            'num_seasons': num_seasons,
            'hr_seasons':  hr_seasons,
        })
    return results


# ── Chart helpers ─────────────────────────────────────────────────────────────
DARK_BG   = '#0A0A0A'
BAR_BG    = '#111111'
GRID_CLR  = '#2a2a2a'
LABEL_CLR = '#CCCCCC'
AXIS_CLR  = '#AAAAAA'


def bar_color(team):
    return TEAM_COLORS.get(team, '#666666')


# ── Report 1: Top 20 raw career HR ───────────────────────────────────────────
def report_career_hr(results, date_str, out_path):
    top = sorted(results, key=lambda x: (-x['career_hr'], -x['career_avg'], -x['career_ab']))[:20]
    n = len(top)

    fig, ax = plt.subplots(figsize=(16, 10), facecolor=DARK_BG)
    ax.set_facecolor(BAR_BG)

    colors = [bar_color(r['team']) for r in top]
    bars   = ax.barh(range(n), [r['career_hr'] for r in top],
                     color=colors, height=0.70, zorder=3,
                     edgecolor='#1a1a1a', linewidth=0.5)

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"#{i+1}  {top[i]['batter']}" for i in range(n)],
                       fontsize=10.5, color='white', fontweight='bold')
    ax.set_xlabel("Career Home Runs vs. Pitcher  (all seasons combined)", color=AXIS_CLR, fontsize=10)
    ax.set_title(f"Top 20 BvP Home Run Matchups — All Games · {date_str}",
                 color='white', fontsize=14, fontweight='bold', pad=14)
    ax.tick_params(colors=AXIS_CLR)
    ax.spines[:].set_color(GRID_CLR)
    ax.invert_yaxis()
    ax.set_xlim(0, max(r['career_hr'] for r in top) * 1.65)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis='x', color=GRID_CLR, linestyle='--', alpha=0.5, zorder=0)

    for i, (bar, r) in enumerate(zip(bars, top)):
        bw = bar.get_width()
        by = bar.get_y() + bar.get_height() / 2

        # Team badge inside bar
        ax.text(0.18, by, r['team'],
                va='center', ha='left', fontsize=8.5, color='white', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.22', facecolor='#00000060', edgecolor='none'),
                zorder=5)

        # Stats outside bar
        ax.text(bw + 0.12, by,
                f"vs {r['pitcher']}  ·  {r['career_hr']}/{r['career_ab']} AB  ·  "
                f"{r['career_avg']:.3f} avg  ·  {r['num_seasons']} season(s)  ·  "
                f"HR in: {r['hr_seasons']}",
                va='center', ha='left', fontsize=7.8, color=LABEL_CLR)

    # Legend — unique teams present
    seen = {}
    for r in top:
        if r['team'] not in seen:
            seen[r['team']] = bar_color(r['team'])
    patches = [mpatches.Patch(color=c, label=t) for t, c in seen.items()]
    ax.legend(handles=patches, loc='lower right', fontsize=8, facecolor='#1a1a1a',
              edgecolor='#444', labelcolor='white', title='Team', title_fontsize=8,
              framealpha=0.9, ncol=2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=155, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
    print(f"  Saved: {out_path}")


# ── Report 2: Top 20 HR rate (5+ AB) ─────────────────────────────────────────
def report_hr_rate(results, date_str, out_path, min_ab=5):
    eligible = [r for r in results if r['career_ab'] >= min_ab]
    top = sorted(eligible, key=lambda x: (-x['hr_rate'], -x['career_hr'], -x['career_ab']))[:20]
    n = len(top)
    if n == 0:
        print(f"  No matchups with {min_ab}+ AB found — skipping HR rate report.")
        return

    fig, ax = plt.subplots(figsize=(16, max(8, n * 0.52 + 1.5)), facecolor=DARK_BG)
    ax.set_facecolor(BAR_BG)

    colors = [bar_color(r['team']) for r in top]
    bars   = ax.barh(range(n), [r['hr_rate'] for r in top],
                     color=colors, height=0.70, zorder=3,
                     edgecolor='#1a1a1a', linewidth=0.5)

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"#{i+1}  {top[i]['batter']}" for i in range(n)],
                       fontsize=10.5, color='white', fontweight='bold')
    ax.set_xlabel(f"Career HR Rate  (Total HR ÷ Total AB vs Pitcher, all seasons · min {min_ab} AB)",
                  color=AXIS_CLR, fontsize=10)
    ax.set_title(f"Top 20 BvP HR Rate Matchups · {min_ab}+ Career AB · All Games · {date_str}",
                 color='white', fontsize=14, fontweight='bold', pad=14)
    ax.tick_params(colors=AXIS_CLR)
    ax.spines[:].set_color(GRID_CLR)
    ax.invert_yaxis()
    ax.set_xlim(0, max(r['hr_rate'] for r in top) * 1.9)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax.grid(axis='x', color=GRID_CLR, linestyle='--', alpha=0.5, zorder=0)

    for i, (bar, r) in enumerate(zip(bars, top)):
        bw = bar.get_width()
        by = bar.get_y() + bar.get_height() / 2

        # Team badge inside bar
        ax.text(0.004, by, r['team'],
                va='center', ha='left', fontsize=8.5, color='white', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.22', facecolor='#00000060', edgecolor='none'),
                zorder=5)

        # Stats outside bar
        ax.text(bw + 0.003, by,
                f"vs {r['pitcher']}  ·  {r['career_hr']}/{r['career_ab']} AB  ·  "
                f"{r['career_avg']:.3f} avg  ·  {r['num_seasons']} season(s)  ·  "
                f"HR yrs: {r['hr_seasons']}",
                va='center', ha='left', fontsize=7.8, color=LABEL_CLR)

    # Legend — unique teams
    seen = {}
    for r in top:
        if r['team'] not in seen:
            seen[r['team']] = bar_color(r['team'])
    patches = [mpatches.Patch(color=c, label=t) for t, c in seen.items()]
    ax.legend(handles=patches, loc='lower right', fontsize=8, facecolor='#1a1a1a',
              edgecolor='#444', labelcolor='white', title='Team', title_fontsize=8,
              framealpha=0.9, ncol=2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=155, bbox_inches='tight', facecolor=DARK_BG)
    plt.close()
    print(f"  Saved: {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    print(f"\n=== BvP HR Reports · {date_str} ===\n")

    data_dir = find_data_dir(date_str)
    print(f"Data directory: {data_dir}")

    combined   = load_bvp_data(data_dir)
    by_id, by_name = load_team_map(data_dir)

    bvp_files = sorted(glob.glob(os.path.join(data_dir, 'bvp_*.csv')))
    print(f"Loaded {len(bvp_files)} BvP file(s), {len(combined)} total rows\n")

    results = aggregate(combined, by_id, by_name)
    print(f"Aggregated {len(results)} unique batter-pitcher matchups with 1+ HR\n")

    reports_dir = find_reports_dir()
    print(f"Output directory: {reports_dir}\n")
    out1 = os.path.join(reports_dir, f"report_top20_career_hr_{date_str}.png")
    out2 = os.path.join(reports_dir, f"report_top20_hr_rate_{date_str}.png")

    print("Generating Report 1: Top 20 Career HR...")
    report_career_hr(results, date_str, out1)

    print("Generating Report 2: Top 20 HR Rate (5+ AB)...")
    report_hr_rate(results, date_str, out2, min_ab=5)

    print("\nDone.")


if __name__ == '__main__':
    main()
