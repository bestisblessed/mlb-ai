import os
import json
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import pandas as pd 

today = datetime.now().strftime("%Y-%m-%d")
folder = f"data/{today}"
os.makedirs(folder, exist_ok=True)
links_file = f"{folder}/bovada_game_links.csv"
with open(links_file) as f:
    urls = [line.strip() for line in f if line.strip()]
print(f"Loaded {len(urls)} game URLs from {links_file}")
combined_csv_file = f"{folder}/bovada_all_pitcher_props_{today}.csv"
all_pitchers_data_list = [] 
with sync_playwright() as p:
    #browser = p.chromium.launch(headless=True)
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    pitcher_count = 0
    line_count = 0 
    for url in urls:
        game_id = url.split('/')[-1]
        print(f"\nProcessing: {url}")
        try:
            page.goto(url, timeout=60000)
            time.sleep(1) 
            print("Looking for Pitcher Props tab...")
            tab_found = False
            try:
                tabs = page.query_selector_all("span.sp-display-group-menu__list__item__description")
                for tab in tabs:
                    if tab.inner_text().strip() == "Pitcher Props":
                        print("Found Pitcher Props tab")
                        tab.click()
                        tab_found = True
                        break
                if not tab_found:
                    print("Tab not found by exact match, trying contains search")
                    pitcher_tab_elements = page.query_selector_all("span:has-text('Pitcher Props')")
                    for pt_tab in pitcher_tab_elements:
                        if pt_tab.is_visible() and pt_tab.inner_text().strip() == "Pitcher Props":
                            pt_tab.click()
                            tab_found = True
                            print("Found and clicked Pitcher Props tab via contains search.")
                            break
                    if not tab_found and pitcher_tab_elements: 
                        print("Trying to click the first 'Pitcher Props' tab found by contains search as a fallback.")
                        pitcher_tab_elements[0].click()
                        tab_found = True
            except Exception as e:
                print(f"Error finding or clicking tab: {e}")
            if not tab_found:
                print("Could not find or click Pitcher Props tab, skipping this game.")
                continue
            print("Waiting for content to load after tab click...")
            time.sleep(3) 
            content = page.content()
            if "Alternate Strikeouts" in content:
                print("Found 'Alternate Strikeouts' in page content.")
                sections = re.findall(r'Alternate Strikeouts - ([^(]+) \(([^)]+)\).*?<ul[^>]*class="outright-market market-type two-columns">(.*?)</ul>', content, re.DOTALL)
                if not sections: 
                    print("Primary section regex (with ul class) found no pitchers. Trying broader pitcher section search...")
                    sections = re.findall(r'Alternate Strikeouts - ([^(]+) \(([^)]+)\)(.*?)(?=(?:Alternate Strikeouts - |Market Groups))', content, re.DOTALL)
                for pitcher_name_raw, team_raw, section_html_content in sections:
                    pitcher_name = pitcher_name_raw.strip()
                    team = team_raw.strip()
                    print(f"Found pitcher: {pitcher_name} ({team})")
                    current_pitcher_csv_row = {
                        "game_url": url,
                        "pitcher": pitcher_name,
                        "team": team
                    }
                    lines_collected_for_this_pitcher = 0
                    primary_lines = re.findall(r'<span class="outcomes">(\d+\+\s*Strikeouts)</span>.*?<span class="bet-price">\s*([+-]\d+)\s*</span>', section_html_content, re.DOTALL)
                    if primary_lines:
                        print(f"  Lines from primary regex for {pitcher_name}:")
                        for line_str, odds_str in primary_lines:
                            line_key = line_str.strip()
                            odds_value = odds_str.strip()
                            current_pitcher_csv_row[line_key] = odds_value
                            print(f"    {line_key}: {odds_value}")
                            lines_collected_for_this_pitcher += 1
                    if not primary_lines:
                        print(f"  Primary regex found no lines in identified section for {pitcher_name}. Trying fallback pattern on section.")
                        alt_pattern = r'(\d+\+\s*Strikeouts)[^<>]*?</span>[^<>]*?<span[^<>]*?>([+-]\d+)'
                        fallback_lines_in_section = re.findall(alt_pattern, section_html_content)
                        if fallback_lines_in_section:
                            print(f"  Lines from fallback regex (on section) for {pitcher_name}:")
                            for line_str, odds_str in fallback_lines_in_section:
                                line_key = line_str.strip()
                                odds_value = odds_str.strip()
                                current_pitcher_csv_row[line_key] = odds_value
                                print(f"    {line_key}: {odds_value}")
                                lines_collected_for_this_pitcher += 1
                        else:
                             print(f"  Fallback regex also found no lines for {pitcher_name} in their section content.")
                    if lines_collected_for_this_pitcher > 0:
                        all_pitchers_data_list.append(current_pitcher_csv_row)
                        pitcher_count += 1 
                        line_count += lines_collected_for_this_pitcher 
                    else:
                        print(f"  No lines ultimately recorded for {pitcher_name} ({team}).")
            else:
                print("No Alternate Strikeouts section found for this game.")
            time.sleep(1) 
        except Exception as e:
            print(f"Error processing {url}: {e}")
    browser.close()
if all_pitchers_data_list:
    df = pd.DataFrame(all_pitchers_data_list)
    output_columns = ['game_url', 'pitcher', 'team']
    for i in range(3, 12): 
        output_columns.append(f"{i}+ Strikeouts")
    df = df.reindex(columns=output_columns)
    df.to_csv(combined_csv_file, index=False)
    print(f"\nSaved all pitcher props to {combined_csv_file}")
else:
    print("\nNo pitcher data collected to save to CSV.")
print(f"\nTotal unique pitchers with lines: {pitcher_count}")
print(f"Total individual strikeout lines recorded: {line_count}")
if pitcher_count > 0:
    print(f"Average lines per pitcher: {line_count/pitcher_count:.1f}")
else:
    print("Average lines per pitcher: 0.0")
