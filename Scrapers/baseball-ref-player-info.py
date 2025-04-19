# # import requests
# # from bs4 import BeautifulSoup
# # import json
# # import time
# # import re
# # from pathlib import Path
# # import csv
# # import random

# # class PlayerDataScraper:
# #     def __init__(self):
# #         self.base_url = "https://www.baseball-reference.com/players"
# #         self.headers = {
# #             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
# #         }
# #         self.player_info_dir = Path("data/baseball-ref/player-info")
# #         self.player_info_dir.mkdir(parents=True, exist_ok=True)
        
# #     def get_active_players(self) -> list:
# #         """Read all CSV files and return list of active players."""
# #         active_players = []
# #         csv_dir = Path("data/baseball-ref/player-ids")
        
# #         if not csv_dir.exists():
# #             print(f"Error: CSV directory not found at {csv_dir}")
# #             return active_players
            
# #         csv_files = list(csv_dir.glob("player-ids-*.csv"))
# #         if not csv_files:
# #             print(f"Error: No CSV files found in {csv_dir}")
# #             return active_players
            
# #         for csv_file in csv_files:
# #             print(f"Reading {csv_file.name}...")
# #             try:
# #                 with open(csv_file, 'r', encoding='utf-8') as f:
# #                     reader = csv.DictReader(f)
# #                     for row in reader:
# #                         # Check if years field ends with 2024 or 2025
# #                         years = row.get('years', '').strip()
# #                         if years.endswith('2024') or years.endswith('2025'):
# #                             active_players.append({
# #                                 'id': row['player_id'],
# #                                 'name': row['name'],
# #                                 'years': years
# #                             })
# #             except Exception as e:
# #                 print(f"Error reading {csv_file.name}: {str(e)}")
# #                 continue
        
# #         print(f"Total active players found: {len(active_players)}")
# #         if active_players:
# #             print("First few active players:")
# #             for player in active_players[:5]:
# #                 print(f"- {player['name']} ({player['id']}) - {player['years']}")
                
# #         return active_players
        
# #     def get_player_url(self, player_id: str) -> str:
# #         """Generate the proper URL for a player's profile page."""
# #         # Player IDs have format like 'ohtansh01'
# #         # URL pattern is first letter of last name/full ID.shtml
# #         first_letter = player_id[0]
# #         return f"{self.base_url}/{first_letter}/{player_id}.shtml"

# #     def clean_text(self, text):
# #         """Clean up text by removing extra whitespace and normalizing spaces."""
# #         if not text:
# #             return text
# #         text = re.sub(r'\s+', ' ', text)
# #         text = text.replace('\n', ' ').replace('\t', ' ')
# #         # Fix spacing around punctuation
# #         text = re.sub(r'\s*([,.:;])\s*', r'\1 ', text)
# #         # Fix spacing around bullets
# #         text = re.sub(r'\s*•\s*', ' • ', text)
# #         # Remove leading/trailing spaces
# #         return text.strip()

# #     def scrape_player_info(self, player_id: str, name: str) -> dict:
# #         """Scrape player info from their profile page."""
# #         player_url = self.get_player_url(player_id)
# #         print(f"Accessing URL: {player_url}")
        
# #         response = requests.get(player_url, headers=self.headers)
# #         if response.status_code != 200:
# #             print(f"Failed to retrieve page for {name}. Status code: {response.status_code}")
# #             return None
        
# #         # Parse the HTML
# #         soup = BeautifulSoup(response.text, 'html.parser')
        
# #         # Check if page exists
# #         not_found = soup.select_one(".page_not_found")
# #         if not_found:
# #             print(f"Player page not found for {name}")
# #             return None
        
# #         # Extract player data
# #         player_data = {
# #             'player_id': player_id,
# #             'name': name,
# #             'profile_url': player_url,
# #             'scrape_date': time.strftime("%Y-%m-%d %H:%M:%S")
# #         }
        
# #         # Get player photo URL
# #         photo = soup.select_one("div.media-item img")
# #         if photo and photo.has_attr('src'):
# #             player_data['photo_url'] = photo['src']
        
