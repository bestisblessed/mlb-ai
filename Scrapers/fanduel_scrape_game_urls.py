import requests
import json
import pandas as pd
import re

url = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
headers = {
    "User-Agent": "Mozilla/5.0"
}
response = requests.get(url, headers=headers)
data = response.json()
with open("fanduel_mlb_raw.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# If json already scraped:
#with open("fanduel_mlb_raw.json", "r", encoding="utf-8") as f:
#    data = json.load(f)
    
print("Top-level keys:", list(data.keys()))
if 'modules' in data:
    print("modules type:", type(data['modules']))
    if isinstance(data['modules'], list) and data['modules']:
        print("First module keys:", list(data['modules'][0].keys()))
        if 'display' in data['modules'][0]:
            print("Sample display item:", data['modules'][0]['display'][0] if data['modules'][0]['display'] else 'EMPTY')
if 'layout' in data:
    print("layout keys:", list(data['layout'].keys()))
    if 'links' in data['layout']:
        print("Sample link item:", next(iter(data['layout']['links'].values())))
    if 'cards' in data['layout']:
        cards = data['layout']['cards']
        print("cards type:", type(cards))
        if isinstance(cards, dict) and cards:
            for i, (k, v) in enumerate(cards.items()):
                print(f"Sample card item {i}: key={k}, value={v}")
                # Try to follow coupon IDs
                if 'coupons' in v and isinstance(v['coupons'], list):
                    for cid in v['coupons'][:2]:
                        cid_val = cid['id'] if isinstance(cid, dict) and 'id' in cid else cid
                        coupon = data['layout']['coupons'].get(str(cid_val)) or data['layout']['coupons'].get(cid_val)
                        if coupon:
                            print(f"  Coupon {cid_val} sample: keys={list(coupon.keys())}")
                            if 'display' in coupon and coupon['display']:
                                print(f"    Sample display item: {coupon['display'][0]}")
                if i >= 2: break
    if 'coupons' in data['layout']:
        coupons = data['layout']['coupons']
        print("coupons type:", type(coupons))
        if isinstance(coupons, dict) and coupons:
            for i, (k, v) in enumerate(coupons.items()):
                print(f"Sample coupon item {i}: key={k}, value={v}")
                if i >= 2: break
                # For MLB Odds coupon, print rows
                if k == '824' and 'coupons' in v:
                    for cid in v['coupons']:
                        cid_val = cid['id'] if isinstance(cid, dict) and 'id' in cid else cid
                        if str(cid_val) in data['layout']['coupons']:
                            coupon = data['layout']['coupons'][str(cid_val)]
                            if 'display' in coupon and coupon['display']:
                                display = coupon['display'][0]
                                if 'rows' in display:
                                    print(f"All rows in MLB Odds coupon:")
                                    for row in display['rows']:
                                        print(row)
                                    # Try to correlate eventId with layout['links']
                                    first_event_id = display['rows'][0]['eventId']
                                    for link in data['layout']['links'].values():
                                        if link.get('linkIdentifier', {}).get('eventId') == first_event_id:
                                            print(f"Matching link for eventId {first_event_id}: {link}")
                                            break

# Print attachments structure for eventId to matchup mapping
if 'attachments' in data:
    print('attachments keys:', list(data['attachments'].keys()))
    # Print a sample eventId and its value
    for k, v in list(data['attachments'].items())[:2]:
        print(f'attachments sample {k}:', v)

# Extract game URLs from the JSON data
urls = set()
# Find MLB Odds coupon (id 14862) and extract eventIds
mlb_event_ids = []
mlb_coupon = None
cards = data['layout']['cards']
if isinstance(cards, dict):
    for k, v in cards.items():
        if v.get('title', '').lower() == 'mlb odds' and 'coupons' in v:
            for cid in v['coupons']:
                cid_val = cid['id'] if isinstance(cid, dict) and 'id' in cid else cid
                coupon = data['layout']['coupons'].get(str(cid_val))
                if coupon and 'display' in coupon and coupon['display']:
                    display = coupon['display'][0]
                    if 'rows' in display:
                        for row in display['rows']:
                            mlb_event_ids.append(row['eventId'])
# Correlate eventIds with matchup names from layout['links']
eventid_to_name = {}
for link in data['layout']['links'].values():
    eid = link.get('linkIdentifier', {}).get('eventId')
    name = link.get('linkIdentifier', {}).get('options', {}).get('title')
    if eid and name and name.lower() != 'more wagers':
        eventid_to_name[eid] = name
# Build URLs
for eid in mlb_event_ids:
    matchup = eventid_to_name.get(eid)
    if matchup:
        slug = matchup.lower().replace('.', '').replace(',', '').replace("'", '')
        slug = slug.replace(' & ', '-').replace(' at ', '-@-')
        slug = slug.replace(' ', '-').replace('--', '-')
        url = f"https://sportsbook.fanduel.com/baseball/mlb/{slug}-{eid}?tab=pitcher-props"
        urls.add(url)
df = pd.DataFrame(sorted(urls), columns=["url"])
df.to_csv("fanduel_pitcher_props_urls.csv", index=False)
print(df)

# Print a sample from attachments['events'] for the first eventId in MLB Odds coupon rows
if mlb_event_ids and 'events' in data['attachments']:
    first_eid = str(mlb_event_ids[0])
    if first_eid in data['attachments']['events']:
        print(f"Sample event for eventId {first_eid}: {data['attachments']['events'][first_eid]}")

# Extract pitcher props URLs using event names from attachments['events']
urls = set()
events = data['attachments'].get('events', {})
for eid in mlb_event_ids:
    event = events.get(str(eid))
    if event and 'name' in event:
        matchup = event['name']
        # Remove pitcher names in parentheses for URL slug
        matchup_slug = re.sub(r'\s*\([^)]*\)', '', matchup)
        slug = matchup_slug.lower().replace('.', '').replace(',', '').replace("'", '')
        slug = slug.replace(' & ', '-').replace(' @ ', '-@-')
        slug = slug.replace(' ', '-').replace('--', '-')
        url = f"https://sportsbook.fanduel.com/baseball/mlb/{slug}-{eid}?tab=pitcher-props"
        urls.add(url)
df = pd.DataFrame(sorted(urls), columns=["url"])
df.to_csv("fanduel_pitcher_props_urls.csv", index=False)
print(df)

#
#from playwright.sync_api import sync_playwright
#from bs4 import BeautifulSoup
#import pandas as pd
#from time import sleep
#
#with sync_playwright() as p:
#    browser = p.chromium.launch()
#    page = browser.new_page()
#    page.goto("https://sportsbook.fanduel.com/navigation/mlb")
#    #page.wait_for_selector('a[href^="/baseball/mlb/"]', timeout=10000)
#    sleep(5)
#    html = page.content()
#    browser.close()
#
#soup = BeautifulSoup(html, 'html.parser')
## Debug: print all anchor tags with '/baseball/mlb/' in href
#for a in soup.find_all('a', href=True):
#    if '/baseball/mlb/' in a['href']:
#        print('DEBUG:', a.get_text(strip=True), a['href'])
#
#game_links = []
#for a in soup.find_all('a', href=True):
#    href = a['href']
#    if href.startswith('/baseball/mlb/'):
#        name = a.get_text(strip=True)
#        url = f"https://sportsbook.fanduel.com{href}"
#        game_links.append({'name': name, 'url': url})
#
#df = pd.DataFrame(game_links)
#print(df)

