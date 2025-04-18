#!/usr/bin/env python3
import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# Build today's path
today = datetime.now().strftime('%Y-%m-%d')
INPUT_HTML = f"data/raw/{today}/game-sims/778260.html"
OUTPUT_DIR = "data/778260_extracted"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load and parse HTML
with open(INPUT_HTML, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Helper to find a <p> tag by substring
def find_p(substring):
    return soup.find("p", string=lambda s: s and substring in s)

# 1) "X win by" tables for each team
for team in ["Giants", "Angels"]:
    p = find_p(f"{team} win by:")
    if p:
        tbl = p.find_next("table", class_="runMarginTable")
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(f"{OUTPUT_DIR}/wins_by_{team.lower()}.csv", index=False)
            print(f"Saved wins_by_{team.lower()}.csv")

# 2) Projected Box Score — 4 tables (2 pitchers + 2 batters)
all_bs = soup.find_all("table", class_="boxScoreTable")
for idx, tbl in enumerate(all_bs[:4], start=1):
    df = pd.read_html(str(tbl))[0]
    if idx <= 2:
        team = "giants" if idx == 1 else "angels"
        name = f"proj_box_pitchers_{team}"
    else:
        team = "giants" if idx == 3 else "angels"
        name = f"proj_box_batters_{team}"
    df.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False)
    print(f"Saved {name}.csv")

# 3) Total Runs Scored (single table)
p_total = find_p("Total Runs Scored")
if p_total:
    tbl = p_total.find_next("table", class_="totalRunsTable")
    if tbl:
        df = pd.read_html(str(tbl))[0]
        df.to_csv(f"{OUTPUT_DIR}/total_runs_scored.csv", index=False)
        print("Saved total_runs_scored.csv")

# 4) Team-specific Runs tables
for team in ["Giants", "Angels"]:
    p = find_p(f"{team} Runs")
    if p:
        tbl = p.find_next("table", class_="runMarginTable")
        if tbl:
            df = pd.read_html(str(tbl))[0]
            df.to_csv(f"{OUTPUT_DIR}/{team.lower()}_runs.csv", index=False)
            print(f"Saved {team.lower()}_runs.csv")

# 5) Runs By Inning
p_rbi = find_p("Runs By Inning")
if p_rbi:
    tbl = p_rbi.find_next("table", class_="runsByInningTable")
    if tbl:
        df = pd.read_html(str(tbl))[0]
        df.to_csv(f"{OUTPUT_DIR}/runs_by_inning.csv", index=False)
        print("Saved runs_by_inning.csv")

# 6) First 5 Innings
p_f5 = find_p("First 5 Innings")
if p_f5:
    tbl = p_f5.find_next("table", class_="runMarginTable")
    if tbl:
        df = pd.read_html(str(tbl))[0]
        df.to_csv(f"{OUTPUT_DIR}/first_5_innings.csv", index=False)
        print("Saved first_5_innings.csv")

# 7) Projected Team Stats
p_team = find_p("Projected Team Stats")
if p_team:
    tbl = p_team.find_next("table", class_="runMarginTable")
    if tbl:
        df = pd.read_html(str(tbl))[0]
        df.to_csv(f"{OUTPUT_DIR}/projected_team_stats.csv", index=False)
        print("Saved projected_team_stats.csv")

print("All sections extracted to", OUTPUT_DIR)