# #         # Get player meta info
# #         meta = soup.select_one("#meta")
# #         if meta:
# #             # Get and store all paragraphs
# #             meta_paragraphs = meta.find_all('p')
            
# #             # Extract positions
# #             for p in meta_paragraphs:
# #                 text = p.get_text(strip=True)
# #                 if text.startswith('Positions:'):
# #                     player_data['positions'] = self.clean_text(text.replace('Positions:', ''))
# #                     break
            
# #             # Extract bats/throws
# #             for p in meta_paragraphs:
# #                 text = p.get_text(strip=True)
# #                 if text.startswith('Bats:'):
# #                     player_data['bats_throws'] = self.clean_text(text)
# #                     break
            
# #             # Extract height/weight (paragraph that contains 'lb' but no labels)
# #             for p in meta_paragraphs:
# #                 text = p.get_text(strip=True)
# #                 if 'lb' in text and not text.startswith('Position') and not text.startswith('Team'):
# #                     player_data['height_weight'] = self.clean_text(text)
# #                     break
            
# #             # Extract team info
# #             for p in meta_paragraphs:
# #                 text = p.get_text(strip=True)
# #                 if text.startswith('Team:'):
# #                     player_data['team'] = self.clean_text(text.replace('Team:', ''))
# #                     break
            
# #             # Extract born info
# #             for p in meta_paragraphs:
# #                 text = p.get_text(strip=True)
# #                 if text.startswith('Born:'):
# #                     player_data['born'] = self.clean_text(text.replace('Born:', ''))
                    
# #                     # Extract country flag if present
# #                     flag_img = p.select_one('img.flagicon')
# #                     if flag_img and flag_img.has_attr('alt'):
# #                         player_data['country_code'] = flag_img['alt']
# #                     break
        
# #         return player_data

# #     def scrape_all_active_players(self):
# #         """Scrape info for all active players."""
# #         active_players = self.get_active_players()
# #         print(f"Found {len(active_players)} active players")
        
# #         for i, player in enumerate(active_players):
# #             player_id = player['id']
# #             name = player['name']
            
# #             # Skip if already scraped
# #             info_file = self.player_info_dir / f"{player_id}.json"
# #             if info_file.exists():
# #                 print(f"Skipping {name}, already scraped")
# #                 continue
            
# #             print(f"Scraping {name} ({i+1}/{len(active_players)})...")
            
# #             try:
# #                 info_data = self.scrape_player_info(player_id, name)
# #                 if info_data:
# #                     # Save to JSON file
# #                     with open(info_file, 'w', encoding='utf-8') as f:
# #                         json.dump(info_data, f, indent=2)
# #                     print(f"Saved info for {name}")
                
# #                 # Random delay to be respectful to the server
# #                 delay = random.uniform(1, 3)
# #                 print(f"Waiting {delay:.1f} seconds...")
# #                 time.sleep(delay)
                
# #             except Exception as e:
# #                 print(f"Error scraping {name}: {str(e)}")
# #                 continue

# # def test_single_player(player_id, name):
# #     """Test the scraper with a single player."""
# #     scraper = PlayerDataScraper()
# #     player_data = scraper.scrape_player_info(player_id, name)
# #     if player_data:
# #         print("\nExtracted Player Data:")
# #         print(json.dumps(player_data, indent=2))
        
# #         print("\nData Verification:")
# #         print(f"1. Photo URL: {'✓' if 'photo_url' in player_data else '✗'}")
# #         print(f"2. Name: {player_data['name']}")
# #         print(f"3. Positions: {'✓' if 'positions' in player_data else '✗'} {player_data.get('positions', 'Not found')}")
# #         print(f"4. Bats/Throws: {'✓' if 'bats_throws' in player_data else '✗'} {player_data.get('bats_throws', 'Not found')}")
# #         print(f"5. Height/Weight: {'✓' if 'height_weight' in player_data else '✗'} {player_data.get('height_weight', 'Not found')}")
# #         print(f"6. Team: {'✓' if 'team' in player_data else '✗'} {player_data.get('team', 'Not found')}")
# #         print(f"7. Born: {'✓' if 'born' in player_data else '✗'} {player_data.get('born', 'Not found')}")

