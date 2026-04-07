import asyncio, datetime, os, csv, re
from playwright.async_api import async_playwright

TODAY   = datetime.datetime.now().strftime("%Y-%m-%d")
OUT_DIR = f"data/{TODAY}"
CSV     = f"{OUT_DIR}/dk_game_links.csv"
LEAGUE  = "https://sportsbook.draftkings.com/leagues/baseball/mlb"
ABS     = "https://sportsbook.draftkings.com"
EVENT_RE = re.compile(r"/event/[^/]+/\d+$")        # slug/id

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page    = await browser.new_page()
        await page.goto(LEAGUE, timeout=0)

        # Force lazy-loaded rows to render
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1200)

        links = set()
        for a in await page.query_selector_all("a.event-cell-link"):
            href = await a.get_attribute("href")
            if href and EVENT_RE.search(href):
                links.add(href if href.startswith("http") else ABS + href)

        with open(CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([[u] for u in sorted(links)])

        print(f"Saved {len(links)} DraftKings game URLs → {CSV}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())