# from playwright.async_api import async_playwright
# import asyncio
# import time
# import json
# import os
# import random
# import csv
# import re
# from typing import Set, List, Dict
# from pathlib import Path
# from bs4 import BeautifulSoup

# class MLBScraper:
#     def __init__(self):
#         self.letters = [chr(i) for i in range(ord('a'), ord('z')+1)]
#         self.base_url = "https://www.baseball-reference.com/players/{letter}/"
#         self.player_ids_by_letter = {letter: set() for letter in self.letters}
        
#         # Create necessary directories
#         self.raw_dir = Path("data/baseball-ref/raw")
#         self.raw_dir.mkdir(parents=True, exist_ok=True)
        
#         self.csv_dir = Path("data/baseball-ref/player-ids")
#         self.csv_dir.mkdir(parents=True, exist_ok=True)
    
#     async def download_player_index_pages(self, test_single_letter=False):
#         """Download HTML for all player index pages and save to disk."""
#         async with async_playwright() as p:
#             browser = await p.firefox.launch(headless=True)
#             context = await browser.new_context(
#                 user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0"
#             )
#             page = await context.new_page()
#             page.set_default_timeout(15000)
            
#             letters_to_scrape = [self.letters[0]] if test_single_letter else self.letters
            
#             for i, letter in enumerate(letters_to_scrape):
#                 # Skip if already downloaded
#                 file_path = self.raw_dir / f"players-{letter}.html"
#                 if file_path.exists():
#                     print(f"Skipping letter {letter}, already downloaded")
#                     continue
                    
#                 url = self.base_url.format(letter=letter)
#                 try:
#                     print(f"Downloading players with last names starting with '{letter}' ({i+1}/{len(letters_to_scrape)})...")
                    
#                     await page.goto(url, wait_until="domcontentloaded")
#                     await asyncio.sleep(2)  # Wait for dynamic content
#                     content = await page.content()
                    
#                     with open(file_path, 'w', encoding='utf-8') as f:
#                         f.write(content)
#                     print(f"Saved {letter} index to {file_path}")
                    
#                     # Variable delay to avoid detection
#                     delay = random.uniform(1, 3)
#                     print(f"Waiting {delay:.1f} seconds...")
#                     await asyncio.sleep(delay)
                    
#                 except Exception as e:
#                     print(f"Error downloading letter {letter}: {str(e)}")
                    
#                     # Save results after each letter in case of crash
#                     self.parse_downloaded_pages()
#                     self.save_results()
            
#             await browser.close()
    
#     def extract_player_ids_from_html(self, html_content: str, current_letter: str) -> Set[tuple]:
#         """Extract player IDs from HTML content using BeautifulSoup."""
#         if not html_content or html_content.strip() == "":
#             print(f"Warning: Empty HTML content for letter {current_letter}")
#             return set()
            
#         soup = BeautifulSoup(html_content, 'html.parser')
#         player_ids = set()
        
#         # Find the div containing all players
#         player_div = soup.find('div', id='div_players_')
#         if not player_div:
#             print(f"Warning: Could not find player div for letter {current_letter}")
#             return set()
        
#         # Find all player entries (each in a <p> tag)
#         for p_tag in player_div.find_all('p'):
#             try:
#                 # Find the player link
#                 player_link = p_tag.find('a', href=lambda href: href and '/players/' in href)
#                 if not player_link:
#                     continue
                
#                 href = player_link.get('href', '')
#                 # Extract player ID from URL pattern: /players/a/aasedo01.shtml
#                 import re
#                 match = re.search(r'/players/([a-z])/([^.]+)\.shtml', href)
#                 if match:
#                     letter = match.group(1)
#                     player_id = match.group(2)
#                     # Only include players whose IDs start with the current letter
#                     if letter == current_letter:
#                         name = player_link.text.strip()
                        
#                         # Extract years from text after the link
#                         # Text format is typically the player name followed by years in parentheses
#                         years_text = ""
#                         # The years are usually in the text directly following the player link
#                         next_text = player_link.next_sibling
#                         if next_text:
#                             years_match = re.search(r'\(([^)]+)\)', next_text)
#                             if years_match:
#                                 years_text = years_match.group(1)
                        
#                         # Check if player is active (has ** in the HTML)
#                         is_active = '**' in str(p_tag)
                        
#                         player_ids.add((player_id, name, is_active, years_text))
#             except Exception as e:
#                 print(f"Error processing player entry: {str(e)}")
        
#         return player_ids
    
#     def parse_downloaded_pages(self):
#         """Parse all downloaded HTML files to extract player IDs."""
#         for letter_file in self.raw_dir.glob('players-*.html'):
#             letter = letter_file.stem.split('-')[1]  # Extract letter from filename
#             try:
#                 print(f"Parsing letter {letter}...")
#                 with open(letter_file, 'r', encoding='utf-8') as f:
#                     html_content = f.read()
                
