import os
import pandas as pd
from datetime import datetime
import re
today = datetime.now().strftime('%Y-%m-%d')
base = f"data/{today}"
sim_file  = os.path.join(base, "pitcher_alt_strikeouts.csv")
book_file = os.path.join(base, f"bovada_all_pitcher_props_{today}.csv")
df_sim  = pd.read_csv(sim_file)
df_book = pd.read_csv(book_file)
def find_pitcher_col(df):
     for c in df.columns:
         if "pitcher" in c.lower():
             return c
     raise KeyError("No 'pitcher' column found")
sim_pitch = find_pitcher_col(df_sim)
book_pitch= find_pitcher_col(df_book)
val_cols_sim  = [c for c in df_sim.columns  if re.match(r"\d+K", c)]
book_k_map = {}
for c in df_book.columns:
    m = re.match(r"(\d+)\+ Strikeouts", c)
    if m:
        new_c = f"{m.group(1)}K"
        book_k_map[c] = new_c
df_book = df_book.rename(columns=book_k_map)
val_cols_book = list(book_k_map.values())
sim  = df_sim.melt(id_vars=[sim_pitch],  value_vars=val_cols_sim,  var_name="Line", value_name="Sim")
book = df_book.melt(id_vars=[book_pitch], value_vars=val_cols_book, var_name="Line", value_name="Book")
norm = lambda s: re.sub(r"[^\w]", "", str(s).lower())
sim["n"]  = sim[sim_pitch].map(norm)
book["n"] = book[book_pitch].map(norm)
sim["L"]  = sim["Line"].str.replace("K","").astype(int)
book["L"] = book["Line"].str.replace("K","").astype(int)
def to_prob(o):
     o = float(o)
     return 100/(o+100) if o>0 else -o/(-o+100)
merged = sim.merge(book, on=["n","L"])
merged["P_sim"]  = merged["Sim"].map(to_prob)
merged["P_book"] = merged["Book"].map(to_prob)
merged["Edge"]   = merged["P_sim"] - merged["P_book"]
top = merged.nlargest(20, "Edge")
out  = top[[sim_pitch, "L", "Edge", "Sim", "Book", "P_sim", "P_book"]]
out_file = os.path.join(base, f"value_{today}.csv")
out.to_csv(out_file, index=False)
print("\nTop Pitcher Alt K Value Edges:\n")
print(f"{'Pitcher':20} {'Line':>5} {'Edge':>8} {'Sim Odds':>10} {'Book Odds':>10} {'Sim Prob':>9} {'Book Prob':>9}")
for _, row in out.iterrows():
    line = f"{row[sim_pitch]:20} {str(row['L'])+'K':>5} {row['Edge']:+8.3f} {row['Sim']:10} {row['Book']:10} {row['P_sim']:.3f} {row['P_book']:.3f}"
    print(line)
print(f"\nResults saved to {out_file}\n")

# Markdown Report
md_file = os.path.join(base, f"value_{today}.md")
with open(md_file, "w") as f:
    f.write("# Top Pitcher Alt K Value Edges\n\n")
    f.write("| {:20} | {:>5} | {:>8} | {:>10} | {:>10} | {:>9} | {:>9} |\n".format(
        "Pitcher", "Line", "Edge", "Sim Odds", "Book Odds", "Sim Prob", "Book Prob"))
    f.write("|" + "-"*22 + "|" + "-"*7 + "|" + "-"*10 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*11 + "|" + "-"*11 + "|\n")
    for _, row in out.iterrows():
        f.write("| {:20} | {:>5} | {:+8.3f} | {:10} | {:10} | {:9.3f} | {:9.3f} |\n".format(
            row[sim_pitch], str(row['L'])+'K', row['Edge'], row['Sim'], row['Book'], row['P_sim'], row['P_book']))
    f.write("\n## 3 Best Value Edges\n\n")
    for _, row in out.head(3).iterrows():
        f.write(f"- **{row[sim_pitch]} {row['L']}K**: Sim Odds {row['Sim']}, Book Odds {row['Book']}, Edge {row['Edge']:+.3f}\n")
print(f"Markdown report saved to {md_file}")

# HTML Report
html_file = os.path.join(base, f"value_{today}.html")
with open(html_file, "w") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Top Pitcher Alt K Value Edges</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f8f9fa;
        }}
        h1, h2, h3 {{
            text-align: center;
            color: #2c3e50;
        }}
        .section-title {{
            text-align: center;
            margin: 40px 0 20px 0;
            color: #2c3e50;
            border-bottom: 2px solid #1f77b4;
            padding-bottom: 10px;
        }}
        table {{
            border-collapse: collapse;
            margin: 0 auto 30px auto;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.07);
            font-size: 15px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 14px;
            text-align: right;
        }}
        th {{
            background-color: #f8f9fa;
            color: #2c3e50;
            text-align: center;
        }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #eaf6ff; }}
        ul {{
            max-width: 600px;
            margin: 0 auto;
            font-size: 16px;
        }}
        .summary {{
            text-align: center;
            margin-top: 30px;
            color: #555;
        }}
    </style>
</head>
<body>
    <h1>MLB Value Edge Report</h1>
    <div class="section-title">Date: {today}</div>
    <h2>Top Pitcher Alt K Value Edges</h2>
    {out.to_html(index=False, float_format='%.3f', border=0)}
    <h3>3 Best Value Edges</h3>
    <ul>
""")
    for _, row in out.head(3).iterrows():
        f.write(f"<li><b>{row[sim_pitch]} {row['L']}K</b>: Sim Odds {row['Sim']}, Book Odds {row['Book']}, Edge {row['Edge']:+.3f}</li>\n")
    f.write("""
    </ul>
    <div class="summary">
        <p>Generated by MLB AI</p>
    </div>
</body>
</html>
""")
print(f"HTML report saved to {html_file}")

# TXT Report
txt_file = os.path.join(base, f"value_{today}.txt")
with open(txt_file, "w") as f:
    f.write("Top Pitcher Alt K Value Edges\n\n")
    f.write(f"{'Pitcher':20} {'Line':>5} {'Edge':>8} {'Sim Odds':>10} {'Book Odds':>10} {'Sim Prob':>9} {'Book Prob':>9}\n")
    f.write("-" * 80 + "\n")
    for _, row in out.iterrows():
        f.write(f"{row[sim_pitch]:20} {str(row['L'])+'K':>5} {row['Edge']:>8.3f} {row['Sim']:>10} {row['Book']:>10} {row['P_sim']:>9.3f} {row['P_book']:>9.3f}\n")
    f.write("\n3 Best Value Edges:\n")
    for _, row in out.head(3).iterrows():
        f.write(f"- {row[sim_pitch]:20} {str(row['L'])+'K':>5}: Sim Odds {row['Sim']}, Book Odds {row['Book']}, Edge {row['Edge']:+.3f}\n")
print(f"Text report saved to {txt_file}")

# PDF Report
try:
    import matplotlib.pyplot as plt
    from pandas.plotting import table as pd_table
    pdf_file = os.path.join(base, f"value_{today}.pdf")
    fig, ax = plt.subplots(figsize=(10, min(0.5+0.4*len(out), 12)))
    ax.axis('off')
    pd_table(ax, out.head(20), loc='center', colWidths=[0.13]*len(out.columns))
    plt.title("Top Pitcher Alt K Value Edges", fontsize=14, weight='bold')
    plt.savefig(pdf_file, bbox_inches='tight')
    plt.close(fig)
    print(f"PDF report saved to {pdf_file}")
except Exception as e:
    print(f"PDF report not created: {e}")