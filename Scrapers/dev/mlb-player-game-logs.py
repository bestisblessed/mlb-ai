# # from bs4 import BeautifulSoup
# # import pandas as pd
# # import requests
# # import glob
# # from lxml import html
# # from time import sleep
# # from random import uniform
# # import aiohttp
# # import asyncio
# # import nest_asyncio
# # from pathlib import Path
# # import os
# # from tqdm import tqdm

# # os.makedirs("data/mlb", exist_ok=True)
# # os.makedirs("data/mlb/depth-charts", exist_ok=True)

# # ### All MLB Team URLs ###
# # url = "https://www.mlb.com/team/roster/depth-chart"
# # response = requests.get(url)
# # response.raise_for_status()  
# # soup = BeautifulSoup(response.text, "html.parser")
# # depth_chart_data = []
# # for a in soup.find_all("a", href=True):
# #     href = a["href"]
# #     if "/roster/depth-chart" in href:
# #         img = a.find("img")
# #         if img and "alt" in img.attrs:
# #             team_name = img["alt"].replace(" logo", "").strip()
# #             full_url = f"https://www.mlb.com{href}" if href.startswith("/") else href
# #             depth_chart_data.append((team_name, full_url))
# # depth_chart_df = pd.DataFrame(depth_chart_data, columns=["Team Name", "Depth Chart URL"])
# # depth_chart_df.to_csv("data/mlb/all_teams.csv", index=False)
# # print("Saved to all_teams.csv")
# # print(depth_chart_df.head())


# # ### All Teams Depth Charts ###
# # teams_df = pd.read_csv('data/mlb/all_teams.csv')
# # for index, row in teams_df.iterrows():
# #     team_name = row['Team Name']
# #     depth_chart_url = row['Depth Chart URL']
# #     response = requests.get(depth_chart_url)
# #     soup = BeautifulSoup(response.content, "html.parser")
# #     player_tds = soup.select("td.info")
# #     players_data = []
# #     for td in player_tds:
# #         name_tag = td.find("a")
# #         jersey_tag = td.find("span", class_="jersey")
# #         status_tag = td.find("span", class_="status-il")
# #         mobile_info = td.find("div", class_="mobile-info")
# #         name = name_tag.get_text(strip=True) if name_tag else ""
# #         player_url = "https://www.mlb.com" + name_tag["href"] if name_tag and name_tag.has_attr("href") else ""
# #         jersey = jersey_tag.get_text(strip=True) if jersey_tag else ""
# #         status = status_tag.get_text(strip=True) if status_tag else ""
# #         bt = mobile_info.find("span", class_="mobile-info__bat-throw").get_text(strip=True).replace("B/T: ", "") if mobile_info else ""
# #         height = mobile_info.find("span", class_="mobile-info__height").get_text(strip=True).replace("Ht: ", "") if mobile_info else ""
# #         weight = mobile_info.find("span", class_="mobile-info__weight").get_text(strip=True).replace("Wt: ", "") if mobile_info else ""
# #         dob = mobile_info.find("span", class_="mobile-info__birthday").get_text(strip=True).replace("DOB: ", "") if mobile_info else ""
# #         players_data.append({
# #             "Name": name,
# #             "Player URL": player_url,
# #             "Jersey Number": jersey,
# #             "Status": status,
# #             "B/T": bt,
# #             "Height": height,
# #             "Weight": weight,
# #             "DOB": dob
# #         })
# #     players_df = pd.DataFrame(players_data)
# #     csv_path = f"data/mlb/depth-charts/{team_name.replace(' ', '_').lower()}_depth_chart.csv"
# #     players_df.to_csv(csv_path, index=False)
# #     print(f"Saved data for {team_name} to {csv_path}")
    
    
# # ### Combine all depth chart CSVs into one file and add 'Player ID' column ###
# # all_players = []
# # for team_file in glob.glob("data/mlb/depth-charts/*_depth_chart.csv"):
# #     df = pd.read_csv(team_file)
# #     team_name = team_file.split('/')[-1].replace('_depth_chart.csv','').replace('_',' ').title()
# #     df['Team'] = team_name
# #     df['Player ID'] = df['Player URL'].apply(lambda x: x.split('/')[-1])  # Extracting player ID from URL
# #     all_players.append(df)
# # all_players_df = pd.concat(all_players, ignore_index=True).drop(['Jersey Number', 'Status', 'DOB'], axis=1)
# # all_players_df.to_csv("data/mlb/all_players.csv", index=False)
# # print(f"Combined {len(all_players)} team rosters into all_players.csv")
# # print(f"Total players: {len(all_players_df)}\n")
# # print(all_players_df.head())


