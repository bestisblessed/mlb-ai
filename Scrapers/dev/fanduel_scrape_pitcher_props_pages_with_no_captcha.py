from playwright.sync_api import sync_playwright
import csv
import time
import os

def extract_alt_strikeouts(page):
    rows = []
    # Expand all Alt Strikeouts sections
    buttons = page.locator('button', has_text='Alt Strikeouts')
    count = buttons.count()
    for i in range(count):
        btn = buttons.nth(i)
        btn.scroll_into_view_if_needed()
        btn.click()
        time.sleep(1)
    # After expansion, extract all lines
    items = page.locator('li', has_text='+ Strikeouts')
    for j in range(items.count()):
        text = items.nth(j).inner_text().replace('\n', ' ')
        # text example: "Chris Sale 3+ Strikeouts -2200"
        parts = text.rsplit(' ', 2)
        if len(parts) == 3:
            pitcher_line, line_plus, odds = parts
            pitcher = pitcher_line.rsplit(' ', 1)[0]
            line = line_plus.replace(' Strikeouts', '')
            rows.append((pitcher, line, odds))
    return rows

with sync_playwright() as p:
    # Attach to local Chrome profile to reuse session and avoid CAPTCHA
    user_data = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default')
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        channel='chrome',
        headless=False
    )
    page = context.new_page()

    # Prepare output
    output_file = 'mlb_alt_strikeouts.csv'
    with open('data/2025-05-11/fanduel_game_links.csv', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    all_rows = []

    for url in urls:
        print(f'Navigating to {url}')
        page.goto(url)
        time.sleep(5)
        # Extract
        extracted = extract_alt_strikeouts(page)
        for pitcher, line, odds in extracted:
            all_rows.append((url, pitcher, line, odds))
        # Clean up: collapse or reload
        page.reload()
        time.sleep(3)

    # Write CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['game_url', 'pitcher', 'line', 'odds'])
        writer.writerows(all_rows)

    print(f'Data written to {output_file}')
    context.close()
