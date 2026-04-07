import os
import json
import time
import re
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

today = datetime.now().strftime("%Y-%m-%d")
folder = f"data/{today}"
os.makedirs(folder, exist_ok=True)
links_file = f"{folder}/draftkings_game_links.csv"

# Check if the links file exists
if not os.path.exists(links_file):
    print(f"Error: Links file {links_file} not found. Run draftkings_scrape_game_urls_playwright.py first.")
    exit(1)

with open(links_file) as f:
    urls = [line.strip() for line in f if line.strip()]
print(f"Loaded {len(urls)} game URLs from {links_file}")

combined_csv_file = f"{folder}/draftkings_all_pitcher_props_{today}.csv"
all_pitchers_data = {}  # Use dictionary to avoid duplicates

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Set to False to debug visually
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    
    for url_index, url in enumerate(urls):
        game_id = re.search(r'\/(\d+)', url).group(1) if re.search(r'\/(\d+)', url) else f"game_{url_index}"
        
        print(f"Processing game {url_index + 1}/{len(urls)}: {url}")
        try:
            page.goto(url, timeout=60000)
            time.sleep(5)  # Fixed wait time
            
            # Check if the Strikeouts Thrown section exists
            strikeouts_section = page.query_selector('button:has(div:has-text("Strikeouts Thrown"))')
            if not strikeouts_section:
                print(f"  No pitcher props found for game {game_id}, skipping...")
                continue
            
            # Make sure the section is expanded
            expanded_attr = strikeouts_section.get_attribute('aria-expanded')
            if expanded_attr != 'true':
                strikeouts_section.click()
                time.sleep(2)
            
            # Get away and home team names from the header
            team_names = page.query_selector('div.event-header__title')
            teams_text = team_names.inner_text() if team_names else "Unknown vs Unknown"
            away_team, home_team = "Unknown", "Unknown"
            if " AT " in teams_text:
                away_team, home_team = teams_text.split(' AT ')
            
            # Find all pitchers in the Strikeouts Thrown section
            pitcher_rows = page.query_selector_all('div.sportsbook-table-row__contents:has(p.sportsbook-row-name)')
            processed_pitchers = set()  # Track processed pitchers to avoid duplicates
            
            for pitcher_row in pitcher_rows:
                # Extract the pitcher name
                pitcher_name_elem = pitcher_row.query_selector('p.sportsbook-row-name')
                if not pitcher_name_elem:
                    continue
                
                pitcher_name = pitcher_name_elem.inner_text().strip()
                
                # Skip if we've already processed this pitcher
                if pitcher_name in processed_pitchers:
                    continue
                
                processed_pitchers.add(pitcher_name)
                
                # Determine team based on position in the list (first pitcher is away, second is home)
                team = away_team if len(processed_pitchers) % 2 == 1 else home_team
                opponent = home_team if team == away_team else away_team
                
                print(f"  Processing pitcher: {pitcher_name} ({team})")
                
                # Create a unique key for this pitcher
                pitcher_key = f"{game_id}_{pitcher_name}"
                
                # Initialize data for this pitcher
                if pitcher_key not in all_pitchers_data:
                    all_pitchers_data[pitcher_key] = {
                        'game_id': game_id,
                        'date': today,
                        'pitcher_name': pitcher_name,
                        'team': team,
                        'opponent': opponent
                    }
                    # Initialize K+ columns with None
                    for k in range(3, 11):
                        all_pitchers_data[pitcher_key][f'K{k}+_odds'] = None
                
                # Find all K+ options for this pitcher by clicking arrows and capturing all available options
                # First, find the section containing this pitcher's strikeout options
                pitcher_section = None
                sections = page.query_selector_all('div.sportsbook-event-accordion__wrapper')
                
                for section in sections:
                    name_in_section = section.query_selector(f'p:text("{pitcher_name}")')
                    if name_in_section:
                        pitcher_section = section
                        break
                
                if not pitcher_section:
                    print(f"    Could not find strikeout section for {pitcher_name}")
                    continue
                
                # Click left arrow until we reach the beginning
                while True:
                    left_arrow = pitcher_section.query_selector('button:has(img[alt="Arrow pointing left icon"])')
                    if left_arrow and left_arrow.is_visible():
                        try:
                            left_arrow.click()
                            time.sleep(0.5)
                        except:
                            break
                    else:
                        break
                
                # Now process each visible option and click right arrow to see more
                max_clicks = 10  # Limit to avoid infinite loops
                for _ in range(max_clicks):
                    # Process all currently visible K+ buttons
                    k_buttons = pitcher_section.query_selector_all('button:has(div:text-matches("\\d\\+"))')
                    
                    for button in k_buttons:
                        button_text = button.inner_text().strip()
                        
                        # Extract K value and odds from button text
                        k_match = re.search(r'(\d+)\+', button_text)
                        odds_match = re.search(r'([-+]\d+)', button_text)
                        
                        if k_match:
                            k_value = int(k_match.group(1))
                            odds = odds_match.group(1) if odds_match else None
                            
                            if odds and 3 <= k_value <= 10:  # Only capture realistic K values
                                print(f"    Found K{k_value}+ odds: {odds}")
                                all_pitchers_data[pitcher_key][f'K{k_value}+_odds'] = odds
                    
                    # Click right arrow to see more options
                    right_arrow = pitcher_section.query_selector('button:has(img[alt="Arrow pointing right icon"])')
                    if right_arrow and right_arrow.is_visible():
                        try:
                            right_arrow.click()
                            time.sleep(0.5)
                        except:
                            break
                    else:
                        break
                        
        except Exception as e:
            print(f"  Error processing game {game_id}: {str(e)}")
    
    # Convert the dictionary to a DataFrame
    if all_pitchers_data:
        df = pd.DataFrame.from_dict(all_pitchers_data, orient='index')
        
        # Save to CSV
        df.to_csv(combined_csv_file, index=False)
        print(f"Saved {len(df)} pitcher prop records to {combined_csv_file}")
    else:
        print("No pitcher prop data was found.")
    
    browser.close() 