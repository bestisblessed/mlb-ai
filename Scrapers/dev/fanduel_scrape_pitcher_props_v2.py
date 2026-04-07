from playwright.sync_api import sync_playwright
import pandas as pd
import os
import time
import csv
from datetime import datetime
import re

today = datetime.now().strftime("%Y-%m-%d")
folder = f'data/{today}'
#with open(f'{folder}/fanduel_game_links.csv') as f:
#    urls = [line.strip() for line in f if line.strip()]

# TEST: Only use the Toronto-Seattle game URL
urls = ["https://sportsbook.fanduel.com/baseball/mlb/toronto-blue-jays-@-seattle-mariners-34303310?tab=pitcher-props"]

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
            # Click all buttons whose text ends with ' - Alt Strikeouts' and wait for modal
            alt_buttons = page.get_by_role("button")
            count = alt_buttons.count()
            for i in range(count):
                btn = alt_buttons.nth(i)
                try:
                    text = btn.inner_text()
                    if re.search(r" - Alt Strikeouts$", text.strip()):
                        print(f"Clicking: {text}")
                        btn.click()
                        # Wait for a unique selector inside the modal (e.g., a table or text)
                        try:
                            time.sleep(3)
                            print('--- FULL PAGE HTML AFTER CLICK ---')
                            print(page.content())
                        except Exception as e:
                            print(f"Modal wait error: {e}")
                        time.sleep(1)
                except Exception as e:
                    print(f"Error: {e}")
                    continue
            page.wait_for_timeout(2000)
            #page.wait_for_selector('div:has-text("Alt Strikeouts")', timeout=15000)
            sections = page.query_selector_all('div:has-text("Alt Strikeouts")')
            for section in sections:
                header = section.query_selector('div:has-text("Alt Strikeouts")')
                pitcher = header.inner_text().split(' - ')[0] if header else ''
                for row in section.query_selector_all('div[role=\"row\"]'):
                    try:
                        k_text = row.query_selector('span').inner_text()
                        odds = row.query_selector('button').inner_text()
                        new_rows.append({'url': url, 'pitcher': pitcher, 'line': k_text, 'odds': odds})
                    except Exception:
                        continue
        except Exception:
            continue
        # Append new rows to CSV after each URL
        if new_rows:
            with open(out_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(new_rows)
        time.sleep(10)
    browser.close()

df = pd.DataFrame(rows)
os.makedirs(folder, exist_ok=True)
df.to_csv(f"{folder}/fanduel_pitcher_props.csv", index=False)
print(df)