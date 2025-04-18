

from playwright.async_api import async_playwright
import asyncio
from bs4 import BeautifulSoup
import csv
import os
import pandas as pd

### Scrape Game Simulations Home Page ###
async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_user_data",
            headless=False
        )
        page = await context.new_page()
        await page.goto('https://www.ballparkpal.com/Game-Simulations.php')
        await page.wait_for_timeout(1000)
        content = await page.content()
        with open('data/game_simulations.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved page HTML to data/game_simulations.html")
asyncio.run(main())

### Parse Game Simulations Page Main Table ###
INPUT_HTML = "data/game_simulations.html"
OUTPUT_CSV = "data/game_simulations.csv"
with open(INPUT_HTML, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")
container = soup.find("div", class_="game-summary-box")
items = container.find_all("a", class_="game-summary-item")
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=[
        "game_id", "away_team", "away_score", "time", "home_team", "home_score"
    ])
    writer.writeheader()
    for a in items:
        href = a.get("href", "")
        game_id = href.split("_")[-1] if "_" in href else href.lstrip("#")
        cols = a.find_all("div", class_="column")
        away_img = cols[0].find("img")
        away_team = away_img["alt"].strip()
        away_score = cols[0].find("div", class_="score").get_text(strip=True)
        time = cols[1].find("div", class_="time").get_text(strip=True)
        home_img = cols[2].find("img")
        home_team = home_img["alt"].strip()
        home_score = cols[2].find("div", class_="score").get_text(strip=True)
        writer.writerow({
            "game_id": game_id,
            "away_team": away_team,
            "away_score": away_score,
            "time": time,
            "home_team": home_team,
            "home_score": home_score
        })
print(f"Wrote {len(items)} rows to {OUTPUT_CSV!r}")


### Parse Game Simulations Per Game Tables ###
INPUT_HTML   = "data/game_simulations.html"
OUTPUT_CSV   = "data/game_simulations_per_game_tables.csv"
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
with open(INPUT_HTML, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")
containers = soup.select("div.summaryDescriptionContainer")
records = []
for container in containers:
    row = {}
    anchor = container.find_previous_sibling("a", id=True)
    row["game_id"] = anchor["id"].split("_")[-1]
    time_div = container.find("div", class_="atSymbol")
    row["time"] = time_div.get_text(strip=True) if time_div else ""
    away_divs = [d.get_text(strip=True) for d in container.select("div.awayTeam")]
    home_divs = [d.get_text(strip=True) for d in container.select("div.homeTeam")]
    if len(away_divs) > 1:
        row["away_team"] = away_divs[1]
    if len(home_divs) > 1:
        row["home_team"] = home_divs[1]
    pitchers = container.select("a[href*='Pitcher.php']")
    if len(pitchers) >= 2:
        row["starter_away"] = pitchers[0].get_text(strip=True)
        row["starter_home"] = pitchers[1].get_text(strip=True)
    for stat in ["Runs", "Win", "ML", "F5 Runs", "F5 Lead"]:
        stat_div = container.find("div", class_="middleText", string=stat)
        if stat_div:
            wrap = stat_div.parent
            siblings = [c for c in wrap.parent.find_all(recursive=False) if c.name == "div"]
            idx = siblings.index(wrap)
            row[f"{stat.lower().replace(' ', '_')}_away"] = siblings[idx-1].get_text(strip=True)
            row[f"{stat.lower().replace(' ', '_')}_home"] = siblings[idx+1].get_text(strip=True)
    table = container.find("table", class_="totalsTable")
    if table:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        values  = [td.get_text(strip=True) for td in table.find_all("tr")[1].find_all("td")]
        for h, v in zip(headers, values):
            col = h.replace(".", "_").replace(" ", "_")
            row[f"total_{col}"] = v
    total_div = container.find("div", class_="middleText", string="Total")
    if total_div:
        wrap = total_div.parent
        sibs = [c for c in wrap.parent.find_all(recursive=False) if c.name == "div"]
        idx  = sibs.index(wrap)
        row["under"] = sibs[idx-1].get_text(strip=True)
        row["over"]  = sibs[idx+1].get_text(strip=True)
    yrfi = container.find("div", class_="yrfi")
    if yrfi:
        row["YRFI"] = yrfi.get_text(strip=True)
    park_div = container.find("div", class_="middleText", string=lambda s: s and "Park" in s)
    if park_div:
        txt   = park_div.get_text(strip=True)
        parts = [p.strip() for p in txt.split("|")]
        row["park"]      = parts[0]
        row["park_runs"] = parts[1].replace("Runs:", "").strip() if len(parts) > 1 else ""
    lineup_div = container.find("div", class_="middleText", string=lambda s: s and "Lineups Final" in s)
    if lineup_div:
        row["lineups_final"] = lineup_div.get_text(strip=True).replace("Lineups Final:", "").strip()
    records.append(row)
df = pd.DataFrame(records)
df.to_csv(OUTPUT_CSV, index=False)
print(f"Wrote {len(df)} game records to {OUTPUT_CSV!r}")
