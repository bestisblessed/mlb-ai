import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path
import csv
import random
from concurrent.futures import ThreadPoolExecutor
import threading

# A requests.Session wrapper that enforces rate limit and 429 backoff
class RateLimitedSession:
    def __init__(self, headers, max_per_minute=5, max_retries=5, base_delay=3):
        import time, requests, random
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.interval = 60.0 / max_per_minute
        self.last = None
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.time = time
        self.random = random
        self.lock = threading.Lock()

    def get(self, url, **kwargs):
        with self.lock:
            # enforce simple rate limit
            if self.last is not None:
                delta = self.time.time() - self.last
                if delta < self.interval:
                    self.time.sleep(self.interval - delta)
            # retries with exponential backoff
            for attempt in range(self.max_retries):
                resp = self.session.get(url, **kwargs)
                self.last = self.time.time()
                if resp.status_code == 429:
                    wait = self.base_delay * (2 ** attempt) + self.random.random()
                    print(f"429 rate limit, backing off {wait:.1f}s...")
                    self.time.sleep(wait)
                    continue
                return resp
            return resp

class PlayerDataScraper:
    def __init__(self, max_workers=5):
        self.base_url = "https://www.baseball-reference.com/players"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
        }
        self.player_info_dir = Path("data/baseball-ref/player-info")
        self.player_info_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        # use rate-limited session for robust requests
        self.session = RateLimitedSession(self.headers, max_per_minute=30, max_retries=5, base_delay=3)
        # directory to cache raw HTML pages
        self.raw_dir = Path("data/baseball-ref/raw-players")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
    def get_active_players(self) -> list:
        """Read all CSV files and return list of active players."""
        active_players = []
        csv_dir = Path("data/baseball-ref/player-ids")
        
        if not csv_dir.exists():
            print(f"Error: CSV directory not found at {csv_dir}")
            return active_players
            
        csv_files = list(csv_dir.glob("player-ids-*.csv"))
        if not csv_files:
            print(f"Error: No CSV files found in {csv_dir}")
            return active_players
            
        for csv_file in csv_files:
            print(f"Reading {csv_file.name}...")
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Check if years field ends with 2024 or 2025
                        years = row.get('years', '').strip()
                        if years.endswith('2024') or years.endswith('2025'):
                            # Check if player already has info file
                            info_file = self.player_info_dir / f"{row['player_id']}.json"
                            if not info_file.exists():
                                active_players.append({
                                    'id': row['player_id'],
                                    'name': row['name'],
                                    'years': years
                                })
            except Exception as e:
                print(f"Error reading {csv_file.name}: {str(e)}")
                continue
        
        print(f"Total active players needing scraping: {len(active_players)}")
        if active_players:
            print("First few active players to scrape:")
            for player in active_players[:5]:
                print(f"- {player['name']} ({player['id']}) - {player['years']}")
                
        return active_players
        
    def get_player_url(self, player_id: str) -> str:
        """Generate the proper URL for a player's profile page."""
        # Player IDs have format like 'ohtansh01'
        # URL pattern is first letter of last name/full ID.shtml
        first_letter = player_id[0]
        return f"{self.base_url}/{first_letter}/{player_id}.shtml"

    def clean_text(self, text):
        """Clean up text by removing extra whitespace and normalizing spaces."""
        if not text:
            return text
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ').replace('\t', ' ')
        # Fix spacing around punctuation
        text = re.sub(r'\s*([,.:;])\s*', r'\1 ', text)
        # Fix spacing around bullets
        text = re.sub(r'\s*•\s*', ' • ', text)
        # Remove leading/trailing spaces
        return text.strip()

    def format_born_info(self, text):
        """Format born information with proper spacing."""
        if not text:
            return text
        # Add space between date and "in" location
        text = re.sub(r'(\d{4})in', r'\1 in', text)
        # Separate country code from location with comma
        # Common pattern: City, STcc where ST is state and cc is country code
        text = re.sub(r'([A-Z]{2})([a-z]{2})', r'\1, \2', text)
        return text

    def format_team_info(self, text):
        """Format team information with proper spacing."""
        if not text:
            return text
        # Add space between team name and parenthetical status
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        return text

    def scrape_player_info(self, player_id: str, name: str) -> dict:
        """Scrape player info with robust session, caching, and parsing."""
        player_url = self.get_player_url(player_id)
        print(f"Accessing URL: {player_url}")
        # HTML cache
        raw_file = self.raw_dir / f"{player_id}.html"
        if raw_file.exists():
            html = raw_file.read_text(encoding='utf-8')
        else:
            resp = self.session.get(player_url)
            if resp.status_code != 200:
                print(f"Failed to retrieve page for {name}. Status code: {resp.status_code}")
                return None
            html = resp.text
            raw_file.write_text(html, encoding='utf-8')
        # Parse the HTML with lxml for speed
        soup = BeautifulSoup(html, 'lxml')
        
        # Check if page exists
        not_found = soup.select_one(".page_not_found")
        if not_found:
            print(f"Player page not found for {name}")
            return None
        
        # Extract player data
        player_data = {
            'player_id': player_id,
            'name': name,
            'profile_url': player_url,
            'scrape_date': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Get player photo URL
        photo = soup.select_one("div.media-item img")
        if photo and photo.has_attr('src'):
            player_data['photo_url'] = photo['src']
        
        # Get player meta info
        meta = soup.select_one("#meta")
        if meta:
            # Get and store all paragraphs
            meta_paragraphs = meta.find_all('p')
            
            # Extract positions - check both "Position:" and "Positions:"
            for p in meta_paragraphs:
                text = p.get_text(strip=True)
                if text.startswith('Position:') or text.startswith('Positions:'):
                    # Remove "Position:" or "Positions:"
                    position_text = re.sub(r'^Positions?:', '', text).strip()
                    player_data['positions'] = self.clean_text(position_text)
                    break
            
            # Extract bats/throws
            for p in meta_paragraphs:
                text = p.get_text(strip=True)
                if text.startswith('Bats:'):
                    player_data['bats_throws'] = self.clean_text(text)
                    break
            
            # Extract height/weight (paragraph that contains 'lb' but no labels)
            for p in meta_paragraphs:
                text = p.get_text(strip=True)
                if 'lb' in text and not text.startswith('Position') and not text.startswith('Team'):
                    player_data['height_weight'] = self.clean_text(text)
                    break
            
            # Extract team info
            for p in meta_paragraphs:
                text = p.get_text(strip=True)
                if text.startswith('Team:'):
                    team_text = text.replace('Team:', '').strip()
                    player_data['team'] = self.format_team_info(self.clean_text(team_text))
                    break
            
            # Extract born info
            for p in meta_paragraphs:
                text = p.get_text(strip=True)
                if text.startswith('Born:'):
                    born_text = text.replace('Born:', '').strip()
                    player_data['born'] = self.format_born_info(self.clean_text(born_text))
                    
                    # Extract country flag if present
                    flag_img = p.select_one('img.flagicon')
                    if flag_img and flag_img.has_attr('alt'):
                        player_data['country_code'] = flag_img['alt']
                    break
        
        return player_data

    def process_player(self, player, i, total):
        """Process a single player - for threading."""
        player_id = player['id']
        name = player['name']
        
        print(f"Scraping {name} ({i+1}/{total})...")
        
        try:
            info_data = self.scrape_player_info(player_id, name)
            if info_data:
                # Save to JSON file
                info_file = self.player_info_dir / f"{player_id}.json"
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(info_data, f, indent=2)
                print(f"Saved info for {name}")
        except Exception as e:
            print(f"Error scraping {name}: {str(e)}")
    
    def scrape_all_active_players(self):
        """Scrape info for all active players using threads."""
        active_players = self.get_active_players()
        print(f"Found {len(active_players)} active players needing scraping")
        
        # Create batches of players (to avoid overwhelming the server)
        batch_size = 50  # Process 50 players at a time
        for batch_start in range(0, len(active_players), batch_size):
            batch_end = min(batch_start + batch_size, len(active_players))
            batch = active_players[batch_start:batch_end]
            
            print(f"Processing batch {batch_start//batch_size + 1}: players {batch_start+1}-{batch_end}")
            
            # Process batch with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i, player in enumerate(batch):
                    global_i = batch_start + i  # Global index
                    futures.append(
                        executor.submit(
                            self.process_player, 
                            player, 
                            global_i, 
                            len(active_players)
                        )
                    )
                
                # Wait for all futures to complete
                for future in futures:
                    future.result()
            
            # Add a longer pause between batches if not the last batch
            if batch_end < len(active_players):
                pause = random.uniform(5, 10)
                print(f"Batch complete. Pausing for {pause:.1f} seconds before next batch...")
                time.sleep(pause)

def test_single_player(player_id, name):
    """Test the scraper with a single player."""
    scraper = PlayerDataScraper()
    player_data = scraper.scrape_player_info(player_id, name)
    if player_data:
        print("\nExtracted Player Data:")
        print(json.dumps(player_data, indent=2))
        
        print("\nData Verification:")
        print(f"1. Photo URL: {'✓' if 'photo_url' in player_data else '✗'}")
        print(f"2. Name: {player_data['name']}")
        print(f"3. Positions: {'✓' if 'positions' in player_data else '✗'} {player_data.get('positions', 'Not found')}")
        print(f"4. Bats/Throws: {'✓' if 'bats_throws' in player_data else '✗'} {player_data.get('bats_throws', 'Not found')}")
        print(f"5. Height/Weight: {'✓' if 'height_weight' in player_data else '✗'} {player_data.get('height_weight', 'Not found')}")
        print(f"6. Team: {'✓' if 'team' in player_data else '✗'} {player_data.get('team', 'Not found')}")
        print(f"7. Born: {'✓' if 'born' in player_data else '✗'} {player_data.get('born', 'Not found')}")

def test_multiple_players():
    """Test the scraper with multiple players."""
    test_cases = [
        {"id": "ohtansh01", "name": "Shohei Ohtani"},
        {"id": "irvinja01", "name": "Jake Irvin"},
        {"id": "judgeaa01", "name": "Aaron Judge"}
    ]
    
    scraper = PlayerDataScraper()
    results = {}
    
    for player in test_cases:
        print(f"\nTesting with {player['name']}...")
        player_data = scraper.scrape_player_info(player['id'], player['name'])
        
        if player_data:
            results[player['id']] = player_data
            
            print("\nExtracted Player Data:")
            print(json.dumps(player_data, indent=2))
            
            print("\nData Verification:")
            print(f"1. Photo URL: {'✓' if 'photo_url' in player_data else '✗'}")
            print(f"2. Name: {player_data['name']}")
            print(f"3. Positions: {'✓' if 'positions' in player_data else '✗'} {player_data.get('positions', 'Not found')}")
            print(f"4. Bats/Throws: {'✓' if 'bats_throws' in player_data else '✗'} {player_data.get('bats_throws', 'Not found')}")
            print(f"5. Height/Weight: {'✓' if 'height_weight' in player_data else '✗'} {player_data.get('height_weight', 'Not found')}")
            print(f"6. Team: {'✓' if 'team' in player_data else '✗'} {player_data.get('team', 'Not found')}")
            print(f"7. Born: {'✓' if 'born' in player_data else '✗'} {player_data.get('born', 'Not found')}")
        
        # Add a delay between requests
        if player != test_cases[-1]:  # Skip delay after last player
            delay = random.uniform(1, 2)
            print(f"Waiting {delay:.1f} seconds...")
            time.sleep(delay)
    
    return results

def convert_jsons_to_csv():
    """Convert all player-info JSON files to a single CSV."""
    from pathlib import Path
    import json, csv
    files = list(Path("data/baseball-ref/player-info").glob("*.json"))
    if not files:
        print("No JSON files to convert.")
        return
    records = [json.load(open(str(f), encoding='utf-8')) for f in files]
    keys = sorted({k for rec in records for k in rec})
    out = Path("data/baseball-ref/player-info.csv")
    with open(out, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, keys)
        writer.writeheader()
        writer.writerows(records)
    print(f"Converted {len(records)} JSON files to CSV: {out}")

def main():
    """Main function to run the scraper."""
    print("Baseball Reference Player Data Scraper")
    print("-------------------------------------")
    print("1. Test with Shohei Ohtani")
    print("2. Test with Jake Irvin")
    print("3. Test with multiple players")
    print("4. Run full scraper for all active players")
    print("5. Test with custom player ID")
    print("6. Convert all JSONs to CSV")
    choice = input("Enter your choice (1-6): ")
    
    scraper = PlayerDataScraper(max_workers=5)  # Adjust number of workers as needed
    
    if choice == '1':
        test_single_player("ohtansh01", "Shohei Ohtani")
    elif choice == '2':
        test_single_player("irvinja01", "Jake Irvin")
    elif choice == '3':
        test_multiple_players()
    elif choice == '4':
        scraper.scrape_all_active_players()
    elif choice == '5':
        player_id = input("Enter player ID (e.g., 'ohtansh01'): ")
        name = input("Enter player name: ")
        test_single_player(player_id, name)
    elif choice == '6':
        convert_jsons_to_csv()
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()