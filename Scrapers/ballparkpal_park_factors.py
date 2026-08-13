#!/usr/bin/env python3
"""
Scrape Ballpark Pal Park-Factors page and extract weather and roof icon filenames per game.
Uses requests (https://docs.python-requests.org/) and BeautifulSoup (https://www.crummy.com/software/BeautifulSoup/bs4/doc/).
"""

import pandas as pd
from playwright.async_api import async_playwright
import asyncio
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
from ballparkpal_auth import ballparkpal_browser_context, assert_authenticated_html

URL = "https://www.ballparkpal.com/Park-Factors.php"
HEADLESS = os.getenv("BALLPARKPAL_HEADLESS", "0") == "1"

async def download_html(url, filepath):
    async with async_playwright() as p:
        async with ballparkpal_browser_context(p, headless=HEADLESS) as ctx:
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector("table#parkFactorsTable", state="attached", timeout=20000)
            except Exception as e:
                print(f"Warning: park factors table selector wait timed out: {e}")
                await page.wait_for_timeout(3000)
            content = await page.content()
            assert_authenticated_html(page.url, content, "Park Factors")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

today = datetime.now().strftime('%Y-%m-%d')
output_dir = os.path.join("data", today)
os.makedirs(output_dir, exist_ok=True)
html_filepath = os.path.join(output_dir, "park_factors.html")

async def main():
    await download_html(URL, html_filepath)
    print(f"Downloaded HTML to {html_filepath}")
asyncio.run(main())

# --- PARSE AND EXTRACT ICONS ---
with open(html_filepath, encoding="utf-8") as f:
    html = f.read()
soup = BeautifulSoup(html, "lxml")

header = soup.find("h1", class_="sectionHeader")
if header:
    raw = header.get_text(strip=True)
    m = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", raw)
    if m:
        date_str = datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    else:
        date_str = today
else:
    date_str = today
output_dir = os.path.join("data", date_str)
os.makedirs(output_dir, exist_ok=True)

legend = {
    "LightWind.png": "Light Breeze",
    "ModerateWind.png": "Moderate Wind",
    "HeavyWind.png": "Heavy Wind",
    "Under60.png": "<60°F",
    "From60to75.png": "60–75°F",
    "From76to82.png": "76–82°F",
    "From83to89.png": "83–89°F",
    "Over90.png": "≥90°F",
    "RoofClosed.png": "Roof Closed",
    "LowP.png": "Low Pressure",
    "HighP.png": "High Pressure",
    "LowH.png": "Low Humidity",
    "HighH.png": "High Humidity"
}

table = soup.find("table", id="parkFactorsTable")
if table is None:
    print("Error: parkFactorsTable not found. The page may require login or a different header.")
    exit(1)
rows = table.find("tbody").find_all("tr")


def load_game_ids_by_matchup(date):
    """Map Ballpark Pal's abbreviated matchup labels to GamePk values."""
    game_simulations_path = os.path.join(
        "data", "raw", date, "game_simulations.html"
    )
    if not os.path.exists(game_simulations_path):
        return {}

    with open(game_simulations_path, encoding="utf-8") as f:
        simulations_soup = BeautifulSoup(f, "lxml")

    game_ids_by_matchup = {}
    for game in simulations_soup.select("a.game-summary-item"):
        game_id_match = re.search(r"(?:#game_|GamePk=)(\d+)", game.get("href", ""))
        team_codes = [
            re.sub(r"-logo\.(?:svg|png)$", "", os.path.basename(img.get("src", "")), flags=re.I)
            for img in game.find_all("img")
        ]
        if game_id_match and len(team_codes) == 2 and all(team_codes):
            matchup = f"{team_codes[0].upper()} @ {team_codes[1].upper()}"
            game_ids_by_matchup[matchup] = int(game_id_match.group(1))
    return game_ids_by_matchup


game_ids_by_matchup = load_game_ids_by_matchup(date_str)
rows_data = []
for tr in rows:
    game_cell = tr.find("td", {"data-column": "Game"})
    if game_cell is None:
        print("Warning: skipping park factors row with no Game cell")
        continue

    link = game_cell.find("a", class_="gameLink")
    href = link.get("href", "") if link else ""
    game_id_match = re.search(r"GamePk=(\d+)", href)
    matchup = game_cell.select_one(".matchupText")
    matchup_text = matchup.get_text(" ", strip=True).upper() if matchup else ""
    game_id = (
        int(game_id_match.group(1))
        if game_id_match
        else game_ids_by_matchup.get(matchup_text)
    )
    if game_id is None:
        print(f"Warning: skipping park factors row with no GamePk: {matchup_text or game_cell.get_text(' ', strip=True)}")
        continue

    game_text = game_cell.get_text(strip=True)
    icons = [img["src"].split("/")[-1] for img in game_cell.find_all("img") if img["src"].endswith((".png", ".svg"))]
    labels = [legend.get(name, name) for name in icons]
    rows_data.append({
        "game_id": game_id,
        "game": game_text,
        "icons": ",".join(icons),
        "icon_labels": ",".join(labels)
    })

df = pd.DataFrame(rows_data)
csv_path = os.path.join(output_dir, "park_factors_icons.csv")
df.to_csv(csv_path, index=False)
print(f"Saved park factors icons CSV to {csv_path}") 
