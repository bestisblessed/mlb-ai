import os
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
from pathlib import Path
import glob
import requests
import re
from datetime import datetime
import time
import random
from lxml import html as lxml_html
from io import StringIO

# Configuration
SAVANT_DIR = "data/mlb/savant"
DEPTH_CHART_DIR = "data/mlb/depth-charts"
RAW_PLAYER_DIR = "data/mlb/raw-players"
RAW_HITTER_LOG_DIR = "data/mlb/raw_player_game_logs_hitters"
RAW_PITCHER_LOG_DIR = "data/mlb/raw_player_game_logs_pitchers"
PARSED_HITTER_LOG_DIR = "data/mlb/player_game_logs_hitters"
PARSED_PITCHER_LOG_DIR = "data/mlb/player_game_logs_pitchers"
os.makedirs(SAVANT_DIR, exist_ok=True)
os.makedirs(DEPTH_CHART_DIR, exist_ok=True)
os.makedirs(RAW_PLAYER_DIR, exist_ok=True)
os.makedirs(RAW_HITTER_LOG_DIR, exist_ok=True)
os.makedirs(RAW_PITCHER_LOG_DIR, exist_ok=True)
os.makedirs(PARSED_HITTER_LOG_DIR, exist_ok=True)
os.makedirs(PARSED_PITCHER_LOG_DIR, exist_ok=True)

async def scrape_mlb_teams():
    """Scrape all MLB team depth chart URLs."""
    url = "https://www.mlb.com/team/roster/depth-chart"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    depth_chart_data = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/roster/depth-chart" in href:
            img = a.find("img")
            if img and "alt" in img.attrs:
                team_name = img["alt"].replace(" logo", "").strip()
                full_url = f"https://www.mlb.com{href}" if href.startswith("/") else href
                depth_chart_data.append((team_name, full_url))
    
    depth_chart_df = pd.DataFrame(depth_chart_data, columns=["Team Name", "Depth Chart URL"])
    depth_chart_df.to_csv("data/mlb/all_teams.csv", index=False)
    return depth_chart_df

def scrape_team_depth_charts():
    """Scrape depth charts for all teams and save individual CSVs."""
    teams_df = pd.read_csv('data/mlb/all_teams.csv')
    
    for index, row in teams_df.iterrows():
        team_name = row['Team Name']
        depth_chart_url = row['Depth Chart URL']
        
        try:
            response = requests.get(depth_chart_url)
            response.raise_for_status()  # Raise HTTP errors
            soup = BeautifulSoup(response.content, "html.parser")
            
            player_tds = soup.select("td.info")
            players_data = []
            
            for td in player_tds:
                name_tag = td.find("a")
                jersey_tag = td.find("span", class_="jersey")
                status_tag = td.find("span", class_="status-il")
                mobile_info = td.find("div", class_="mobile-info")
                
                name = name_tag.get_text(strip=True) if name_tag else ""
                player_url = "https://www.mlb.com" + name_tag["href"] if name_tag and name_tag.has_attr("href") else ""
                jersey = jersey_tag.get_text(strip=True) if jersey_tag else ""
                status = status_tag.get_text(strip=True) if status_tag else ""
                bt = mobile_info.find("span", class_="mobile-info__bat-throw").get_text(strip=True).replace("B/T: ", "") if mobile_info else ""
                height = mobile_info.find("span", class_="mobile-info__height").get_text(strip=True).replace("Ht: ", "") if mobile_info else ""
                weight = mobile_info.find("span", class_="mobile-info__weight").get_text(strip=True).replace("Wt: ", "") if mobile_info else ""
                dob = mobile_info.find("span", class_="mobile-info__birthday").get_text(strip=True).replace("DOB: ", "") if mobile_info else ""
                
                players_data.append({
                    "Name": name,
                    "Player URL": player_url,
                    "Jersey Number": jersey,
                    "Status": status,
                    "B/T": bt,
                    "Height": height,
                    "Weight": weight,
                    "DOB": dob
                })
            
            players_df = pd.DataFrame(players_data)
            csv_path = f"{DEPTH_CHART_DIR}/{team_name.replace(' ', '_').lower()}_depth_chart.csv"
            players_df.to_csv(csv_path, index=False)
            print(f"Saved data for {team_name} to {csv_path}")
            
            # Add delay between teams (2-5 seconds)
            time.sleep(1 + random.random() * 2)  # Random 3-5 second delay
            
        except Exception as e:
            print(f"Error scraping {team_name}: {e}")
            continue  # Skip to next team if error occurs