# # def main():
# #     """Main function to run the scraper."""
# #     print("Baseball Reference Player Data Scraper")
# #     print("-------------------------------------")
# #     print("1. Test with Shohei Ohtani")
# #     print("2. Run full scraper for all active players")
# #     print("3. Test with custom player ID")
# #     choice = input("Enter your choice (1-3): ")
    
# #     scraper = PlayerDataScraper()
    
# #     if choice == '1':
# #         test_single_player("ohtansh01", "Shohei Ohtani")
# #     elif choice == '2':
# #         scraper.scrape_all_active_players()
# #     elif choice == '3':
# #         player_id = input("Enter player ID (e.g., 'ohtansh01'): ")
# #         name = input("Enter player name: ")
# #         test_single_player(player_id, name)
# #     else:
# #         print("Invalid choice!")

# # if __name__ == "__main__":
# #     main()





# ########################################################################################


# import requests
# from bs4 import BeautifulSoup
# import json
# import time
# import re
# from pathlib import Path
# import csv
# import random

# class PlayerDataScraper:
#     def __init__(self):
#         self.base_url = "https://www.baseball-reference.com/players"
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
#         }
#         self.player_info_dir = Path("data/baseball-ref/player-info")
#         self.player_info_dir.mkdir(parents=True, exist_ok=True)
        
#     def get_active_players(self) -> list:
#         """Read all CSV files and return list of active players."""
#         active_players = []
#         csv_dir = Path("data/baseball-ref/player-ids")
        
#         if not csv_dir.exists():
#             print(f"Error: CSV directory not found at {csv_dir}")
#             return active_players
            
#         csv_files = list(csv_dir.glob("player-ids-*.csv"))
#         if not csv_files:
#             print(f"Error: No CSV files found in {csv_dir}")
#             return active_players
            
#         for csv_file in csv_files:
#             print(f"Reading {csv_file.name}...")
#             try:
#                 with open(csv_file, 'r', encoding='utf-8') as f:
#                     reader = csv.DictReader(f)
#                     for row in reader:
#                         # Check if years field ends with 2024 or 2025
#                         years = row.get('years', '').strip()
#                         if years.endswith('2024') or years.endswith('2025'):
#                             active_players.append({
#                                 'id': row['player_id'],
#                                 'name': row['name'],
#                                 'years': years
#                             })
#             except Exception as e:
#                 print(f"Error reading {csv_file.name}: {str(e)}")
#                 continue
        
#         print(f"Total active players found: {len(active_players)}")
#         if active_players:
#             print("First few active players:")
#             for player in active_players[:5]:
#                 print(f"- {player['name']} ({player['id']}) - {player['years']}")
                
#         return active_players
        
#     def get_player_url(self, player_id: str) -> str:
#         """Generate the proper URL for a player's profile page."""
#         # Player IDs have format like 'ohtansh01'
#         # URL pattern is first letter of last name/full ID.shtml
#         first_letter = player_id[0]
#         return f"{self.base_url}/{first_letter}/{player_id}.shtml"

#     def clean_text(self, text):
#         """Clean up text by removing extra whitespace and normalizing spaces."""
#         if not text:
#             return text
#         text = re.sub(r'\s+', ' ', text)
#         text = text.replace('\n', ' ').replace('\t', ' ')
#         # Fix spacing around punctuation
#         text = re.sub(r'\s*([,.:;])\s*', r'\1 ', text)
#         # Fix spacing around bullets
#         text = re.sub(r'\s*•\s*', ' • ', text)
#         # Remove leading/trailing spaces
#         return text.strip()

#     def scrape_player_info(self, player_id: str, name: str) -> dict:
#         """Scrape player info from their profile page."""
#         player_url = self.get_player_url(player_id)
#         print(f"Accessing URL: {player_url}")
        
#         response = requests.get(player_url, headers=self.headers)
#         if response.status_code != 200:
#             print(f"Failed to retrieve page for {name}. Status code: {response.status_code}")
#             return None
        
