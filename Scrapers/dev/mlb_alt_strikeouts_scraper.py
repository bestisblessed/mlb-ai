from playwright.sync_api import sync_playwright
import csv
import time
import re
import os
import random
from datetime import datetime

def random_sleep(min_seconds=2, max_seconds=5):
    """Sleep for a random time between min and max seconds"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_game_id(url):
    # Extract game ID from the URL using regex
    match = re.search(r'/baseball/mlb/.*-(\d+)\?', url)
    if match:
        return match.group(1)
    return "unknown"

def extract_team_names(url):
    # Extract team names from the URL
    match = re.search(r'/baseball/mlb/(.*-@-.*)-\d+\?', url)
    if match:
        teams = match.group(1).replace('-@-', ' @ ').replace('-', ' ')
        return teams
    return "unknown matchup"

def human_scroll(page):
    """Scroll like a human would"""
    # Get page height
    height = page.evaluate('() => document.body.scrollHeight')
    # Scroll down in chunks with random pauses
    for i in range(0, height, random.randint(100, 300)):
        page.evaluate(f'window.scrollTo(0, {i})')
        random_sleep(0.1, 0.3)

def scrape_alt_strikeouts(url, output_dir):
    with sync_playwright() as p:
        # Use a persistent context to maintain cookies
        user_data_dir = "playwright_user_data"
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True
        )
        
        page = browser.new_page()
        
        # Add extra headers to appear more like a browser
        page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # Navigate to the URL
        print(f"Navigating to {url}")
        page.goto(url)
        random_sleep(4, 7)  # Let page load
        
        # Check if we hit a CAPTCHA
        if "verify you are a human" in page.content().lower() or "press & hold" in page.content().lower():
            print("CAPTCHA detected! Waiting for human interaction...")
            # Wait for user to solve CAPTCHA
            input("Press Enter after solving the CAPTCHA...")
        
        # Human-like scrolling
        human_scroll(page)
        random_sleep(1, 3)
        
        game_id = extract_game_id(url)
        matchup = extract_team_names(url)
        print(f"Processing game: {matchup} (ID: {game_id})")
        
        data = []

        # Look for alt strikeout sections
        alt_strikeout_buttons = page.query_selector_all('button:has-text("- Alt Strikeouts")')
        
        # If no buttons found, try scrolling more and searching again
        if not alt_strikeout_buttons:
            print("No Alt Strikeouts buttons found, scrolling more...")
            human_scroll(page)
            random_sleep(2, 3)
            alt_strikeout_buttons = page.query_selector_all('button:has-text("- Alt Strikeouts")')
        
        print(f"Found {len(alt_strikeout_buttons)} Alt Strikeouts buttons")
        
        for i, button in enumerate(alt_strikeout_buttons):
            # Scroll to make button visible
            button.scroll_into_view_if_needed()
            random_sleep(0.5, 1.5)
            
            # Click to expand the alt strikeout section
            button.click()
            random_sleep(1.5, 3)  # Wait for expansion
            
            # Get pitcher name from button text
            button_text = button.inner_text()
            pitcher_name = button_text.split(' - Alt')[0].strip()
            
            # Determine team based on position in page
            team = None
            if ' @ ' in matchup:
                teams = matchup.split(' @ ')
                team = teams[0] if i == 0 else teams[1]
            
            print(f"Extracting data for {pitcher_name} ({team})")
            
            # Get all the lines and odds
            lines = page.query_selector_all(f'button:has-text("{pitcher_name} ")')
            for line in lines:
                if '+ Strikeouts' in line.inner_text():
                    line.scroll_into_view_if_needed()
                    random_sleep(0.2, 0.7)
                    
                    line_text = line.inner_text()
                    strikeouts = line_text.split('+ Strikeouts')[0].split(pitcher_name)[1].strip()
                    
                    # Get the odds from the adjacent element
                    odds_elements = page.query_selector_all(f'button:has-text("{pitcher_name} {strikeouts}+ Strikeouts")')
                    for odds_element in odds_elements:
                        if '+ Strikeouts' in odds_element.inner_text():
                            odds_text = odds_element.evaluate('el => {const span = el.querySelector("span:last-child"); return span ? span.innerText : "";}')
                            if odds_text:
                                data.append({
                                    'game_url': url,
                                    'team': team,
                                    'pitcher': pitcher_name,
                                    'line': f"{strikeouts}+",
                                    'odds': odds_text
                                })
            
            # Close the expanded section to keep page clean
            random_sleep(0.5, 1.5)
            button.click()
            random_sleep(1, 2)
        
        browser.close()
        
        # Save data to CSV
        if data:
            os.makedirs(output_dir, exist_ok=True)
            csv_file = os.path.join(output_dir, f"game_{game_id}.csv")
            
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['game_url', 'team', 'pitcher', 'line', 'odds'])
                writer.writeheader()
                writer.writerows(data)
            
            print(f"Saved data to {csv_file}")
            return data
        else:
            print("No data found")
            return []

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    csv_file = "fanduel_pitcher_props_urls.csv"
    output_dir = f"data/{today}/pitcher_lines"
    
    all_data = []
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read URLs from CSV
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        urls = [row['url'] for row in reader if row['url'].strip()]
    
    # Process each URL
    for i, url in enumerate(urls):
        print(f"\nProcessing game {i+1}/{len(urls)}")
        try:
            data = scrape_alt_strikeouts(url, output_dir)
            all_data.extend(data)
            
            # Random delay between requests to avoid detection
            if i < len(urls) - 1:
                delay = random.randint(7, 15)  # More variable delay
                print(f"Waiting {delay} seconds before next game...")
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Save aggregated data
    if all_data:
        aggregated_file = "mlb_alt_strikeouts.csv"
        with open(aggregated_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['game_url', 'team', 'pitcher', 'line', 'odds'])
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nSaved all data to {aggregated_file}")
    
    print("\nScraping completed!")

if __name__ == "__main__":
    main() 