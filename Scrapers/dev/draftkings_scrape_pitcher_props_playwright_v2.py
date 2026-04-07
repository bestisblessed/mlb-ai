from __future__ import annotations
import asyncio
import csv
import datetime as _dt
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

TODAY = _dt.datetime.now().strftime("%Y-%m-%d")
DATA_DIR = Path(f"data/{TODAY}")
LINKS_CSV = DATA_DIR / "dk_game_links.csv"
OUT_CSV = DATA_DIR / f"dk_pitcher_props_{TODAY}.csv"
LADDER_COLS = [f"{n}+" for n in range(3, 11)]
_CLICK_DEBOUNCE = 0.08


def _get_playwright():
    try:
        from playwright.async_api import async_playwright, Locator, Page  # type: ignore
    except ModuleNotFoundError:
        print("\n✖ playwright not installed. Run:\n    pip install playwright\n    playwright install chromium", file=sys.stderr)
        sys.exit(1)
    return async_playwright, Locator, Page


async_playwright, Locator, Page = _get_playwright()


async def _arrow_enabled(arrow: Locator) -> bool:
    return bool(
        await arrow.count()
        and await arrow.is_visible()
        and not (
            await arrow.get_attribute("disabled")
            or await arrow.get_attribute("aria-disabled")
        )
    )


async def _ladder_for_row(row: Locator) -> Dict[str, Optional[str]]:
    left = row.locator(".cb-selection-picker__left-arrow")
    right = row.locator(".cb-selection-picker__right-arrow")
    picks = row.locator("button.cb-selection-picker__selection")
    label_sel = ".cb-selection-picker__selection-label"
    odds_sel = ".cb-selection-picker__selection-odds"

    max_attempts = 20
    while await _arrow_enabled(left) and max_attempts > 0:
        await left.click()
        await asyncio.sleep(_CLICK_DEBOUNCE)
        max_attempts -= 1

    prices: Dict[str, str] = {}
    seen = set()

    while True:
        for btn in await picks.all():
            label_node = btn.locator(label_sel).first
            if not await label_node.count():
                continue
            label = (await label_node.inner_text()).strip()
            if label in seen or not re.fullmatch(r"\d\+", label):
                continue
            seen.add(label)
            odds_node = btn.locator(odds_sel).first
            if await odds_node.count():
                prices[label] = (await odds_node.inner_text()).strip()

        if not await _arrow_enabled(right):
            break
        await right.click()
        await asyncio.sleep(_CLICK_DEBOUNCE)

    name_node = row.locator(".cb-player-page-link p.cb-market__label--truncate-strings").first
    pitcher = (await name_node.inner_text()).strip() if await name_node.count() else ""

    record: Dict[str, Optional[str]] = {"pitcher": pitcher}
    for col in LADDER_COLS:
        record[col] = prices.get(col)
    return record


async def _scrape_game(page: Page, base_url: str) -> List[Dict[str, Optional[str]]]:
    url = base_url if "subcategory=pitcher-props" in base_url else f"{base_url}?category=odds&subcategory=pitcher-props"
    await page.goto(url, timeout=0)
    await page.wait_for_selector("h2:has-text('Strikeouts Thrown')", timeout=15000)

    results: List[Dict[str, Optional[str]]] = []
    rows = page.locator("[data-testid='market-template']")
    for i in range(await rows.count()):
        ladder = await _ladder_for_row(rows.nth(i))
        ladder["game_url"] = base_url
        results.append(ladder)
    return results


