#import os
#import pandas as pd
#from datetime import datetime
#import re
#
## Paths
#today = datetime.now().strftime('%Y-%m-%d')
#base = f'data/{today}'
#sim_file  = os.path.join(base, 'pitcher_alt_strikeouts.csv')
#book_file = os.path.join(base, f'bovada_all_pitcher_props_{today}.csv')
#
## Load
#df_sim  = pd.read_csv(sim_file)
#df_book = pd.read_csv(book_file)
#
## Melt long
#sim = df_sim.melt(['Pitcher'], [c for c in df_sim if 'K' in c], 'Line', 'Sim')
#book= df_book.melt(['Pitcher'], [c for c in df_book if 'K' in c], 'Line', 'Book')
#
## Normalize
#norm = lambda s: re.sub(r'[^\w]', '', s.lower())
#sim['n']=sim.Pitcher.map(norm)
#book['n']=book.Pitcher.map(norm)
#sim['L']=sim.Line.str.replace('K','').astype(int)
#book['L']=book.Line.str.replace('K','').astype(int)
#
## Merge & probs
#def to_p(o):
#    o=float(o)
#    return (100/(o+100) if o>0 else -o/(-o+100))
#merged = sim.merge(book, on=['n','L'])
#merged['P_sim']=merged.Sim.map(to_p)
#merged['P_book']=merged.Book.map(to_p)
#merged['Edge']=merged.P_sim - merged.P_book
#
## Top 20 & save
#top = merged.nlargest(20, 'Edge')
#top[['Pitcher_x','Line','Sim','Book','P_sim','P_book','Edge']] \
#    .to_csv(os.path.join(base, f'value_{today}.csv'), index=False)
#print('Done!')


import os
import pandas as pd
from datetime import datetime
import re

# Determine today's data folder
today = datetime.now().strftime('%Y-%m-%d')
base = f"data/{today}"

# File paths
sim_file  = os.path.join(base, "pitcher_alt_strikeouts.csv")
book_file = os.path.join(base, f"bovada_all_pitcher_props_{today}.csv")

# Load CSVs
df_sim  = pd.read_csv(sim_file)
df_book = pd.read_csv(book_file)

# Helper to find the pitcher column
def find_pitcher_col(df):
     for c in df.columns:
         if "pitcher" in c.lower():
             return c
     raise KeyError("No 'pitcher' column found")

sim_pitch = find_pitcher_col(df_sim)
book_pitch= find_pitcher_col(df_book)

# Identify prop columns (e.g., '2K','3K',...) for sim
val_cols_sim  = [c for c in df_sim.columns  if re.match(r"\d+K", c)]

# For book, find columns like '3+ Strikeouts', map to '3K', and rename
book_k_map = {}
for c in df_book.columns:
    m = re.match(r"(\d+)\+ Strikeouts", c)
    if m:
        new_c = f"{m.group(1)}K"
        book_k_map[c] = new_c
df_book = df_book.rename(columns=book_k_map)
val_cols_book = list(book_k_map.values())

# Melt to long format
sim  = df_sim.melt(id_vars=[sim_pitch],  value_vars=val_cols_sim,  var_name="Line", value_name="Sim")
book = df_book.melt(id_vars=[book_pitch], value_vars=val_cols_book, var_name="Line", value_name="Book")

# Normalize pitcher names and extract line number
norm = lambda s: re.sub(r"[^\w]", "", str(s).lower())
sim["n"]  = sim[sim_pitch].map(norm)
book["n"] = book[book_pitch].map(norm)
sim["L"]  = sim["Line"].str.replace("K","").astype(int)
book["L"] = book["Line"].str.replace("K","").astype(int)

# American odds → implied probability
def to_prob(o):
     o = float(o)
     return 100/(o+100) if o>0 else -o/(-o+100)

# Merge datasets on normalized name + line
merged = sim.merge(book, on=["n","L"])
merged["P_sim"]  = merged["Sim"].map(to_prob)
merged["P_book"] = merged["Book"].map(to_prob)
merged["Edge"]   = merged["P_sim"] - merged["P_book"]

# Select top 20 edges and save
top = merged.nlargest(20, "Edge")
out  = top[[sim_pitch, "L", "Sim", "Book", "P_sim", "P_book", "Edge"]]
out_file = os.path.join(base, f"value_{today}.csv")
out.to_csv(out_file, index=False)
print(f"Done! Results saved to {out_file}")
