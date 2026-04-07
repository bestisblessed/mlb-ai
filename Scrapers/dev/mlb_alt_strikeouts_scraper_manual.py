from playwright.sync_api import sync_playwright
import csv
import time
import os
import re

# Create the output directory if it doesn't exist
os.makedirs('data/2025-05-11/pitcher_lines', exist_ok=True)
os.makedirs('data/2025-05-11/pitcher_screenshots', exist_ok=True)

# Read the game URLs from the CSV file
with open('data/2025-05-11/fanduel_game_links.csv', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

# URLs that have already been processed (first 3 games)
processed_urls = urls[:3]

# Remaining URLs to process
remaining_urls = urls[3:]

# Create a master CSV to collect all data
master_csv_file = 'mlb_alt_strikeouts.csv'
master_data = []

# Read existing data from master CSV
existing_data_urls = set()
with open(master_csv_file, 'r') as f:
    reader = csv.reader(f)
    headers = next(reader)  # Skip header row
    for row in reader:
        master_data.append(row)
        existing_data_urls.add(row[4])  # game_url is in column 4

# Process remaining games
with sync_playwright() as p:
    # Use a persistent context to maintain cookies and avoid CAPTCHA
    user_data_dir = "playwright_user_data"
    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        viewport={"width": 1280, "height": 800},
        permissions=["geolocation"],
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    
    # Set a fixed geolocation (New Jersey coordinates)
    browser.set_geolocation({"latitude": 40.0583, "longitude": -74.4057})
    
    page = browser.new_page()
    page.set_default_timeout(30000)  # 30 seconds timeout
    
    try:
        for i, url in enumerate(remaining_urls):
            if url in existing_data_urls:
                print(f"Skipping {url} - already processed")
                continue
                
            print(f"Processing game {i+4}/{len(urls)} - {url}")
            
            try:
                # Navigate to the game
                page.goto(url)
                time.sleep(5)
                
                # Check for location verification dialog and handle it
                if page.locator("text=Verifying location").count() > 0:
                    print("Waiting for location verification to complete...")
                    # Wait longer for location verification to resolve
                    time.sleep(15)
                
                # Check if we're on the pitcher props tab, click if needed
                try:
                    if "tab=pitcher-props" not in url:
                        pitcher_props_tab = page.get_by_role("button", name="Pitcher Props")
                        pitcher_props_tab.click()
                        time.sleep(2)
                except Exception as e:
                    print(f"Tab navigation error: {e}")
                
                # Get game teams from URL for better data attribution
                match = re.search(r'/baseball/mlb/(.*)-@-(.*)-\d+', url)
                away_team = match.group(1).replace('-', ' ').title() if match else "Away Team"
                home_team = match.group(2).replace('-', ' ').title() if match else "Home Team"
                
                # Create a game-specific CSV
                game_id = url.split('-')[-1].split('?')[0]
                game_csv_file = f"data/2025-05-11/pitcher_lines/game{game_id}_alt_strikeouts.csv"
                
                # Take a screenshot of the page to see what we're working with
                page.screenshot(path=f"data/2025-05-11/pitcher_screenshots/page_{game_id}.png")
                
                # Try to find the Alt Strikeouts buttons (multiple different ways)
                alt_strikeouts_buttons = None
                count = 0
                
                # Try different selectors to find the Alt Strikeouts buttons
                for selector in [
                    'button:has-text("Alt Strikeouts")',
                    'button:has-text("- Alt Strikeouts")',
                    'button >> text=Alt Strikeouts',
                    'button:has-text("Strikeouts")'
                ]:
                    try:
                        alt_strikeouts_buttons = page.locator(selector)
                        count = alt_strikeouts_buttons.count()
                        if count >= 2:
                            print(f"Found {count} Alt Strikeouts buttons with selector: {selector}")
                            break
                    except:
                        continue
                
                if count < 2:
                    print(f"Could not find enough Alt Strikeouts buttons, only found {count}")
                    # Take a screenshot to see what's on the page
                    page.screenshot(path=f"data/2025-05-11/pitcher_screenshots/error_{game_id}.png")
                    continue
                
                game_data = []
                
                # Process each pitcher's Alt Strikeouts table
                for j in range(count):
                    try:
                        button = alt_strikeouts_buttons.nth(j)
                        # Button text should contain the pitcher name
                        pitcher_text = button.inner_text()
                        pitcher_name = pitcher_text.split(' - ')[0].strip()
                        print(f"Expanding {pitcher_name} Alt Strikeouts")
                        
                        # Team assignment based on button position (generally first is away, second is home)
                        team = away_team if j == 0 else home_team
                        
                        # Click to expand the Alt Strikeouts section
                        button.scroll_into_view_if_needed()
                        button.click()
                        time.sleep(2)
                        
                        # Take a screenshot of expanded section
                        page.screenshot(path=f"data/2025-05-11/pitcher_screenshots/{game_id}_{pitcher_name.replace(' ', '_')}.png")
                        
                        # Try to parse the strikeout lines
                        lines = page.locator(f"li:has-text(\"{pitcher_name}\"):has-text(\"Strikeouts\")")
                        lines_count = lines.count()
                        print(f"Found {lines_count} strikeout lines for {pitcher_name}")
                        
                        if lines_count == 0:
                            # Try alternative selector
                            lines = page.locator(f"li:has-text(\"+\"):has-text(\"Strikeouts\")")
                            lines_count = lines.count()
                            print(f"Alternative selector found {lines_count} lines")
                        
                        for k in range(lines_count):
                            line_text = lines.nth(k).inner_text()
                            # Look for patterns like "5+ Strikeouts -2500" or "[Pitcher] 5+ Strikeouts -2500"
                            match = re.search(r'(\d+)\+ Strikeouts\s+([+-]\d+)', line_text)
                            if match:
                                strikeouts = match.group(1) + "+"
                                odds = match.group(2)
                                row = [team, pitcher_name, strikeouts, odds, url]
                                game_data.append(row)
                                master_data.append(row)
                                print(f"Added: {team}, {pitcher_name}, {strikeouts}, {odds}")
                            else:
                                print(f"No match in line text: {line_text}")
                    
                    except Exception as e:
                        print(f"Error processing {pitcher_name}: {e}")
                
                # Write the game-specific data to a CSV
                if game_data:
                    with open(game_csv_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(['team', 'pitcher', 'strikeouts', 'odds', 'game_url'])
                        writer.writerows(game_data)
                    print(f"Saved data for game {game_id} to {game_csv_file}")
                else:
                    print(f"No data found for game {game_id}")
                
                # Random pause between games
                if i < len(remaining_urls) - 1:
                    pause = 10 + (i % 5)  # Longer pauses to avoid detection
                    print(f"Pausing for {pause} seconds before the next game")
                    time.sleep(pause)
                
            except Exception as e:
                print(f"Error processing {url}: {e}")
                # Take a screenshot for debugging
                try:
                    page.screenshot(path=f"data/2025-05-11/pitcher_screenshots/error_{i+4}.png")
                except:
                    pass
        
        # Write all data to the master CSV
        with open(master_csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['team', 'pitcher', 'strikeouts', 'odds', 'game_url'])
            writer.writerows(master_data)
        print(f"Saved all data to {master_csv_file}")
        
    finally:
        browser.close()

print("Scraping completed!") 