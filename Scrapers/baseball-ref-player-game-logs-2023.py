import asyncio
import csv
import random
import time
from pathlib import Path
from playwright.async_api import async_playwright

class GameLogDownloader:
    def __init__(self, end_year: int = 2023, years_count: int = 1):
        # Define the range of years to download (only the 2023 season)
        self.years = [2023]
        # Source CSV containing player IDs
        self.player_info_file = Path("data/baseball-ref/player-info.csv")
        # Output directory for raw game log HTML
        self.raw_gl_dir = Path("data/baseball-ref/raw-players-game-logs/")
        self.raw_gl_dir.mkdir(parents=True, exist_ok=True)

    def get_active_players(self):
        """
        Load player-info.csv and return list of (player_id, name) for each entry.
        """
        active = []
        if not self.player_info_file.exists():
            print(f"Error: player info file not found at {self.player_info_file}")
            return active

        with open(self.player_info_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get('player_id') or row.get('playerId')
                name = row.get('name', '').strip()
                if pid:
                    active.append((pid, name))
        return active

    def make_gamelog_url(self, player_id: str, year: int) -> str:
        """
        Construct the batting game log URL for a player in a given year.
        """
        return (
            f"https://www.baseball-reference.com/players/gl.fcgi"
            f"?id={player_id}&t=b&year={year}"
        )

    async def download_all(self, test_limit: int = None):
        """
        Download game log pages for each player-year combination. If `test_limit`
        is set, only process that many players (still downloading all years for each).
        """
        players = self.get_active_players()
        if test_limit:
            players = players[:test_limit]

        # Build a list of (player_id, name, year) tasks
        tasks = [(pid, name, year) for pid, name in players for year in self.years]
        total = len(tasks)

        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) "
                    "Gecko/20100101 Firefox/124.0"
                )
            )
            page = await context.new_page()
            page.set_default_timeout(15000)

            for idx, (pid, name, year) in enumerate(tasks, start=1):
                url = self.make_gamelog_url(pid, year)
                out_file = self.raw_gl_dir / f"{pid}_{year}.html"
                if out_file.exists():
                    print(f"[{idx}/{total}] Skipping {pid} ({year}) — already downloaded")
                    continue

                try:
                    print(f"[{idx}/{total}] Downloading {name} ({pid}) game log for {year}...")
                    await page.goto(url, wait_until='domcontentloaded')
                    await asyncio.sleep(1)
                    content = await page.content()
                    out_file.write_text(content, encoding='utf-8')
                    print(f"    Saved to {out_file}")
                except Exception as e:
                    print(f"    Error ({pid}, {year}): {e}")

                # Random short delay between requests
                await asyncio.sleep(random.uniform(2, 3))

            await browser.close()

async def main(test: bool = False):
    # `test=True` will limit to the first 3 players
    downloader = GameLogDownloader(end_year=2023, years_count=1)
    await downloader.download_all(test_limit=3 if test else None)

if __name__ == '__main__':
    import sys
    test_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'test'
    asyncio.run(main(test=test_mode))