async def _run() -> None:
    if not LINKS_CSV.exists():
        sys.exit("dk_game_links.csv missing – run the URL scraper first.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    urls = [row[0].strip() for row in csv.reader(LINKS_CSV.open()) if row]

    all_rows: List[Dict[str, Optional[str]]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        for url in urls:
            try:
                rows = await _scrape_game(page, url)
                all_rows.extend(rows)
                print(f"{url} ✔ {len(rows)} pitchers scraped")
            except Exception as exc:
                print(f"{url} ✖ {exc}")

        await browser.close()

    if all_rows:
        pd.DataFrame(all_rows).sort_values(["game_url", "pitcher"]).to_csv(
            OUT_CSV, index=False
        )
        print(f"\nSaved {len(all_rows)} rows → {OUT_CSV}")
    else:
        print("No rows collected – selectors may need adjustment.")


if __name__ == "__main__":
    asyncio.run(_run())





#from __future__ import annotations
#import asyncio
#import csv
#import datetime as _dt
#import sys
#import re
#from pathlib import Path
#from typing import Dict, List, Optional
#
#import pandas as pd
#
#TODAY = _dt.datetime.now().strftime("%Y-%m-%d")
#DATA_DIR = Path(f"data/{TODAY}")
#LINKS_CSV = DATA_DIR / "dk_game_links.csv"
#OUT_CSV = DATA_DIR / f"dk_pitcher_props_{TODAY}.csv"
#LADDER_COLS = [f"{n}+" for n in range(3, 11)]
#_CLICK_DEBOUNCE = 0.08
#
#
#def _get_playwright():
#    try:
#        from playwright.async_api import async_playwright, Locator, Page  # type: ignore
#    except ModuleNotFoundError:
#        print("\n✖ playwright not installed. Run:\n    pip install playwright\n    playwright install chromium", file=sys.stderr)
#        sys.exit(1)
#    return async_playwright, Locator, Page
#
#
#async_playwright, Locator, Page = _get_playwright()
#
#
#async def _arrow_enabled(arrow: Locator) -> bool:
#    return bool(
#        await arrow.count()
#        and await arrow.is_visible()
#        and not (
#            await arrow.get_attribute("disabled")
#            or await arrow.get_attribute("aria-disabled")
#        )
#    )
#
#
#async def _ladder_for_row(row: Locator) -> Dict[str, Optional[str]]:
#    left = row.locator(".cb-selection-picker__left-arrow")
#    right = row.locator(".cb-selection-picker__right-arrow")
#    picks = row.locator("button.cb-selection-picker__selection")
#    label_sel = ".cb-selection-picker__selection-label"
#    odds_sel = ".cb-selection-picker__selection-odds"
#
#    max_attempts = 20
#    while await _arrow_enabled(left) and max_attempts > 0:
#        await left.click()
#        await asyncio.sleep(_CLICK_DEBOUNCE)
#        max_attempts -= 1
#
#    prices: Dict[str, str] = {}
#    seen = set()
#
#    while True:
#        for btn in await picks.all():
#            label_node = btn.locator(label_sel).first
#            if not await label_node.count():
#                continue
#            label = (await label_node.inner_text()).strip()
#            if label in seen or not re.fullmatch(r"\d\+", label):
#                continue
#            seen.add(label)
#            odds_node = btn.locator(odds_sel).first
#            if await odds_node.count():
#                prices[label] = (await odds_node.inner_text()).strip()
#
#        if not await _arrow_enabled(right):
#            break
#        await right.click()
#        await asyncio.sleep(_CLICK_DEBOUNCE)
#
#    name_node = row.locator(".cb-player-page-link p.cb-market__label--truncate-strings").first
#    pitcher = (await name_node.inner_text()).strip() if await name_node.count() else ""
#
#    record: Dict[str, Optional[str]] = {"pitcher": pitcher}
#    for col in LADDER_COLS:
#        record[col] = prices.get(col)
#    return record
#
#
#async def _scrape_game(page: Page, base_url: str) -> List[Dict[str, Optional[str]]]:
#    url = base_url if "subcategory=pitcher-props" in base_url else f"{base_url}?category=odds&subcategory=pitcher-props"
#    await page.goto(url, timeout=0)
#    await page.wait_for_selector("h2:has-text('Strikeouts Thrown')", timeout=15000)
#
#    results: List[Dict[str, Optional[str]]] = []
#
#    # Only select the first section below the "Strikeouts Thrown" header
#    h2 = page.locator("h2:has-text('Strikeouts Thrown')").first
#    container = h2.locator("xpath=..")  # get the parent container
#    rows = container.locator("[data-testid='market-template']")
#
#    for i in range(await rows.count()):
#        ladder = await _ladder_for_row(rows.nth(i))
#        ladder["game_url"] = base_url
#        results.append(ladder)
#    return results
#
#
#async def _run() -> None:
#    if not LINKS_CSV.exists():
#        sys.exit("dk_game_links.csv missing – run the URL scraper first.")
#
#    DATA_DIR.mkdir(parents=True, exist_ok=True)
#    urls = [row[0].strip() for row in csv.reader(LINKS_CSV.open()) if row]
#
#    all_rows: List[Dict[str, Optional[str]]] = []
#    async with async_playwright() as p:
#        browser = await p.chromium.launch(headless=False)
#        context = await browser.new_context()
#        page = await context.new_page()
#
#        for url in urls:
#            try:
#                rows = await _scrape_game(page, url)
#                all_rows.extend(rows)
#                print(f"{url} ✔ {len(rows)} pitchers scraped")
#            except Exception as exc:
#                print(f"{url} ✖ {exc}")
#
#        await browser.close()
#
#    if all_rows:
#        pd.DataFrame(all_rows).sort_values(["game_url", "pitcher"]).to_csv(
#            OUT_CSV, index=False
#        )
#        print(f"\nSaved {len(all_rows)} rows → {OUT_CSV}")
#    else:
#        print("No rows collected – selectors may need adjustment.")
#
#
#if __name__ == "__main__":
#    asyncio.run(_run())
