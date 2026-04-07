import os
from datetime import datetime
import requests
import re

today = datetime.now().strftime("%Y-%m-%d")
os.makedirs(f'data/{today}', exist_ok=True)

url = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
headers = {"User-Agent": "Mozilla/5.0"}
data = requests.get(url, headers=headers).json()

# If json already scraped:
#with open("fanduel_mlb_raw.json", "r", encoding="utf-8") as f:
#    data = json.load(f)

mlb_event_ids = []
cards = data['layout']['cards']
for v in cards.values():
    if v.get('title', '').lower() == 'mlb odds':
        for cid in v['coupons']:
            coupon = data['layout']['coupons'].get(str(cid['id'] if isinstance(cid, dict) else cid))
            if coupon and 'display' in coupon and coupon['display']:
                for row in coupon['display'][0].get('rows', []):
                    mlb_event_ids.append(row['eventId'])

urls = []
events = data['attachments'].get('events', {})
for eid in mlb_event_ids:
    event = events.get(str(eid))
    if event and 'name' in event:
        matchup = re.sub(r'\s*\([^)]*\)', '', event['name'])
        slug = matchup.lower().replace('.', '').replace(',', '').replace("'", '')
        slug = slug.replace(' & ', '-').replace(' @ ', '-@-').replace(' ', '-').replace('--', '-')
        urls.append(f"https://sportsbook.fanduel.com/baseball/mlb/{slug}-{eid}?tab=pitcher-props")

out_path = f"data/{today}/fanduel_game_links.csv"
with open(out_path, "w") as f:
    for url in sorted(urls):
        f.write(url + "\n")

for url in sorted(urls):
    print(url)
print(f"\nSaved game links to {out_path}")

