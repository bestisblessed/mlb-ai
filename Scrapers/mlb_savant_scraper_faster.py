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
import math, aiohttp, json
from tqdm import tqdm
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
        df['Player ID'] = df['Player URL'].str.split('/').str[-1]
        df['Player ID'] = df['Player ID'].astype(str)
        all_players.append(df)
    
    all_players_df = pd.concat(all_players, ignore_index=True)
    
    # Guarantee Position column exists to avoid KeyError later
    if "Position" not in all_players_df.columns:
        all_players_df["Position"] = ""
    
    all_players_df.to_csv("data/mlb/all_players.csv", index=False)
    print(f"Combined {len(all_players)} team rosters into all_players.csv")
    print(f"Total players: {len(all_players_df)}")
    return all_players_df

# ------------------------------------------------------------------
# Fast position fetch: StatsAPI  (≈ 300 ms per 100 players)
# ------------------------------------------------------------------
def _patch_positions_via_statsapi(players_df, batch=100):
    """Fill the Position column using statsapi.mlb.com (no browser)."""
    players_df["Player ID"] = players_df["Player ID"].astype(str)
    players_df["MLB_ID"] = players_df["Player ID"].str.extract(r"(\d+)$")
    need = players_df[players_df["Position"].isna() | (players_df["Position"] == "")]
    ids   = need["MLB_ID"].dropna().unique().tolist()

    for i in range(0, len(ids), batch):
        chunk = ids[i : i + batch]
        url   = f"https://statsapi.mlb.com/api/v1/people?personIds={','.join(chunk)}"
        try:
            data = requests.get(url, timeout=10).json().get("people", [])
            for p in data:
                pos = p.get("primaryPosition", {}).get("abbreviation", "")
                if not pos:
                    continue
                players_df.loc[players_df["MLB_ID"] == str(p["id"]), "Position"] = pos
        except Exception as e:
            print(f"StatsAPI chunk {i//batch+1}: {e}")

    players_df.drop(columns="MLB_ID", inplace=True, errors="ignore")
    return players_df


# ------------------------------------------------------------------
# Browser fallback for the leftovers, but concurrent (semaphore)
# ------------------------------------------------------------------
async def scrape_player_positions(players_df, max_concurrent: int = 6):
    """
    1. First hit StatsAPI (fast JSON).
    2. Then scrape the few still-unknown players with Playwright, `max_concurrent`
       pages at a time (defaults to 6, safe for MLB.com).
    """
    players_df = _patch_positions_via_statsapi(players_df)

    todo_idx = players_df[
        players_df["Position"].isna() | (players_df["Position"].str.strip() == "")
    ].index
    print(f"➡️  Need browser for {len(todo_idx)} players after StatsAPI.")

    if not len(todo_idx):
        return players_df

    sem = asyncio.Semaphore(max_concurrent)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def fetch(idx):
            row = players_df.loc[idx]
            url = row["Player URL"]
            async with sem:
                page = await browser.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    soup = BeautifulSoup(await page.content(), "html.parser")
                    span = soup.select_one("span.position")
                    players_df.at[idx, "Position"] = (
                        span.get_text(strip=True) if span else "UNKNOWN"
                    )
                except Exception as e:
                    print(f"⚠️  {row['Name']} – {e}")
                    players_df.at[idx, "Position"] = "ERROR"
                finally:
                    await page.close()

        # Kick off tasks
        await asyncio.gather(*(fetch(i) for i in todo_idx))
        await browser.close()

    players_df.to_csv("data/mlb/all_players.csv", index=False)
    print("✅ Position scraping complete.")
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

# -------------------------------------------------------------
# Game-log HTML downloader (Playwright, concurrent)
# -------------------------------------------------------------
async def _scrape_game_logs(players_df: pd.DataFrame, player_type: str = "hitter", concurrency: int = 6, max_retries: int = 3):
    """Download each player's game-log page HTML for the current season."""
    out_dir = RAW_HITTER_LOG_DIR if player_type == "hitter" else RAW_PITCHER_LOG_DIR
    season = datetime.now().year
    total = len(players_df)
    pbar = tqdm(total=total, desc=f"{player_type.title()} logs", unit="player")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sem = asyncio.Semaphore(concurrency)

        async def grab(row):
            player_id = row["Player ID"]
            url = row["Game Log URL"]
            save_path = f"{out_dir}/{player_id}_{season}.html"
            if os.path.exists(save_path) and os.path.getsize(save_path) > 50000:
                pbar.update(1)
                return
            async with sem:
                for attempt in range(1, max_retries + 1):
                    page = await browser.new_page()
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=60000)
                        try:
                            # Wait up to 10 s for any <table> element to be rendered (JS-driven)
                            await page.wait_for_selector("table", timeout=10000)
                        except Exception:
                            # Even if selector wait fails we proceed—HTML may still include JSON for stats
                            pass
                        html_text = await page.content()
                        with open(save_path, "w", encoding="utf-8") as f:
                            f.write(html_text)
                        # success – progress bar increment
                        pbar.update(1)
                        break  # success
                    except Exception as e:
                        if attempt == max_retries:
                            print(f"⚠️  Game-log fetch error {player_id} after {max_retries} attempts: {e}")
                        else:
                            await asyncio.sleep(2 * attempt)  # simple back-off
                    finally:
                        await page.close()
                        if attempt == max_retries:
                            # even on failure count progress so bar moves
                            pbar.update(1)

        await asyncio.gather(*(grab(r) for _, r in players_df.iterrows()))
        await browser.close()
    pbar.close()
    print(f"✅ Downloaded {player_type} game logs → {out_dir}")

