from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import pandas as pd
import os
import time
import csv
from datetime import datetime
import re

today = datetime.now().strftime("%Y-%m-%d")
folder = f'data/{today}'
with open(f'{folder}/fanduel_game_links.csv') as f:
    urls = [line.strip() for line in f if line.strip()]

rows = []
for url in urls:
    print(f"Scraping: {url}")
    time.sleep(13)
    new_rows = []
    with sync_playwright() as p:
        
        # Chrome
        #browser = p.chromium.launch(headless=False, args=[
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ])
        context = browser.new_context(
            #user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            user_agent="Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width":1280, "height":800},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            ignore_https_errors=True
        )
        
        ## Firefox
        #browser = p.firefox.launch(headless=False)
        #context = browser.new_context()
        
        
        page = context.new_page()
        stealth_sync(page)
        out_path = f"{folder}/fanduel_pitcher_props.csv"
        fieldnames = ['url', 'pitcher', 'line', 'odds']
        if not os.path.exists(out_path):
            with open(out_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        try:
            page.goto(url, timeout=60000)
            time.sleep(15)
            alt_buttons = page.get_by_role("button")
            count = alt_buttons.count()
            for i in range(count):
                btn = alt_buttons.nth(i)
                try:
                    text = btn.inner_text()
                    if re.search(r" - Alt Strikeouts$", text.strip()):
                        btn.click()
                        time.sleep(2)
                        # Print the raw HTML of the parent container (table)
                        parent = btn.evaluate_handle("el => el.closest('li')")
                        if parent:
                            print("--- RAW ALT TABLE HTML ---")
                            print(parent.inner_html())
                except Exception:
                    continue
            time.sleep(2)
            alt_lines = page.query_selector_all('div[role="button"][aria-label*="Alt Strikeouts"]')
            for div in alt_lines:
                try:
                    aria = div.get_attribute("aria-label")
                    odds = div.inner_text()
                    parts = aria.split(',')
                    if len(parts) == 3:
                        pitcher = parts[0].replace(' - Alt Strikeouts', '').strip()
                        line = parts[1].replace(f'{pitcher} ', '').replace('Strikeouts', '').strip()
                        odds_val = parts[2].strip()
                        new_rows.append({'url': url, 'pitcher': pitcher, 'line': line, 'odds': odds_val})
                except Exception:
                    continue
        except Exception:
            continue
        if new_rows:
            with open(out_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(new_rows)
        browser.close()

df = pd.DataFrame(rows)
os.makedirs(folder, exist_ok=True)
df.to_csv(f"{folder}/fanduel_pitcher_props.csv", index=False)
print(df)