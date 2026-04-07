from playwright.sync_api import sync_playwright
import csv
import time
import os
import re
import random

print("USING ONLY FIRST 3 GAMES")

def extract_alt_strikeouts(page):
    rows = []
    # Find and expand the Alt Strikeouts sections
    alt_strikeout_buttons = page.locator('button:has-text("Alt Strikeouts")')
    count = alt_strikeout_buttons.count()
    
    print(f"Found {count} Alt Strikeouts buttons")
    
    for i in range(count):
        button = alt_strikeout_buttons.nth(i)
        pitcher_name = button.inner_text().split(' - ')[0].strip()
        print(f"Expanding {pitcher_name} Alt Strikeouts")
        button.scroll_into_view_if_needed()
        button.click()
        time.sleep(2)
        
        # Find all strikeout lines within the expanded section
        # The button's parent div contains all the strikeout options
        parent = button.locator('xpath=..')
        strikeout_lines = parent.locator('xpath=following-sibling::div').locator('li')
        lines_count = strikeout_lines.count()
        
        print(f"  Found {lines_count} strikeout lines")
        
        for j in range(lines_count):
            line_text = strikeout_lines.nth(j).inner_text()
            # Expected format: "X+ Strikeouts +/-NNN"
            match = re.search(r'(\d+\+) Strikeouts ([+-]\d+)', line_text)
            if match:
                line = match.group(1)
                odds = match.group(2)
                rows.append((pitcher_name, line, odds))
                print(f"  Added: {pitcher_name}, {line}, {odds}")
    
    return rows

with sync_playwright() as p:
    # Attach to local Chrome profile to reuse session and avoid CAPTCHA
    user_data_dir = os.path.join(os.getcwd(), 'playwright_user_data')
    os.makedirs(user_data_dir, exist_ok=True)
    
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=False,
        permissions=["geolocation"]
    )
    
    # Set geolocation to New Jersey
    context.set_geolocation({"latitude": 40.0583, "longitude": -74.4057})
    context.set_extra_http_headers({"accept-language": "en-US,en;q=0.9"})
    
    # Prepare output
    output_file = 'mlb_alt_strikeouts.csv'
    json_file = 'mlb_alt_strikeouts.json'
    
    # Read game URLs
    with open('data/2025-05-11/fanduel_game_links.csv', 'r') as f:
        reader = csv.reader(f)
        urls = [row[0] for row in reader if row][:3]
    
    all_rows = []
    
    for url in urls:
        try:
            print(f'\nProcessing: {url}')
            page = context.new_page()
            page.goto(url)
            time.sleep(5)
            
            # Make sure we're on the pitcher props tab
            try:
                pitcher_props_tab = page.get_by_role('tab', name='Pitcher Props')
                pitcher_props_tab.click()
                time.sleep(2)
            except:
                print("Already on Pitcher Props tab or tab not found")
            
            # Extract the alt strikeout data
            extracted = extract_alt_strikeouts(page)
            
            # Add the results to our collection
            for pitcher, line, odds in extracted:
                all_rows.append((url, pitcher, line, odds))
                
            # Take a screenshot for verification
            game_id = url.split('?')[0].split('-')[-1]
            page.screenshot(path=f"data/2025-05-11/{game_id}_screenshot.png")
            
            # Close page and wait before next request
            page.close()
            delay = random.uniform(8, 12)
            print(f"Waiting {delay:.1f} seconds before next URL")
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Write results to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['game_url', 'pitcher', 'line', 'odds'])
        writer.writerows(all_rows)
    
    # Write results to JSON
    import json
    json_data = []
    for url, pitcher, line, odds in all_rows:
        json_data.append({
            "game_url": url,
            "pitcher": pitcher,
            "line": line,
            "odds": odds
        })
    
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f'\nSuccessfully wrote {len(all_rows)} rows to {output_file} and {json_file}')
    context.close() 