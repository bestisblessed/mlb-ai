import pandas as pd
from playwright.async_api import async_playwright
import asyncio
import os
from datetime import datetime
from ballparkpal_auth import USER_AGENT, assert_authenticated_html

HEADLESS = os.getenv("BALLPARKPAL_HEADLESS", "0") == "1"

#####################
### DOWNLOAD HTML ###
#####################
async def download_html(url, filepath):
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_user_data",
            headless=HEADLESS,
            user_agent=USER_AGENT
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        initial_content = await page.content()
        assert_authenticated_html(page.url, initial_content, "Starting Pitchers")
        await page.wait_for_selector("table", timeout=5000)
        
        # Click on the Strikeouts tab
        strikeouts_button = await page.query_selector("button.dt-button:has(span:text-is('Strikeouts'))")
        if strikeouts_button:
            await strikeouts_button.click()
            await page.wait_for_timeout(1000)
        else:
            print("Strikeouts button not found")
        
        content = await page.content()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        await ctx.close()         

today = datetime.now().strftime('%Y-%m-%d')
output_dir = f"data/{today}"
os.makedirs(output_dir, exist_ok=True)
html_filepath = os.path.join(output_dir, "Pitchers.html")
pitchers_url = "https://www.ballparkpal.com/Starting-Pitchers.php"
async def main():
    await download_html(pitchers_url, html_filepath)
    print(f"Downloaded HTML to {html_filepath}")
asyncio.run(main())



#####################################
### PARSE AND CALCULATE FROM HTML ###
#####################################
today = datetime.now().strftime('%Y-%m-%d')
output_dir = f"data/{today}"
df_list = pd.read_html(f"{output_dir}/Pitchers.html")
df = next((t for t in df_list if {"Pitcher","0","12+"}.issubset(t.columns)), None)
if df is None:
    df = next((t for t in df_list if {"Pitcher","0","10+"}.issubset(t.columns)), None)
if df is None:
    print([list(t.columns) for t in df_list])
    raise RuntimeError("No matching table found")
df = df.copy()
    
# Get Ladder Probs
if "12+" in df.columns:
    prob_cols = [str(i) for i in range(12)] + ["12+"]
else:
    prob_cols = [str(i) for i in range(10)] + ["10+"]
for k in range(2, 11):
    df[f"{k}plus"] = df[[c for c in prob_cols if int(c.rstrip('+')) >= k]].sum(axis=1)
    
# Calculate Money Line (no-vig)
for k in range(2, 11):
    # Calculate no-vig odds, guard against division by zero for p=0 or p=1
    df[f"{k}plus_odds"] = df[f"{k}plus"].apply(
        lambda p: None if p in (0, 1) else (-round(p/(1-p)*100) if p >= 0.5 else round((1-p)/p*100))
    )
    
# View/Save
cols = ["Pitcher"] + [f"{k}plus_odds" for k in range(2, 11)]
rename_dict = {f"{k}plus_odds": f"{k}K" for k in range(2, 11)}
df_out = df[cols].rename(columns=rename_dict)
print(df_out)
df_out.sort_values(by="Pitcher").to_csv(f"{output_dir}/pitcher_alt_strikeouts.csv", index=False)