def create_all_players_csv():
    """Combine all team depth charts into one master CSV file."""
    all_players = []
    for team_file in glob.glob(f"{DEPTH_CHART_DIR}/*_depth_chart.csv"):
        df = pd.read_csv(team_file)
        team_name = team_file.split('/')[-1].replace('_depth_chart.csv','').replace('_',' ').title()
        df['Team'] = team_name
        df['Player ID'] = df['Player URL'].str.split('/').str[-1]  # Extracting player ID from URL
        all_players.append(df)
    
    all_players_df = pd.concat(all_players, ignore_index=True)
    all_players_df.to_csv("data/mlb/all_players.csv", index=False)
    print(f"Combined {len(all_players)} team rosters into all_players.csv")
    print(f"Total players: {len(all_players_df)}")
    return all_players_df

async def scrape_player_positions(players_df):
    """Scrape player positions from their individual pages."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for i, row in players_df.iterrows():
            if pd.notna(row.get("Position")) and str(row["Position"]).strip():
                continue
                
            player_url = row["Player URL"]
            try:
                await page.goto(player_url, wait_until="domcontentloaded")
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Extract position from the player header
                position_span = soup.select_one("span.position")
                if position_span:
                    position = position_span.get_text(strip=True)
                    players_df.at[i, "Position"] = position
                    print(f"Found position for {row['Name']}: {position}")
                
                # Save checkpoint every 20 players
                if (i + 1) % 20 == 0:
                    players_df.to_csv("data/mlb/all_players.csv", index=False)
                    print(f"Checkpoint saved at row {i+1}")
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"Error scraping {player_url}: {e}")
        
        await browser.close()
        players_df.to_csv("data/mlb/all_players.csv", index=False)
        return players_df

def filter_pitchers_hitters(players_df):
    """Create separate CSVs for pitchers and hitters with game log URLs."""
    # Filter pitchers
    pitchers_df = players_df[
        players_df["Position"].notna() & 
        (players_df["Position"].str.strip().str.upper() == "P")
    ].copy()
    
    pitchers_df["Game Log URL"] = pitchers_df["Player ID"].apply(
        lambda pid: f"https://www.mlb.com/player/{pid}?stats=gamelogs-r-pitching-mlb&year={datetime.now().year}"
    )
    pitchers_df.to_csv("data/mlb/pitchers_with_game_logs.csv", index=False)
    print(f"Saved {len(pitchers_df)} pitchers with game log URLs")
    
    # Filter non-pitchers
    hitters_df = players_df[
        players_df["Position"].notna() & 
        (players_df["Position"].str.strip().str.upper() != "P")
    ].copy()
    
    hitters_df["Game Log URL"] = hitters_df["Player ID"].apply(
        lambda pid: f"https://www.mlb.com/player/{pid}?stats=gamelogs-r-hitting-mlb&year={datetime.now().year}"
    )
    hitters_df.to_csv("data/mlb/hitters_with_game_logs.csv", index=False)
    print(f"Saved {len(hitters_df)} hitters with game log URLs")
    
    return pitchers_df, hitters_df

async def scrape_savant_player(browser, player_id, player_name, player_type="hitter"):
    """Scrape player data from MLB Savant."""
    page = await browser.new_page()
    
    # Build URL based on player type
    if player_type == "hitter":
        url = f"https://baseballsavant.mlb.com/savant-player/{player_id}?stats=statcast-r-hitting-mlb"
    else:
        url = f"https://baseballsavant.mlb.com/savant-player/{player_id}?stats=statcast-r-pitching-mlb&playerType=pitcher"
    
    try:
        print(f"Scraping {player_name} ({player_id}) as {player_type}...")
        await page.goto(url, wait_until="domcontentloaded")
        html = await page.content()
        
        # Save raw HTML
        safe_id = player_id.replace("/", "_")
        with open(f"{SAVANT_DIR}/{safe_id}_{player_type}.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        return True
    except Exception as e:
        print(f"Error scraping {player_id}: {e}")
        return False
    finally:
        await page.close()

async def process_players(players_df):
    """Process all players from the dataframe."""
    # Categorize players
    pitchers = players_df[players_df["Position"].str.strip().str.upper() == "P"]
    hitters = players_df[players_df["Position"].str.strip().str.upper() != "P"]
    
    print(f"Found {len(pitchers)} pitchers and {len(hitters)} hitters to process")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Process pitchers
        pitcher_tasks = []
        for _, row in pitchers.iterrows():
            pitcher_tasks.append(
                scrape_savant_player(
                    browser,
                    row["Player ID"],
                    row["Name"],
                    "pitcher"
                )
            )
        
        # Process hitters
        hitter_tasks = []
        for _, row in hitters.iterrows():
            hitter_tasks.append(
                scrape_savant_player(
                    browser,
                    row["Player ID"],
                    row["Name"],
                    "hitter"
                )
            )
        
        # Run all tasks
        await asyncio.gather(*pitcher_tasks, *hitter_tasks)
        await browser.close()

async def _scrape_game_logs(players_df, player_type="hitter", concurrency: int = 8):
    """Download HTML game-log pages for each player.

    Parameters
    ----------
    players_df : pd.DataFrame
        DataFrame that includes at least Player ID and Game Log URL columns.
    player_type : str, optional
        "hitter" or "pitcher" to decide where files are stored, by default "hitter".
    concurrency : int, optional
        Maximum number of concurrent pages, by default 8.
    """
    output_dir = RAW_HITTER_LOG_DIR if player_type == "hitter" else RAW_PITCHER_LOG_DIR
    os.makedirs(output_dir, exist_ok=True)

    print(f"Starting game-log download for {len(players_df)} {player_type}s → {output_dir}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(player_row):
            player_id = player_row["Player ID"]
            url = player_row["Game Log URL"]
            season_year = datetime.now().year
            file_path = f"{output_dir}/{player_id}_{season_year}.html"
            # Skip if already downloaded
            if os.path.exists(file_path):
                return
            async with sem:
                page = await browser.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    html_content = await page.content()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"Saved {player_type} log HTML: {player_id}")
                except Exception as e:
                    print(f"Error downloading game log for {player_id}: {e}")
                finally:
                    await page.close()

        tasks = [_fetch_one(row) for _, row in players_df.iterrows()]
        await asyncio.gather(*tasks)
        await browser.close()
    print(f"Finished downloading {player_type} game logs.")

def _parse_game_logs(raw_dir: str, parsed_dir: str, player_type: str = "hitter"):
    """Parse raw HTML files into per-player CSVs.

    For hitters we look for a table that contains a "Date" column.
    For pitchers we look for a table that contains typical pitching columns like "IP"/"ERA".
    """
    raw_path = Path(raw_dir)
    parsed_path = Path(parsed_dir)
    files = list(raw_path.glob("*.html"))
    if not files:
        print(f"No raw HTML files found in {raw_dir} – skipping parse.")
        return

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                html_text = f.read()
            tables = pd.read_html(StringIO(html_text))
        except Exception as e:
            print(f"Failed to read tables from {file.name}: {e}")
            continue

        selected = None
        for tbl in tables:
            cols = set(tbl.columns.astype(str))
            if player_type == "hitter" and ("Date" in cols or "G" in cols):
                selected = tbl.copy()
                break
            if player_type == "pitcher" and ("IP" in cols or "ERA" in cols):
                selected = tbl.copy()
                break
        if selected is None:
            print(f"No suitable table found in {file.name}")
            continue

        # Clean duplicate header rows that sometimes appear inside body
        selected = selected[selected[selected.columns[0]] != selected.columns[0]]
        # Remove rows that are just month labels (letters only)
        selected = selected[~selected[selected.columns[0]].astype(str).str.match(r"^[A-Za-z]+$")]

        player_id = file.stem.split("_")[0]
        season_year = datetime.now().year
        out_file = parsed_path / f"{player_id}_{season_year}.csv"
        selected.to_csv(out_file, index=False)
        print(f"Parsed game-log CSV saved: {out_file}")

async def main():
    """Main function to run the entire scraping pipeline."""
    # Step 1: Get all MLB teams
    print("Scraping MLB team depth chart URLs...")
    await scrape_mlb_teams()
    
    # Step 2: Scrape all team depth charts
    print("Scraping individual team depth charts...")
    scrape_team_depth_charts()
    
    # Step 3: Combine into all_players.csv
    print("Creating combined all_players.csv...")
    players_df = create_all_players_csv()
    
    # Step 4: Scrape player positions
    print("Scraping player positions...")
    players_df = await scrape_player_positions(players_df)
    
    # Step 5: Create pitcher/hitter CSVs
    print("Categorizing pitchers and hitters...")
    pitchers_df, hitters_df = filter_pitchers_hitters(players_df)
    
    # Step 6: Scrape MLB Savant data
    print("Scraping MLB Savant data for all players...")
    await process_players(players_df)
    
    # Step 7: Download game-log HTML pages
    print("Downloading game-log pages for hitters...")
    await _scrape_game_logs(hitters_df, "hitter")
    print("Downloading game-log pages for pitchers...")
    await _scrape_game_logs(pitchers_df, "pitcher")
    
    # Step 8: Parse saved game-log HTML into CSVs
    print("Parsing hitter game logs...")
    _parse_game_logs(RAW_HITTER_LOG_DIR, PARSED_HITTER_LOG_DIR, "hitter")
    print("Parsing pitcher game logs...")
    _parse_game_logs(RAW_PITCHER_LOG_DIR, PARSED_PITCHER_LOG_DIR, "pitcher")
    
    print("All scraping complete!")

if __name__ == "__main__":
    asyncio.run(main()) 