# Save all game urls
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

url = "https://www.mlb.com/scores"
response = requests.get(url)
html_content = response.text
soup = BeautifulSoup(html_content, "html.parser")
links = set(
    a['href'] 
    for a in soup.find_all('a', href=True) 
    if '/gameday/' in a['href']
)
data = []
for url in sorted(links):
    match = re.search(r'/gameday/(\d+)', url)
    game_id = match.group(1) if match else None
    if not url.endswith('/preview'):
        url += '/preview'
    data.append({'game_id': game_id, 'url': url})
df = pd.DataFrame(data)
df.to_csv("data/mlb/upcoming_games.csv", index=False)
print(df)


# Save game matchups
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
chrome_options = Options()
chrome_options.add_argument('--headless')
# driver = webdriver.Chrome(options=chrome_options)
os.makedirs("data/mlb/game_previews", exist_ok=True)
for game in data:
    url = game['url']
    game_id = game['game_id']
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    html_content = driver.page_source
    driver.quit()
    with open(f"data/mlb/game_previews/{game_id}.html", "w", encoding='utf-8') as f:
        f.write(html_content)
    print(game)
    
    

# Parse game matchups lineups
from bs4 import BeautifulSoup
import pandas as pd
file_path = "data/mlb/game_previews/778189.html"
with open(file_path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, "html.parser")
rows = soup.find_all('tr', attrs={'data-selected': True})
table_groups = {}
for tr in rows:
    td0 = tr.find('td')
    if not td0 or 'id' not in td0.attrs:
        continue
    prefix = td0['id'].split('-body')[0]
    if prefix not in table_groups:
        table_groups[prefix] = []
    cells = tr.find_all('td')
    row_data = []
    for cell in cells:
        if cell == cells[0]:
            link = cell.find('a', class_='LineupMatchupstyle__PlayerLink-sc-5h968q-11')
            name = link.get_text(strip=True) if link else ""
            pos = cell.find('span', class_='LineupMatchupstyle__PositionWrapper-sc-5h968q-9')
            position = pos.get_text(strip=True) if pos else ""
            row_data.extend([name, position])
        else:
            row_data.append(cell.get_text(strip=True))
    table_groups[prefix].append(row_data)
for i, (prefix, data) in enumerate(table_groups.items(), start=1):
    num_cols = len(data[0])
    cols = ["player", "position"] + [f"col_{j}" for j in range(1, num_cols-1)]
    df = pd.DataFrame(data, columns=cols)
    csv_path = f"data/mlb/game_previews/{prefix}_matchup.csv"
    df.to_csv(csv_path, index=False)
    print(f"[Download CSV for {prefix}](sandbox:{csv_path})")