#                 player_ids = self.extract_player_ids_from_html(html_content, letter)
#                 print(f"Found {len(player_ids)} players for letter {letter}")
#                 self.player_ids_by_letter[letter] = player_ids
                
#                 # Save to CSV immediately after parsing each letter
#                 self.save_letter_to_csv(letter, player_ids)
                
#             except Exception as e:
#                 print(f"Error parsing letter {letter}: {str(e)}")
    
#     def save_letter_to_csv(self, letter: str, player_ids: Set[tuple]):
#         """Save player IDs for a specific letter to a CSV file."""
#         csv_path = self.csv_dir / f"player-ids-{letter}.csv"
        
#         with open(csv_path, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerow(['player_id', 'name', 'is_active', 'years'])  # Header
#             # Sort by player ID before writing
#             sorted_players = sorted(player_ids, key=lambda x: x[0])
#             writer.writerows(sorted_players)
        
#         print(f"Saved {len(player_ids)} players to {csv_path}")
    
#     def save_results(self):
#         """Save summary results to a JSON file."""
#         data = {
#             "total_players": sum(len(ids) for ids in self.player_ids_by_letter.values()),
#             "players_by_letter": {letter: len(ids) for letter, ids in self.player_ids_by_letter.items()},
#             "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
#             "letters_scraped": [f.stem.split('-')[1] for f in self.raw_dir.glob('players-*.html')]
#         }
        
#         summary_path = self.csv_dir / "summary.json"
#         with open(summary_path, 'w') as f:
#             json.dump(data, f, indent=2)
#         print(f"Saved summary to {summary_path}")

#     def get_html_content(self, letter: str) -> str:
#         """Get HTML content for a given letter from disk."""
#         file_path = self.raw_dir / f"players-{letter}.html"
#         if not file_path.exists():
#             return ""
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 return f.read()
#         except Exception as e:
#             print(f"Error reading file for letter {letter}: {str(e)}")
#             return ""
    
#     def is_letter_downloaded(self, letter: str) -> bool:
#         """Check if a letter file exists and has been downloaded."""
#         csv_path = self.csv_dir / f"player-ids-{letter}.csv"
#         return csv_path.exists()

# async def main(test_single_letter=False):
#     scraper = MLBScraper()
    
#     try:
#         # First download all player index pages
#         await scraper.download_player_index_pages(test_single_letter)
        
#         # Then parse all downloaded pages
#         scraper.parse_downloaded_pages()
        
#         # Save final summary
#         scraper.save_results()
        
#         print("Scraping completed successfully!")
#         if test_single_letter:
#             print(f"Test completed for letter '{scraper.letters[0]}'")
#     except KeyboardInterrupt:
#         print("\nScraping interrupted by user. Saving current results...")
#         scraper.parse_downloaded_pages()
#         scraper.save_results()
#     except Exception as e:
#         print(f"Error during scraping: {str(e)}")
#         scraper.parse_downloaded_pages()
#         scraper.save_results()

# if __name__ == "__main__":
#     import sys
#     # Check if command line args contain 'test'
#     test_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'test'
#     asyncio.run(main(test_single_letter=test_mode))


from playwright.async_api import async_playwright
import asyncio
import time
import json
import os
import random
import csv
import re
from typing import Set, List, Dict
from pathlib import Path
from bs4 import BeautifulSoup

