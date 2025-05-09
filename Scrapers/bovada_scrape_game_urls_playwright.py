import os
from datetime import datetime
from playwright.sync_api import sync_playwright

today = datetime.now().strftime("%Y-%m-%d")
os.makedirs(f'data/{today}', exist_ok=True)

with sync_playwright() as p:
    #browser = p.chromium.launch(headless=True)
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    try:
        page.goto("https://www.bovada.lv/sports/baseball/mlb", wait_until="networkidle")
        page.wait_for_selector('a[href*="/mlb/"]', timeout=15000, state='attached')
        elems = page.query_selector_all('a[href*="/mlb/"]')
        hrefs = [e.get_attribute('href') for e in elems]
        links = [h for h in hrefs if h and h.split('-')[-1].isdigit()]
        if not links:
            raise Exception("No game links found")
        with open(f'data/{today}/bovada_game_links.csv', 'w') as f:
            f.writelines([f'{url}\n' for url in set(links)])
        print(f"Saved game links to data/{today}/bovada_game_links.csv")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        context.close()
        browser.close()
