from playwright.async_api import async_playwright
import asyncio
import os

os.makedirs("data", exist_ok=True)
user_data_dir = "playwright_user_data"

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )
        page = await context.new_page()
        await page.goto('https://www.ballparkpal.com/Game-Simulations.php')
        await page.wait_for_timeout(1000)  
        # content = await page.content()
        # file_path = os.path.join('data', 'game_simulations.html')
        # with open(file_path, 'w', encoding='utf-8') as f:
        #     f.write(content)
        # print(f"Saved page HTML to {file_path}")
        input("Press Enter to close the browser...")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