# # ### Scrape Player Positions ###
# # # nest_asyncio.apply()
# # # players_df = pd.read_csv("data/mlb/all_players.csv")
# # # if "Position" not in players_df.columns:
# # #     players_df["Position"] = ""
# # # # if "Raw URL" not in players_df.columns:
# # # #     players_df["Raw URL"] = ""
# # # async def main():
# # #     async with aiohttp.ClientSession() as session:
# # #         semaphore = asyncio.Semaphore(10) 
# # #         tasks = []
# # #         for i, row in players_df.iterrows():
# # #             if pd.notna(row.get("Position")) and row["Position"].strip() != "":
# # #                 print(f"Skipping {row['Player URL']} - already has position: {row['Position']}")
# # #                 continue
# # #             # if pd.notna(row.get("Position")) and row["Position"].strip() != "" and pd.notna(row.get("Raw URL")) and row["Raw URL"].strip() != "":
# # #             #     print(f"Skipping {row['Player URL']} - already has position: {row['Position']} and Raw URL")
# # #             #     continue
# # #             async def process_player(url, idx):
# # #                 async with semaphore:  
# # #                     print(f"Scraping {url}...")
# # #                     try:
# # #                         # async with session.get(url, timeout=10) as response:
# # #                         async with session.get(url, timeout=10, allow_redirects=True) as response:
# # #                             # Save the final URL after any redirects
# # #                             # final_url = str(response.url)
# # #                             # players_df.at[idx, "Raw URL"] = final_url
                            
# # #                             content = await response.text()
# # #                             tree = html.fromstring(content)
# # #                             position = tree.xpath('/html/body/main/section/header/div/div[1]/ul/li[1]/text()')
# # #                             players_df.at[idx, "Position"] = position[0].strip() if position else ""
                            
# # #                             print(f"  Position: {players_df.at[idx, 'Position']}")
# # #                             # print(f"  Raw URL: {final_url}")
                            
# # #                     except Exception as e:
# # #                         print(f"Error for {url}: {str(e)}")
# # #                     if (idx + 1) % 100 == 0:  
# # #                         players_df.to_csv("data/mlb/all_players.csv", index=False)  
# # #                         print(f"Checkpoint saved at row {idx+1}")
# # #                     await asyncio.sleep(uniform(1.5, 3.0))
# # #             tasks.append(process_player(row["Player URL"], i))
# # #         if not tasks:
# # #             print("No players need position information. All done!")
# # #             return
# # #         print(f"Need to scrape {len(tasks)} players for position data")
# # #         # print(f"Need to scrape {len(tasks)} players for position data and/or Raw URL")
# # #         await asyncio.gather(*tasks)
# # # asyncio.run(main())
# # # players_df.to_csv("data/mlb/all_players.csv", index=False)
# # # print("Saved to all_players.csv")
# # ### Scrape Player Positions ###

# # os.makedirs("data/mlb/raw", exist_ok=True)
# # nest_asyncio.apply()
# # players_df = pd.read_csv("data/mlb/all_players.csv")
# # if "Position" not in players_df.columns:
# #     players_df["Position"] = ""
# # async def main():
# #     async with aiohttp.ClientSession() as session:
# #         semaphore = asyncio.Semaphore(1)
# #         tasks = []
# #         for i, row in players_df.iterrows():
# #             if pd.notna(row.get("Position")) and row["Position"].strip() != "":
# #                 print(f"Skipping {row['Player URL']} - already has position: {row['Position']}")
# #                 continue
# #             async def process_player(url, idx):
# #                 async with semaphore:  
# #                     print(f"Scraping {url}...")
# #                     try:
# #                         async with session.get(url, timeout=10) as response:
# #                             content = await response.text()
                            
# #                             # Save raw HTML using final URL after redirects
# #                             final_url = str(response.url)
# #                             safe_filename = final_url.replace(':', '_').replace('/', '_')
# #                             with open(f"data/mlb/raw-players/{safe_filename}.html", "w", encoding="utf-8") as f:
# #                                 f.write(content)
                            