#         # Parse the HTML
#         soup = BeautifulSoup(response.text, 'html.parser')
        
#         # Check if page exists
#         not_found = soup.select_one(".page_not_found")
#         if not_found:
#             print(f"Player page not found for {name}")
#             return None
        
#         # Extract player data
#         player_data = {
#             'player_id': player_id,
#             'name': name,
#             'profile_url': player_url,
#             'scrape_date': time.strftime("%Y-%m-%d %H:%M:%S")
#         }
        
#         # Get player photo URL
#         photo = soup.select_one("div.media-item img")
#         if photo and photo.has_attr('src'):
#             player_data['photo_url'] = photo['src']
        
#         # Get player meta info
#         meta = soup.select_one("#meta")
#         if meta:
#             # Get and store all paragraphs
#             meta_paragraphs = meta.find_all('p')
            
#             # Extract positions - check both "Position:" and "Positions:"
#             for p in meta_paragraphs:
#                 text = p.get_text(strip=True)
#                 if text.startswith('Position:') or text.startswith('Positions:'):
#                     # Remove "Position:" or "Positions:"
#                     position_text = re.sub(r'^Positions?:', '', text).strip()
#                     player_data['positions'] = self.clean_text(position_text)
#                     break
            
#             # Extract bats/throws
#             for p in meta_paragraphs:
#                 text = p.get_text(strip=True)
#                 if text.startswith('Bats:'):
#                     player_data['bats_throws'] = self.clean_text(text)
#                     break
            
#             # Extract height/weight (paragraph that contains 'lb' but no labels)
#             for p in meta_paragraphs:
#                 text = p.get_text(strip=True)
#                 if 'lb' in text and not text.startswith('Position') and not text.startswith('Team'):
#                     player_data['height_weight'] = self.clean_text(text)
#                     break
            
#             # Extract team info
#             for p in meta_paragraphs:
#                 text = p.get_text(strip=True)
#                 if text.startswith('Team:'):
#                     player_data['team'] = self.clean_text(text.replace('Team:', ''))
#                     break
            
#             # Extract born info
#             for p in meta_paragraphs:
#                 text = p.get_text(strip=True)
#                 if text.startswith('Born:'):
#                     player_data['born'] = self.clean_text(text.replace('Born:', ''))
                    
#                     # Extract country flag if present
#                     flag_img = p.select_one('img.flagicon')
#                     if flag_img and flag_img.has_attr('alt'):
#                         player_data['country_code'] = flag_img['alt']
#                     break
        
#         return player_data

#     def scrape_all_active_players(self):
#         """Scrape info for all active players."""
#         active_players = self.get_active_players()
#         print(f"Found {len(active_players)} active players")
        
#         for i, player in enumerate(active_players):
#             player_id = player['id']
#             name = player['name']
            
#             # Skip if already scraped
#             info_file = self.player_info_dir / f"{player_id}.json"
#             if info_file.exists():
#                 print(f"Skipping {name}, already scraped")
#                 continue
            
#             print(f"Scraping {name} ({i+1}/{len(active_players)})...")
            
#             try:
#                 info_data = self.scrape_player_info(player_id, name)
#                 if info_data:
#                     # Save to JSON file
#                     with open(info_file, 'w', encoding='utf-8') as f:
#                         json.dump(info_data, f, indent=2)
#                     print(f"Saved info for {name}")
                
#                 # Random delay to be respectful to the server
#                 delay = random.uniform(1, 3)
#                 print(f"Waiting {delay:.1f} seconds...")
#                 time.sleep(delay)
                
#             except Exception as e:
#                 print(f"Error scraping {name}: {str(e)}")
#                 continue

# def test_single_player(player_id, name):
#     """Test the scraper with a single player."""
#     scraper = PlayerDataScraper()
#     player_data = scraper.scrape_player_info(player_id, name)
#     if player_data:
#         print("\nExtracted Player Data:")
#         print(json.dumps(player_data, indent=2))
        
