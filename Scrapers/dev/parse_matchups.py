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