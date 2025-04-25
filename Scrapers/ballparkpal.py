from playwright.async_api import async_playwright
import asyncio
from bs4 import BeautifulSoup
import csv
import os
import pandas as pd
from datetime import datetime
import glob
from io import StringIO
from urllib.parse import urljoin, urlparse, parse_qs

# Create data directories
today = datetime.now().strftime('%Y-%m-%d')
os.makedirs(f"data/{today}/", exist_ok=True)
os.makedirs(f"data/raw/{today}/", exist_ok=True)


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
        with open(f'data/raw/{today}/game_simulations.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved page HTML to data/raw/{today}/game_simulations.html")
asyncio.run(main())


### Parse Game Simulations Page Main Table ###
INPUT_HTML = f"data/raw/{today}/game_simulations.html"
OUTPUT_CSV = f"data/{today}/game_simulations.csv"
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
INPUT_HTML   = f"data/raw/{today}/game_simulations.html"
OUTPUT_CSV   = f"data/{today}/game_simulations_per_game_tables.csv"
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


### Scrape Individual Game Simulation Pages ###
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_user_data", headless=False
        )
        page = await ctx.new_page()
        os.makedirs(f"data/raw/{today}", exist_ok=True)
        with open(f"data/{today}/game_simulations.csv") as f:
            for row in csv.DictReader(f):
                gid = row["game_id"]
                url = f"https://www.ballparkpal.com/Game.php?GamePk={gid}"
                await page.goto(url)
                await page.wait_for_timeout(1000)
                html = await page.content()
                with open(f"data/raw/{today}/{gid}.html", "w", encoding="utf-8") as out:
                    out.write(html)
                print("saved", gid)
        await ctx.close()
asyncio.run(main())


### Parse Individual Game Simulation Pages ###
today = datetime.now().strftime('%Y-%m-%d')
RAW_DIR = f"data/raw/{today}"
OUTPUT_BASE = f"data/{today}"
os.makedirs(OUTPUT_BASE, exist_ok=True)
def find_p(soup, substring):
    return soup.find('p', string=lambda s: s and substring in s)
game_files = glob.glob(os.path.join(RAW_DIR, '[0-9]*.html'))
print(f"Found {len(game_files)} game files to process")
for html_path in game_files:
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
        headers = [th.get_text(strip=True) for th in tbl.find_all('th')]
        headers.append('Player URL')
        headers.append('Player ID')
        table_data = []
        tbody = tbl.find('tbody')
        if not tbody:
            print(f"Warning: No tbody found in table {idx} for game {game_id}. Skipping table.")
            continue
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if not cells:
                continue
            row_data = [cell.get_text(strip=True) for cell in cells]
            player_url = None
            player_id = None
            player_link = row.find('a', href=lambda href: href and 'PlayerId=' in href)
            if player_link:
                href = player_link['href']
                base_url = "https://www.ballparkpal.com/"
                player_url = urljoin(base_url, href)
                
                if 'PlayerId=' in href:
                    player_id = href.split('PlayerId=')[1]
                
            row_data.append(player_url)
            row_data.append(player_id)
            
            if len(row_data) == len(headers):
                 table_data.append(dict(zip(headers, row_data)))
            else:
                print(f"Warning: Skipping row in table {idx} for game {game_id} due to header/data mismatch.")
                print(f"Headers ({len(headers)}): {headers}")
                print(f"Row Data ({len(row_data)}): {row_data}")
        if table_data:
            df = pd.DataFrame(table_data)
            if idx <= 2:
                name = f"proj_box_pitchers_{idx}.csv"
            else:
                name = f"proj_box_batters_{idx-2}.csv"
            df.to_csv(os.path.join(output_dir, name), index=False)
        else:
             print(f"Info: No data extracted from table {idx} for game {game_id}.")
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


### Scrape BvP Matchups Page ###
import nest_asyncio
nest_asyncio.apply()
async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_user_data",
            headless=False
        )
        page = await context.new_page()
        await page.goto('https://www.ballparkpal.com/Matchups.php')
        await page.wait_for_timeout(1000)
        content = await page.content()
        with open(f'data/{today}/matchups.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved page HTML to data/{today}/matchups.html")
asyncio.run(main())


### Parse BvP Matchups Page ###
import os
import csv
from bs4 import BeautifulSoup
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
data_dir = f"data/{today}"
if not os.path.exists(f"{data_dir}/matchups.html"):
    print(f"Error: {data_dir}/matchups.html not found")
    exit(1)
with open(f"{data_dir}/matchups.html", "r", encoding="utf-8") as f:
    html_content = f.read()
soup = BeautifulSoup(html_content, "html.parser")
rows = soup.find_all("tr", class_=["odd", "even"])
os.makedirs(data_dir, exist_ok=True)
with open(f"{data_dir}/matchups.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Team", "Batter", "BatterID", "AtBats", "Pitcher", "PitcherID", 
        "RC", "HR", "XB", "1B", "BB", "K"
    ])
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 10:
            continue  
        team = cells[0].get_text(strip=True)
        batter_link = cells[1].find("a")
        batter = batter_link.get_text(strip=True) if batter_link else ""
        batter_id = ""
        if batter_link and "PlayerId=" in batter_link["href"]:
            batter_id = batter_link["href"].split("PlayerId=")[1]
        at_bats_link = cells[2].find("a")
        at_bats = at_bats_link.get_text(strip=True) if at_bats_link else ""
        pitcher_link = cells[3].find("a")
        pitcher = pitcher_link.get_text(strip=True) if pitcher_link else ""
        pitcher_id = ""
        if pitcher_link and "PlayerId=" in pitcher_link["href"]:
            pitcher_id = pitcher_link["href"].split("PlayerId=")[1]
        values = [cells[i].get_text(strip=True) for i in range(4, 10)]
        writer.writerow([
            team, batter, batter_id, at_bats, pitcher, pitcher_id,
            *values
        ])
print(f"Parsed matchups table to {data_dir}/matchups.csv") 
os.remove(f"{data_dir}/matchups.html")