#         print("\nData Verification:")
#         print(f"1. Photo URL: {'✓' if 'photo_url' in player_data else '✗'}")
#         print(f"2. Name: {player_data['name']}")
#         print(f"3. Positions: {'✓' if 'positions' in player_data else '✗'} {player_data.get('positions', 'Not found')}")
#         print(f"4. Bats/Throws: {'✓' if 'bats_throws' in player_data else '✗'} {player_data.get('bats_throws', 'Not found')}")
#         print(f"5. Height/Weight: {'✓' if 'height_weight' in player_data else '✗'} {player_data.get('height_weight', 'Not found')}")
#         print(f"6. Team: {'✓' if 'team' in player_data else '✗'} {player_data.get('team', 'Not found')}")
#         print(f"7. Born: {'✓' if 'born' in player_data else '✗'} {player_data.get('born', 'Not found')}")

# def main():
#     """Main function to run the scraper."""
#     print("Baseball Reference Player Data Scraper")
#     print("-------------------------------------")
#     print("1. Test with Shohei Ohtani")
#     print("2. Test with Jake Irvin")
#     print("3. Run full scraper for all active players")
#     print("4. Test with custom player ID")
#     choice = input("Enter your choice (1-4): ")
    
#     scraper = PlayerDataScraper()
    
#     if choice == '1':
#         test_single_player("ohtansh01", "Shohei Ohtani")
#     elif choice == '2':
#         test_single_player("irvinja01", "Jake Irvin")
#     elif choice == '3':
#         scraper.scrape_all_active_players()
#     elif choice == '4':
#         player_id = input("Enter player ID (e.g., 'ohtansh01'): ")
#         name = input("Enter player name: ")
#         test_single_player(player_id, name)
#     else:
#         print("Invalid choice!")

# if __name__ == "__main__":
#     main()
    
    
    
    
    
# ########################################################################################




import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path
import csv
import random

class PlayerDataScraper:
    def __init__(self):
        self.base_url = "https://www.baseball-reference.com/players"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
        }
        self.player_info_dir = Path("data/baseball-ref/player-info")
        self.player_info_dir.mkdir(parents=True, exist_ok=True)
        
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
                            active_players.append({
                                'id': row['player_id'],
                                'name': row['name'],
                                'years': years
                            })
            except Exception as e:
                print(f"Error reading {csv_file.name}: {str(e)}")
                continue
        
        print(f"Total active players found: {len(active_players)}")
        if active_players:
            print("First few active players:")
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
        """Scrape player info from their profile page."""
        player_url = self.get_player_url(player_id)
        print(f"Accessing URL: {player_url}")
        
        response = requests.get(player_url, headers=self.headers)
        if response.status_code != 200:
            print(f"Failed to retrieve page for {name}. Status code: {response.status_code}")
            return None
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
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

    def scrape_all_active_players(self):
        """Scrape info for all active players."""
        active_players = self.get_active_players()
        print(f"Found {len(active_players)} active players")
        
        for i, player in enumerate(active_players):
            player_id = player['id']
            name = player['name']
            
            # Skip if already scraped
            info_file = self.player_info_dir / f"{player_id}.json"
            if info_file.exists():
                print(f"Skipping {name}, already scraped")
                continue
            
            print(f"Scraping {name} ({i+1}/{len(active_players)})...")
            
            try:
                info_data = self.scrape_player_info(player_id, name)
                if info_data:
                    # Save to JSON file
                    with open(info_file, 'w', encoding='utf-8') as f:
                        json.dump(info_data, f, indent=2)
                    print(f"Saved info for {name}")
                
                # Random delay to be respectful to the server
                delay = random.uniform(2, 4)
                print(f"Waiting {delay:.1f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error scraping {name}: {str(e)}")
                continue

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

def main():
    """Main function to run the scraper."""
    print("Baseball Reference Player Data Scraper")
    print("-------------------------------------")
    print("1. Test with Shohei Ohtani")
    print("2. Test with Jake Irvin")
    print("3. Test with multiple players")
    print("4. Run full scraper for all active players")
    print("5. Test with custom player ID")
    choice = input("Enter your choice (1-5): ")
    
    scraper = PlayerDataScraper()
    
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
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()