

from playwright.async_api import async_playwright
import asyncio

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_user_data",
            headless=False
        )
        page = await context.new_page()
        await page.goto('https://www.ballparkpal.com/Game-Simulations.php')
        await page.wait_for_timeout(1000)  # allow JS to load
        content = await page.content()
        with open('data/game_simulations.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved page HTML to data/game_simulations.html")
        
        # Check expiration date of cookies
        # cookies = await context.cookies()
        # for c in cookies:
        #     print(f"{c['name']} — expires at {c['expires']} (Unix epoch seconds)")

        # # Keep browser open until you close it
        # input("Press Enter to close the browser...")
        # await context.close()
        
asyncio.run(main())
