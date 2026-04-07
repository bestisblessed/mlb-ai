import statsapi
import pandas as pd
import os
import sys
from datetime import datetime
from pathlib import Path

def get_data_dir():
    if os.path.exists("data"):
        return "data"
    elif os.path.exists("../data"):
        return "../data"
    else:
        return "."

def scrape_bvp_for_date(date_str):
    DATA_DIR = get_data_dir()
    print(f"Scraping BvP data for {date_str}...")

    games = statsapi.schedule(start_date=date_str, end_date=date_str)
    if not games:
        print(f"No games found for {date_str}.")
        return

    for game in games:
        game_id = game['game_id']
        game_dir = os.path.join(DATA_DIR, date_str, str(game_id))
        os.makedirs(game_dir, exist_ok=True)
        print(f"\nProcessing Game ID: {game_id} ({game['away_name']} vs. {game['home_name']})")

        away_pitcher_name = game.get('away_probable_pitcher')
        home_pitcher_name = game.get('home_probable_pitcher')
        away_pitcher_id = game.get('away_probable_pitcher_id')
        home_pitcher_id = game.get('home_probable_pitcher_id')
        if not away_pitcher_name or not home_pitcher_name:
            print(f"  - Could not determine starting pitchers for game {game_id}.")
            continue

        try:
            box = statsapi.boxscore_data(game_id)
            away_batters = [p for p in box['away']['players'].values() if p['position']['code'] != '1']
            home_batters = [p for p in box['home']['players'].values() if p['position']['code'] != '1']
            # --- Away Batters vs Home Pitcher ---
            bvp_data_away_team = []
            for batter in away_batters:
                batter_id = batter['person']['id']
                batter_name = batter['person']['fullName']
                try:
                    bvp = statsapi.player_stat_data(batter_id, group='hitting', type='career', opponentID=home_pitcher_id)
                    splits = bvp.get('stats', [{}])[0].get('splits', [])
                    for split in splits:
                        row = {'Batter': batter_name, 'Pitcher': home_pitcher_name}
                        row.update(split.get('stat', {}))
                        bvp_data_away_team.append(row)
                except Exception as e:
                    print(f"    - Could not fetch BvP for {batter_name} vs {home_pitcher_name}: {e}")
            if bvp_data_away_team:
                df_away = pd.DataFrame(bvp_data_away_team)
                output_path = os.path.join(game_dir, "bvp_career_away_team.csv")
                df_away.to_csv(output_path, index=False)
                print(f"  - Saved career BvP data for {len(df_away)} away batters to {output_path}")
            # --- Home Batters vs Away Pitcher ---
            bvp_data_home_team = []
            for batter in home_batters:
                batter_id = batter['person']['id']
                batter_name = batter['person']['fullName']
                try:
                    bvp = statsapi.player_stat_data(batter_id, group='hitting', type='career', opponentID=away_pitcher_id)
                    splits = bvp.get('stats', [{}])[0].get('splits', [])
                    for split in splits:
                        row = {'Batter': batter_name, 'Pitcher': away_pitcher_name}
                        row.update(split.get('stat', {}))
                        bvp_data_home_team.append(row)
                except Exception as e:
                    print(f"    - Could not fetch BvP for {batter_name} vs {away_pitcher_name}: {e}")
            if bvp_data_home_team:
                df_home = pd.DataFrame(bvp_data_home_team)
                output_path = os.path.join(game_dir, "bvp_career_home_team.csv")
                df_home.to_csv(output_path, index=False)
                print(f"  - Saved career BvP data for {len(df_home)} home batters to {output_path}")
        except Exception as e:
            print(f"  - ERROR processing game {game_id}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    scrape_bvp_for_date(target_date) 