class MLBScraper:
    def __init__(self):
        self.letters = [chr(i) for i in range(ord('a'), ord('z')+1)]
        self.base_url = "https://www.baseball-reference.com/players/{letter}/"
        self.player_ids_by_letter = {letter: set() for letter in self.letters}
        
        # Create necessary directories
        self.raw_dir = Path("data/baseball-ref/raw")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        self.csv_dir = Path("data/baseball-ref/player-ids")
        self.csv_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_player_index_pages(self, test_single_letter=False):
        """Download HTML for all player index pages and save to disk."""
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0"
            )
            page = await context.new_page()
            page.set_default_timeout(15000)
            
            letters_to_scrape = [self.letters[0]] if test_single_letter else self.letters
            
            for i, letter in enumerate(letters_to_scrape):
                # Skip if already downloaded
                file_path = self.raw_dir / f"players-{letter}.html"
                if file_path.exists():
                    print(f"Skipping letter {letter}, already downloaded")
                    continue
                    
                url = self.base_url.format(letter=letter)
                try:
                    print(f"Downloading players with last names starting with '{letter}' ({i+1}/{len(letters_to_scrape)})...")
                    
                    await page.goto(url, wait_until="domcontentloaded")
                    await asyncio.sleep(2)  # Wait for dynamic content
                    content = await page.content()
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Saved {letter} index to {file_path}")
                    
                    # Variable delay to avoid detection
                    delay = random.uniform(2, 4)
                    print(f"Waiting {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    print(f"Error downloading letter {letter}: {str(e)}")
                    
                    # Save results after each letter in case of crash
                    self.parse_downloaded_pages()
                    self.save_results()
            
            await browser.close()
    
    def extract_player_ids_from_html(self, html_content: str, current_letter: str) -> Set[tuple]:
        """Extract player IDs from HTML content using BeautifulSoup."""
        if not html_content or html_content.strip() == "":
            print(f"Warning: Empty HTML content for letter {current_letter}")
            return set()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        player_ids = set()
        
        # Find the div containing all players
        player_div = soup.find('div', id='div_players_')
        if not player_div:
            print(f"Warning: Could not find player div for letter {current_letter}")
            return set()
        
        # Find all player entries (each in a <p> tag)
        for p_tag in player_div.find_all('p'):
            try:
                # Find the player link
                player_link = p_tag.find('a', href=lambda href: href and '/players/' in href)
                if not player_link:
                    continue
                
                href = player_link.get('href', '')
                # Extract player ID from URL pattern: /players/a/aasedo01.shtml
                import re
                match = re.search(r'/players/([a-z])/([^.]+)\.shtml', href)
                if match:
                    letter = match.group(1)
                    player_id = match.group(2)
                    # Only include players whose IDs start with the current letter
                    if letter == current_letter:
                        name = player_link.text.strip()
                        
                        # Extract years from text after the link
                        # Text format is typically the player name followed by years in parentheses
                        years_text = ""
                        # The years are usually in the text directly following the player link
                        next_text = player_link.next_sibling
                        if next_text:
                            years_match = re.search(r'\(([^)]+)\)', next_text)
                            if years_match:
                                years_text = years_match.group(1)
                        
                        player_ids.add((player_id, name, years_text))
            except Exception as e:
                print(f"Error processing player entry: {str(e)}")
        
        return player_ids
    
    def parse_downloaded_pages(self):
        """Parse all downloaded HTML files to extract player IDs."""
        for letter_file in self.raw_dir.glob('players-*.html'):
            letter = letter_file.stem.split('-')[1]  # Extract letter from filename
            try:
                print(f"Parsing letter {letter}...")
                with open(letter_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                player_ids = self.extract_player_ids_from_html(html_content, letter)
                print(f"Found {len(player_ids)} players for letter {letter}")
                self.player_ids_by_letter[letter] = player_ids
                
                # Save to CSV immediately after parsing each letter
                self.save_letter_to_csv(letter, player_ids)
                
            except Exception as e:
                print(f"Error parsing letter {letter}: {str(e)}")
    
    def save_letter_to_csv(self, letter: str, player_ids: Set[tuple]):
        """Save player IDs for a specific letter to a CSV file."""
        csv_path = self.csv_dir / f"player-ids-{letter}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['player_id', 'name', 'years'])  # Header
            # Sort by player ID before writing
            sorted_players = sorted(player_ids, key=lambda x: x[0])
            writer.writerows(sorted_players)
        
        print(f"Saved {len(player_ids)} players to {csv_path}")
    
    def save_results(self):
        """Save summary results to a JSON file."""
        data = {
            "total_players": sum(len(ids) for ids in self.player_ids_by_letter.values()),
            "players_by_letter": {letter: len(ids) for letter, ids in self.player_ids_by_letter.items()},
            "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "letters_scraped": [f.stem.split('-')[1] for f in self.raw_dir.glob('players-*.html')]
        }
        
        summary_path = self.csv_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved summary to {summary_path}")

    def get_html_content(self, letter: str) -> str:
        """Get HTML content for a given letter from disk."""
        file_path = self.raw_dir / f"players-{letter}.html"
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file for letter {letter}: {str(e)}")
            return ""
    
    def is_letter_downloaded(self, letter: str) -> bool:
        """Check if a letter file exists and has been downloaded."""
        csv_path = self.csv_dir / f"player-ids-{letter}.csv"
        return csv_path.exists()

async def main(test_single_letter=False):
    scraper = MLBScraper()
    
    try:
        # First download all player index pages
        await scraper.download_player_index_pages(test_single_letter)
        
        # Then parse all downloaded pages
        scraper.parse_downloaded_pages()
        
        # Save final summary
        scraper.save_results()
        
        print("Scraping completed successfully!")
        if test_single_letter:
            print(f"Test completed for letter '{scraper.letters[0]}'")
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving current results...")
        scraper.parse_downloaded_pages()
        scraper.save_results()
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        scraper.parse_downloaded_pages()
        scraper.save_results()

if __name__ == "__main__":
    import sys
    # Check if command line args contain 'test'
    test_mode = len(sys.argv) > 1 and sys.argv[1].lower() == 'test'
    asyncio.run(main(test_single_letter=test_mode))