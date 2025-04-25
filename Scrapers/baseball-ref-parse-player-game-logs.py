import os
import pandas as pd
from bs4 import BeautifulSoup

input_dir = "data/baseball-ref/raw-players-game-logs"
output_dir = "data/baseball-ref/player-game-logs"

os.makedirs(output_dir, exist_ok=True)
for filename in os.listdir(input_dir):
    if not filename.endswith(".html"):
        continue
    filepath = os.path.join(input_dir, filename)
    print(f"Parsing: {filename}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        tables = soup.find_all("table")
        game_log_df = None
        for table in tables:
            try:
                df = pd.read_html(str(table))[0]
                if any(col in df.columns for col in ["Date", "PA", "Gcar"]):
                    game_log_df = df
                    break
            except Exception as e:
                continue
        if game_log_df is not None:
            output_filename = filename.replace(".html", ".csv")
            output_path = os.path.join(output_dir, output_filename)
            game_log_df.to_csv(output_path, index=False)
            print(f"Saved: {output_filename}")
        else:
            print(f"No valid game log found in: {filename}")
    except Exception as e:
        print(f"Failed to process {filename}: {e}")
