#!/usr/bin/env python3
import os
import glob
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# Build today's date string
today = datetime.now().strftime('%Y-%m-%d')
RAW_DIR = f"data/raw/{today}/game-sims"
OUTPUT_BASE = f"data/{today}"

# Ensure base output directory exists
os.makedirs(OUTPUT_BASE, exist_ok=True)

# Helper to find a <p> tag by substring
def find_p(soup, substring):
    return soup.find('p', string=lambda s: s and substring in s)

# Process each HTML game file
for html_path in glob.glob(os.path.join(RAW_DIR, '*.html')):
    game_id = os.path.splitext(os.path.basename(html_path))[0]
    output_dir = os.path.join(OUTPUT_BASE, game_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Load and parse HTML
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # 1) "X win by" tables for any team
    for p in soup.find_all('p', string=lambda s: s and ' win by:' in s):
        team_key = p.get_text().split(' win by:')[0].strip().lower().replace(' ', '_')
        tbl = p.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, f"wins_by_{team_key}.csv"), index=False)

    # 2) Projected Box Score — first two tables are pitchers, next two batters
    box_tables = soup.find_all('table', class_='boxScoreTable')
    for idx, tbl in enumerate(box_tables[:4], start=1):
        df = pd.read_html(str(tbl))[0]
        if idx <= 2:
            name = f"proj_box_pitchers_{idx}.csv"
        else:
            name = f"proj_box_batters_{idx-2}.csv"
        df.to_csv(os.path.join(output_dir, name), index=False)

    # 3) Total Runs Scored
    p_total = find_p(soup, 'Total Runs Scored')
    if p_total:
        tbl = p_total.find_next('table', class_='totalRunsTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, 'total_runs_scored.csv'), index=False)

    # 4) "Team Runs" tables dynamically
    for p in soup.find_all('p', string=lambda s: s and s.endswith(' Runs')):
        team_key = p.get_text().split(' Runs')[0].strip().lower().replace(' ', '_')
        tbl = p.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, f"{team_key}_runs.csv"), index=False)

    # 5) Runs By Inning
    p_rbi = find_p(soup, 'Runs By Inning')
    if p_rbi:
        tbl = p_rbi.find_next('table', class_='runsByInningTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, 'runs_by_inning.csv'), index=False)

    # 6) First 5 Innings
    p_f5 = find_p(soup, 'First 5 Innings')
    if p_f5:
        tbl = p_f5.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, 'first_5_innings.csv'), index=False)

    # 7) Projected Team Stats
    p_stats = find_p(soup, 'Projected Team Stats')
    if p_stats:
        tbl = p_stats.find_next('table', class_='runMarginTable')
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(os.path.join(output_dir, 'projected_team_stats.csv'), index=False)

    print(f"Processed game {game_id}, output in {output_dir}")

print("All games extracted under:", OUTPUT_BASE)


# import os
# import pandas as pd
# from bs4 import BeautifulSoup
# from datetime import datetime

# today = datetime.now().strftime('%Y-%m-%d')

# # --- CONFIGURATION ---
# INPUT_HTML = f"data/raw/{today}/game-sims/778260.html"
# OUTPUT_DIR = f"data/778260_extracted"

# # Make sure output directory exists
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # Load and parse the HTML
# with open(INPUT_HTML, encoding="utf-8") as f:
#     soup = BeautifulSoup(f, "html.parser")

# # Helper to find a <p> by substring
# def find_p(substring):
#     return soup.find("p", string=lambda s: s and substring in s)

# # 1. "X win by" tables for each team
# for team in ["Giants", "Angels"]:
#     p = find_p(f"{team} win by:")
#     if p:
#         table = p.find_next("table", class_="runMarginTable")
#         if table:
#             df = pd.read_html(str(table))[0]
#             out = os.path.join(OUTPUT_DIR, f"wins_by_{team.lower()}.csv")
#             df.to_csv(out, index=False)
#             print(f"Saved {out}")

# # 2. Projected Box Score (two tables: first = Giants, second = Angels)
# p_proj = find_p("Projected Box Score")
# if p_proj:
#     tables = p_proj.find_all_next("table", class_="boxScoreTable", limit=2)
#     for idx, table in enumerate(tables, start=1):
#         team = "giants" if idx == 1 else "angels"
#         df = pd.read_html(str(table))[0]
#         out = os.path.join(OUTPUT_DIR, f"projected_box_score_{team}.csv")
#         df.to_csv(out, index=False)
#         print(f"Saved {out}")

# # 3. Total Runs Scored (single combined table)
# p_total = find_p("Total Runs Scored")
# if p_total:
#     table = p_total.find_next("table", class_="totalRunsTable")
#     if table:
#         df = pd.read_html(str(table))[0]
#         out = os.path.join(OUTPUT_DIR, "total_runs_scored.csv")
#         df.to_csv(out, index=False)
#         print(f"Saved {out}")

# # 4. Team‐specific Runs tables ("Giants Runs" and "Angels Runs")
# for team in ["Giants", "Angels"]:
#     p_team = find_p(f"{team} Runs")
#     if p_team:
#         table = p_team.find_next("table", class_="runMarginTable")
#         if table:
#             df = pd.read_html(str(table))[0]
#             out = os.path.join(OUTPUT_DIR, f"{team.lower()}_runs.csv")
#             df.to_csv(out, index=False)
#             print(f"Saved {out}")

# # 5. Runs By Inning
# p_rbi = find_p("Runs By Inning")
# if p_rbi:
#     table = p_rbi.find_next("table", class_="runsByInningTable")
#     if table:
#         df = pd.read_html(str(table))[0]
#         out = os.path.join(OUTPUT_DIR, "runs_by_inning.csv")
#         df.to_csv(out, index=False)
#         print(f"Saved {out}")

# # 6. First 5 Innings
# p_f5 = find_p("First 5 Innings")
# if p_f5:
#     table = p_f5.find_next("table", class_="runMarginTable")
#     if table:
#         df = pd.read_html(str(table))[0]
#         out = os.path.join(OUTPUT_DIR, "first_5_innings.csv")
#         df.to_csv(out, index=False)
#         print(f"Saved {out}")

# print("All sections extracted to", OUTPUT_DIR)