# -------------------------------------------------------------
# HTML → CSV parser
# -------------------------------------------------------------
from lxml import html as lxml_html

def _parse_game_logs(raw_dir: str, parsed_dir: str, player_type: str):
    """Parse raw game-log HTML files into per-player CSVs."""
    season = datetime.now().year
    for file in Path(raw_dir).glob("*.html"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                html_text = f.read()
            tables = pd.read_html(StringIO(html_text))
        except Exception as e:
            print(f"Failed to parse tables from {file.name}: {e}")
            continue

        target = None
        for tbl in tables:
            cols = set(map(str, tbl.columns))
            if player_type == "hitter" and ("Date" in cols) and ("AB" in cols or "R" in cols or "H" in cols):
                target = tbl
                break
            if player_type == "pitcher" and ("IP" in cols or "ERA" in cols):
                target = tbl
                break
        if target is None:
            if player_type == "hitter":
                # Fallback: pull game-log via StatsAPI JSON
                pid = file.stem.split("_")[0]
                try:
                    season_str = str(season)
                    api_url = (
                        f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=gameLog&sportIds=1&"+
                        f"season={season_str}&group=hitting"
                    )
                    api_json = requests.get(api_url, timeout=15).json()
                    splits = (
                        api_json.get("stats", [{}])[0]
                        .get("splits", [])
                    )
                    if not splits and season > 2000:
                        # try previous season as fallback (early season case)
                        prev_url = (
                            f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=gameLog&sportIds=1&"+
                            f"season={int(season)-1}&group=hitting"
                        )
                        api_json = requests.get(prev_url, timeout=15).json()
                        splits = api_json.get("stats", [{}])[0].get("splits", [])
                    if not splits:
                        print(f"No API splits for hitter {pid}")
                        continue
                    rows = []
                    for s in splits:
                        row = {"Date": s.get("date")}
                        row.update(s.get("stat", {}))
                        rows.append(row)
                    target = pd.DataFrame(rows)
                except Exception as e:
                    print(f"API fallback failed for {pid}: {e}")
                    continue
            else:
                print(f"No suitable table in {file.name}")
                continue

        # Clean header duplicates & month rows
        target = target[target[target.columns[0]] != target.columns[0]]
        target = target[~target[target.columns[0]].astype(str).str.match(r"^[A-Za-z]+$")]

        pid = file.stem.split("_")[0]
        outfile = Path(parsed_dir) / f"{pid}_{season}.csv"
        target.to_csv(outfile, index=False)
        print(f"Parsed → {outfile}")

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
    
    # NEW CRITICAL STEP: Scrape player positions
    print("Scraping player positions...")
    players_df = await scrape_player_positions(players_df)
    
    # Step 4: Create pitcher/hitter CSVs
    print("Categorizing pitchers and hitters...")
    pitchers_df, hitters_df = filter_pitchers_hitters(players_df)
    
    # Step 5: Scrape Savant data
    print("Scraping MLB Savant data for all players...")
    await process_players(players_df)

    # NEW: Game-log HTML download & parse
    print("Downloading hitter game-log pages...")
    await _scrape_game_logs(hitters_df, "hitter")
    print("Downloading pitcher game-log pages...")
    await _scrape_game_logs(pitchers_df, "pitcher")

    print("Parsing hitter game-logs to CSV...")
    _parse_game_logs(RAW_HITTER_LOG_DIR, PARSED_HITTER_LOG_DIR, "hitter")
    print("Parsing pitcher game-logs to CSV...")
    _parse_game_logs(RAW_PITCHER_LOG_DIR, PARSED_PITCHER_LOG_DIR, "pitcher")

    print("All scraping complete!")

if __name__ == "__main__":
    asyncio.run(main()) 