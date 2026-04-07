from playwright.sync_api import sync_playwright
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
with sync_playwright() as p:
    #browser = p.chromium.launch(headless=True)
    #browser = p.chromium.launch(headless=False)
    #page = browser.new_page()
    
    browser = p.chromium.launch(headless=False, args=[
    #browser = p.chromium.launch(headless=True, args=[
        #'--disable-blink-features=AutomationControlled',
        #'--disable-infobars',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        #'--disable-gpu',
        #'--window-size=1280,800',
    ])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width":1280, "height":800},
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9"
        },
        ignore_https_errors=True
    )
    page = context.new_page()

    out_path = f"{folder}/fanduel_pitcher_props.csv"
    fieldnames = ['url', 'pitcher', 'line', 'odds']

    # Write header only if file does not exist
    if not os.path.exists(out_path):
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    for url in urls:
        print(f"Scraping: {url}")
        time.sleep(11)
        new_rows = []
        try:
            page.goto(url, timeout=60000)
            time.sleep(4)
            # DEBUG: Print all button texts on the page
            all_buttons = page.query_selector_all('button')
            print('--- BUTTON TEXTS ON PAGE ---')
            for btn in all_buttons:
                try:
                    print(btn.inner_text())
                except Exception:
                    continue
            # DEBUG: Print all elements with role="button"
            role_buttons = page.query_selector_all('[role="button"]')
            print('--- [role="button"] TEXTS ON PAGE ---')
            for btn in role_buttons:
                try:
                    print(btn.inner_text())
                except Exception:
                    continue
            # DEBUG: Print all clickable divs and spans (tabindex or onclick)
            clickable_divs = page.query_selector_all('div[tabindex], div[onclick], span[tabindex], span[onclick]')
            print('--- CLICKABLE DIVS/SPANS TEXTS ON PAGE ---')
            for el in clickable_divs:
                try:
                    print(el.inner_text())
                except Exception:
                    continue
            # Click all buttons whose text ends with ' - Alt Strikeouts'
            alt_buttons = page.get_by_role("button")
            count = alt_buttons.count()
            for i in range(count):
                btn = alt_buttons.nth(i)
                try:
                    text = btn.inner_text()
                    if re.search(r" - Alt Strikeouts$", text.strip()):
                        btn.click()
                        time.sleep(1)
                except Exception:
                    continue
            time.sleep(2)
            # Extract all Alt Strikeouts lines
            alt_lines = page.query_selector_all('div[role="button"][aria-label*="Alt Strikeouts"]')
            for div in alt_lines:
                try:
                    aria = div.get_attribute("aria-label")
                    odds = div.inner_text()
                    # Example aria: 'Logan Evans - Alt Strikeouts, Logan Evans 3+ Strikeouts, -104'
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
        # Append new rows to CSV after each URL
        if new_rows:
            with open(out_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(new_rows)
        #time.sleep(10)
    browser.close()

df = pd.DataFrame(rows)
os.makedirs(folder, exist_ok=True)
df.to_csv(f"{folder}/fanduel_pitcher_props.csv", index=False)
print(df)