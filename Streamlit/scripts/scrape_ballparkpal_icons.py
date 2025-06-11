#!/usr/bin/env python3
"""
Scrape Ballpark Pal Park-Factors page and extract weather and roof icon filenames per game.
Uses requests (https://docs.python-requests.org/) and BeautifulSoup (https://www.crummy.com/software/BeautifulSoup/bs4/doc/).
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import pandas as pd
from datetime import datetime

URL = "https://www.ballparkpal.com/Park-Factors.php"
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
resp = requests.get(URL, headers=headers)
resp.raise_for_status()

local_file = "Today's MLB Park Factors _ Ballpark Pal.html"
if os.path.isfile(local_file):
    with open(local_file, encoding="utf-8") as f:
        html = f.read()
    print(f"Parsing from local HTML file: {local_file}")
else:
    html = resp.text
soup = BeautifulSoup(html, "lxml")

# extract date from page header and prepare output dir
header = soup.find("h1", class_="sectionHeader")
if header:
    raw = header.get_text(strip=True)
    m = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", raw)
    if m:
        date_str = datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    else:
        date_str = datetime.today().strftime("%Y-%m-%d")
else:
    date_str = datetime.today().strftime("%Y-%m-%d")
output_dir = os.path.join("data", date_str)
os.makedirs(output_dir, exist_ok=True)

table = soup.find("table", id="parkFactorsTable")
if table is None:
    print("Error: parkFactorsTable not found. The page may require login or a different header.")
    exit(1)
rows = table.find("tbody").find_all("tr")

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

rows_data = []
for tr in rows:
    game_cell = tr.find("td", {"data-column": "Game"})
    # extract game ID from link
    link = game_cell.find("a", class_="gameLink")
    href = link["href"]
    game_id = re.search(r"GamePk=(\d+)", href).group(1)
    # full game text
    game_text = game_cell.get_text(strip=True)
    # icon filenames and their labels
    icons = [img["src"].split("/")[-1] for img in game_cell.find_all("img") if img["src"].endswith((".png", ".svg"))]
    labels = [legend.get(name, name) for name in icons]
    rows_data.append({
        "game_id": int(game_id),
        "game": game_text,
        "icons": ",".join(icons),
        "icon_labels": ",".join(labels)
    })
# save to CSV
df = pd.DataFrame(rows_data)
csv_path = os.path.join(output_dir, "park_factors_icons.csv")
df.to_csv(csv_path, index=False)
print(f"Saved park factors icons CSV to {csv_path}") 