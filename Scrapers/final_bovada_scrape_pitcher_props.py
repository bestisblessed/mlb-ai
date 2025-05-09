import os
import json
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

today = datetime.now().strftime("%Y-%m-%d")
folder = f"data/{today}"
os.makedirs(folder, exist_ok=True)
links_file = f"{folder}/bovada_game_links.csv"
output_file = f"{folder}/bovada_pitcher_props_{today}.json"
with open(links_file) as f:
    urls = [line.strip() for line in f if line.strip()]
print(f"Loaded {len(urls)} game URLs from {links_file}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    #browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    pitcher_count = 0
    line_count = 0
    
    for url in urls:
        game_id = url.split('/')[-1]
        game_output_file = f"{folder}/bovada_pitcher_props_{today}_{game_id}.json"
        game_pitchers = []
        
        print(f"\nProcessing: {url}")
        try:
            page.goto(url, timeout=60000)
            time.sleep(1)
            print("Looking for Pitcher Props tab...")
            tab_found = False
            try:
                tabs = page.query_selector_all("span.sp-display-group-menu__list__item__description")
                for tab in tabs:
                    if tab.inner_text().strip() == "Pitcher Props":
                        print("Found Pitcher Props tab")
                        tab.click()
                        tab_found = True
                        break  
                if not tab_found:
                    print("Tab not found by exact match, trying contains search")
                    pitcher_tab = page.query_selector("span:has-text('Pitcher Props')")
                    if pitcher_tab:
                        pitcher_tab.click()
                        tab_found = True
            except Exception as e:
                print(f"Error finding tab: {e}")
            if not tab_found:
                print("Could not find Pitcher Props tab, skipping this game")
                continue
            print("Waiting for content to load...")
            time.sleep(2)
            content = page.content()
            game_data = []
            if "Alternate Strikeouts" in content:
                print("Found 'Alternate Strikeouts' in page content")
                pitcher_pattern = r'Alternate Strikeouts - ([^(]+) \(([^)]+)\)'
                pitcher_matches = list(re.finditer(pitcher_pattern, content))
                for match in pitcher_matches:
                    pitcher_name = match.group(1).strip()
                    team = match.group(2).strip()
                    print(f"Found pitcher: {pitcher_name} ({team})")
                    pitcher_data = {
                        "game_url": url,
                        "pitcher": pitcher_name,
                        "team": team,
                        "lines": []
                    }
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(content), match.end() + 2000)
                    section = content[start_pos:end_pos]
                    
                    # Try multiple patterns to capture odds
                    strikeout_lines = re.findall(r'(\d+\+\s*Strikeouts)[^<>]*?</span>[^<>]*?<span[^<>]*?>([+-]\d+)', section)
                    
                    # Fallback patterns if the first one doesn't work
                    if not strikeout_lines:
                        strikeout_lines = re.findall(r'(\d+\+\s*Strikeouts)</span>.*?<span[^>]*>([+-]\d+)', section)
                    
                    if not strikeout_lines:
                        # Try to parse the table structure directly
                        rows = re.findall(r'<div[^>]*?market-cell[^>]*?>.*?(\d+\+\s*Strikeouts).*?([+-]\d+).*?</div>', section, re.DOTALL)
                        if rows:
                            strikeout_lines = rows
                    
                    # Last attempt - try a very broad pattern
                    if not strikeout_lines:
                        strikeout_lines = re.findall(r'(\d+\+\s*Strikeouts).*?([+-]\d+)', section)
                    
                    # Add all found lines to pitcher data
                    if strikeout_lines:
                        for outcome, odds in strikeout_lines:
                            line = outcome.strip()
                            odds_value = odds.strip()
                            pitcher_data["lines"].append({
                                "line": line,
                                "odds": odds_value
                            })
                            print(f"  {line}: {odds_value}")
                            
                    if pitcher_data["lines"]:
                        game_pitchers.append(pitcher_data)
                        pitcher_count += 1
                        line_count += len(pitcher_data["lines"])
                    else:
                        print(f"No lines found for {pitcher_name}")
            else:
                print("No Alternate Strikeouts section found for this game")
            time.sleep(2)

            if game_pitchers:
                with open(game_output_file, "w") as f:
                    json.dump(game_pitchers, f, indent=2)
                print(f"Saved to {game_output_file}")
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    browser.close()

print(f"\nTotal pitchers: {pitcher_count}")
print(f"Total lines: {line_count}")
print(f"Average lines per pitcher: {line_count/pitcher_count if pitcher_count else 0:.1f}")