# #                             tree = html.fromstring(content)
# #                             position = tree.xpath('/html/body/main/section/header/div/div[1]/ul/li[1]/text()')
# #                             players_df.at[idx, "Position"] = position[0].strip() if position else ""
# #                     except Exception as e:
# #                         print(f"Error for {url}: {e}")
# #                     if (idx + 1) % 10 == 0:  
# #                         players_df.to_csv("data/mlb/all_players.csv", index=False)  
# #                         print(f"Checkpoint saved at row {idx+1}")
# #                     await asyncio.sleep(uniform(1.5, 3.0))
# #             tasks.append(process_player(row["Player URL"], i))
# #         if not tasks:
# #             print("No players need position information. All done!")
# #             return
# #         print(f"Need to scrape {len(tasks)} players for position data")
# #         await asyncio.gather(*tasks)
# # asyncio.run(main())
# # players_df.to_csv("data/mlb/all_players.csv", index=False)
# # print("Saved to all_players.csv")


# import os, asyncio, random
# import pandas as pd
# from playwright.async_api import async_playwright
# from bs4 import BeautifulSoup

# # prep
# os.makedirs("data/mlb/raw-players", exist_ok=True)
# df = pd.read_csv("data/mlb/all_players.csv")
# if "Position" not in df.columns:
#     df["Position"] = ""

# async def main():
#     async with async_playwright() as p:
#         browser = await p.firefox.launch(headless=True)
#         page = await browser.new_page()
#         page.set_default_timeout(30000)

#         for i, row in df.iterrows():
#             url = row["Player URL"]
#             if pd.notna(row["Position"]) and row["Position"].strip():
#                 print(f"Skipping {url} (already has position)")
#                 continue

#             print(f"Scraping {url}...")
#             try:
#                 await page.goto(url, wait_until="domcontentloaded")
#                 html = await page.content()

#                 # save raw HTML
#                 safe = url.replace("://", "_").replace("/", "_")
#                 with open(f"data/mlb/raw-players/{safe}.html", "w", encoding="utf-8") as f:
#                     f.write(html)

#                 # parse position
#                 soup = BeautifulSoup(html, "html.parser")
#                 # this maps to XPath /html/body/main/section/header/div/div[1]/ul/li[1]
#                 header = soup.select_one("main section header div div ul")
#                 pos = header.select_one("li").get_text(strip=True) if header else ""
#                 df.at[i, "Position"] = pos

#             except Exception as e:
#                 print(f"Error for {url}: {e}")

#             # checkpoint every 100
#             if (i + 1) % 100 == 0:
#                 df.to_csv("data/mlb/all_players.csv", index=False)
#                 print(f"Checkpoint saved at row {i+1}")

#             await asyncio.sleep(random.uniform(1, 3))

#         await browser.close()

# asyncio.run(main())

# # final write
# df.to_csv("data/mlb/all_players.csv", index=False)
# print("All done, positions saved.")

import os, asyncio, random, pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# prep
os.makedirs("data/mlb/raw-players", exist_ok=True)
df = pd.read_csv("data/mlb/all_players.csv")
df["Position"] = df.get("Position", "")

async def fetch(browser, url, idx, sem):
    async with sem:
        print(f"Scraping {url}…")
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            # save raw
            safe = url.replace("://", "_").replace("/", "_")
            open(f"data/mlb/raw-players/{safe}.html","w",encoding="utf-8").write(html)
            # parse position
            soup = BeautifulSoup(html, "html.parser")
            li = soup.select_one("main section header div div ul li")
            df.at[idx, "Position"] = li.get_text(strip=True) if li else ""
        except Exception as e:
            print(f"Error {url}: {e}")
        await page.close()
        # checkpoint
        if (idx + 1) % 20 == 0:
            df.to_csv("data/mlb/all_players.csv", index=False)
            print(f"Checkpoint @ row {idx+1}")
        await asyncio.sleep(random.uniform(1, 2))

async def main():
    sem = asyncio.Semaphore(3)
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        tasks = [
            fetch(browser, row["Player URL"], i, sem)
            for i, row in df.iterrows()
            if not str(row["Position"]).strip()
        ]
        print(f"Queueing {len(tasks)} pages (10 at a time)…")
        await asyncio.gather(*tasks)
        await browser.close()

    df.to_csv("data/mlb/all_players.csv", index=False)
    print("Done -> all_players.csv updated.")

if __name__ == "__main__":
    asyncio.run(main())