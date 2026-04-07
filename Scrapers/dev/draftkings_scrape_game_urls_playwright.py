import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

today = datetime.now().strftime("%Y-%m-%d")
os.makedirs(f'data/{today}', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    try:
        print("Navigating to DraftKings MLB page...")
        page.goto("https://sportsbook.draftkings.com/leagues/baseball/mlb", timeout=60000)
        
        # Wait for the page to load
        time.sleep(4)
        
        # Find all game links in the table rows
        game_links = []
        rows = page.query_selector_all('table tr[class*="sportsbook-table__row"]')
        
        for row in rows:
            # Skip header rows
            if row.query_selector('th'):
                continue
                
            # Look for links in the team name cells
            link = row.query_selector('td a[href*="/event/"]')
            if link:
                href = link.get_attribute('href')
                if href and '/event/' in href:
                    # Extract just the base URL
                    base_url = href.split('?')[0]
                    # Only include URLs that aren't already in our list
                    if base_url not in [url.split('?')[0] for url in game_links]:
                        props_url = f"{base_url}?category=odds&subcategory=pitcher-props"
                        game_links.append(props_url)
                        print(f"Found game: {props_url}")
        
        # Save game links to file
        output_file = f"data/{today}/draftkings_game_links.csv"
        with open(output_file, 'w') as f:
            for link in game_links:
                f.write(f"{link}\n")
        
        print(f"Saved {len(game_links)} game links to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        browser.close() 