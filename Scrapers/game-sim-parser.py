import os
import glob
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from io import StringIO

today = datetime.now().strftime('%Y-%m-%d')
RAW_DIR = f"data/raw/{today}/game-sims"
OUTPUT_BASE = f"data/{today}"
os.makedirs(OUTPUT_BASE, exist_ok=True)

def find_p(soup, substring):
    return soup.find('p', string=lambda s: s and substring in s)

for html_path in glob.glob(os.path.join(RAW_DIR, '*.html')):
    game_id = os.path.splitext(os.path.basename(html_path))[0]
    output_dir = os.path.join(OUTPUT_BASE, game_id)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    for p in soup.find_all('p', string=lambda s: s and ' win by:' in s):
        team_key = p.get_text().split(' win by:')[0].strip().lower().replace(' ', '_')
        tbl = p.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, f"wins_by_{team_key}.csv"), index=False)

    box_tables = soup.find_all('table', class_='boxScoreTable')
    for idx, tbl in enumerate(box_tables[:4], start=1):
        df = pd.read_html(StringIO(str(tbl)))[0]
        if idx <= 2:
            name = f"proj_box_pitchers_{idx}.csv"
        else:
            name = f"proj_box_batters_{idx-2}.csv"
        df.to_csv(os.path.join(output_dir, name), index=False)

    p_total = find_p(soup, 'Total Runs Scored')
    if p_total:
        tbl = p_total.find_next('table', class_='totalRunsTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, 'total_runs_scored.csv'), index=False)

    for p in soup.find_all('p', string=lambda s: s and s.endswith(' Runs')):
        team_key = p.get_text().split(' Runs')[0].strip().lower().replace(' ', '_')
        tbl = p.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, f"{team_key}_runs.csv"), index=False)

    p_rbi = find_p(soup, 'Runs By Inning')
    if p_rbi:
        tbl = p_rbi.find_next('table', class_='runsByInningTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, 'runs_by_inning.csv'), index=False)

    p_f5 = find_p(soup, 'First 5 Innings')
    if p_f5:
        tbl = p_f5.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, 'first_5_innings.csv'), index=False)

    p_stats = find_p(soup, 'Projected Team Stats')
    if p_stats:
        tbl = p_stats.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(StringIO(str(tbl)))[0]
            df.to_csv(os.path.join(output_dir, 'projected_team_stats.csv'), index=False)

    print(f"Processed game {game_id}, output in {output_dir}")
print("All games extracted under:", OUTPUT_BASE)
