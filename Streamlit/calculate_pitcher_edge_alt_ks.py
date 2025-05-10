import os
import pandas as pd
from datetime import datetime
import re
today = datetime.now().strftime('%Y-%m-%d')
base = f"data/{today}"
report_base = os.path.join(base, "report_pitcher_alt_strikeouts")
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
merged["Edge"]   = (merged["P_sim"] - merged["P_book"]) * 100  # Edge as percent
top = merged.nlargest(14, "Edge")  # Changed from 20 to 15
out = top[[sim_pitch, "L", "Edge", "Sim", "Book", "P_sim", "P_book"]].rename(columns={"L": "K"})
out_file = report_base + ".csv"
out.to_csv(out_file, index=False)
print("\nTop Pitcher Alt K Value Edges:\n")
print(f"{'Pitcher':20} {'Line':>5} {'Edge (%)':>10} {'Sim Odds':>10} {'Book Odds':>10} {'Sim Prob':>9} {'Book Prob':>9}")
for _, row in out.iterrows():
    sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
    book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
    edge = f"{row['Edge']:+.1f}%"
    line = f"{row[sim_pitch]:20} {str(row['K'])+'K':>5} {edge:>10} {sim_odds:>10} {book_odds:>10} {row['P_sim']:.3f} {row['P_book']:.3f}"
    print(line)
print(f"\nResults saved to {out_file}\n")


# Markdown Report
md_file = report_base + ".md"
with open(md_file, "w") as f:
    f.write("# Top Pitcher Alt K Value Edges\n\n")
    f.write("| {:20} | {:>5} | {:>10} | {:>10} | {:>10} | {:>9} | {:>9} |\n".format(
        "Pitcher", "Line", "Edge (%)", "Sim Odds", "Book Odds", "Sim Prob", "Book Prob"))
    f.write("|" + "-"*22 + "|" + "-"*7 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*11 + "|" + "-"*11 + "|\n")
    for _, row in out.iterrows():
        sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
        book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
        edge = f"{row['Edge']:+.1f}%"
        f.write("| {:20} | {:>5} | {:>10} | {:>10} | {:>10} | {:9.3f} | {:9.3f} |\n".format(
            row[sim_pitch], str(row['K'])+'K', edge, sim_odds, book_odds, row['P_sim'], row['P_book']))
    f.write("\n## Top 3 Edges Today\n\n")
    for _, row in out.head(3).iterrows():
        sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
        book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
        edge = f"{row['Edge']:+.1f}%"
        f.write(f"- **{row[sim_pitch]} {row['K']}K**: Sim Odds {sim_odds}, Book Odds {book_odds}, Edge {edge}\n")
print(f"Markdown report saved to {md_file}")


# HTML Report
html_file = report_base + ".html"
def format_odds(val):
    return f"{val:+.0f}" if val >= 0 else f"{val:.0f}"
def format_edge(val):
    return f"{val:+.1f}%"
out_html = out.copy()
out_html['Sim'] = out_html['Sim'].apply(format_odds)
out_html['Book'] = out_html['Book'].apply(format_odds)
out_html['Edge'] = out_html['Edge'].apply(format_edge)
with open(html_file, "w") as f:
    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset=\"utf-8\">
    <title>MLB Edge Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f8f9fa;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 900px;
            margin: 40px auto 0 auto;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 40px 30px 30px 30px;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 0.2em;
            font-weight: 700;
        }}
        .section-title {{
            text-align: center;
            color: #2c3e50;
            font-size: 1.2em;
            margin-bottom: 2em;
            border-bottom: 2px solid #1f77b4;
            padding-bottom: 0.5em;
            width: 60%;
            margin-left: auto;
            margin-right: auto;
        }}
        h2 {{
            text-align: center;
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 1em;
        }}
        table {{
            border-collapse: collapse;
            margin: 0 auto 30px auto;
            background: white;
            font-size: 1.1em;
            min-width: 700px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.07);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 16px;
            text-align: right;
        }}
        th {{
            background-color: #f8f9fa;
            color: #2c3e50;
            text-align: center;
            font-weight: 600;
        }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #eaf6ff; }}
        ul {{
            max-width: 600px;
            margin: 0 auto 2em auto;
            font-size: 1.1em;
        }}
        .summary {{
            text-align: center;
            margin-top: 30px;
            color: #555;
        }}
        .best-edges {{
            text-align: center;
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 1em;
        }}
    </style>
</head>
<body>
    <div class=\"container\">\n        <h1>MLB AI Report</h1>\n        <div class=\"section-title\">Date: {today}</div>\n        <h2>Pitcher Alternate Strikeout Edges</h2>\n        {out_html.to_html(index=False, float_format=None, border=0, columns=[sim_pitch, 'K', 'Edge', 'Sim', 'Book', 'P_sim', 'P_book'], header=[sim_pitch, 'K', 'Edge (%)', 'Sim', 'Book', 'P_sim', 'P_book'])}\n        <div class=\"best-edges\">Top 3 Plays Today</div>\n        <ul>\n""")
    for _, row in out.head(3).iterrows():
        sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
        book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
        edge = f"{row['Edge']:+.1f}%"
        f.write(f"<li><b>{row[sim_pitch]} {row['K']}K</b>: Sim Odds {sim_odds}, Book Odds {book_odds}, Edge {edge}</li>\n")
    f.write("""
        </ul>
        <div class="summary">
            Generated by MLB AI
        </div>
    </div>
</body>
</html>
""")
print(f"HTML report saved to {html_file}")


## TXT Report
#txt_file = report_base + ".txt"
#with open(txt_file, "w") as f:
#    f.write("Top Pitcher Alt K Value Edges\n\n")
#    f.write(f"{'Pitcher':20} {'Line':>5} {'Edge (%)':>10} {'Sim Odds':>10} {'Book Odds':>10} {'Sim Prob':>9} {'Book Prob':>9}\n")
#    f.write("-" * 80 + "\n")
#    for _, row in out.iterrows():
#        sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
#        book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
#        edge = f"{row['Edge']:+.1f}%"
#        f.write(f"{row[sim_pitch]:20} {str(row['K'])+'K':>5} {edge:>10} {sim_odds:>10} {book_odds:>10} {row['P_sim']:>9.3f} {row['P_book']:>9.3f}\n")
#    f.write("\nTop 3 Edges Today:\n")
#    for _, row in out.head(3).iterrows():
#        sim_odds = f"{row['Sim']:+.0f}" if row['Sim'] >= 0 else f"{row['Sim']:.0f}"
#        book_odds = f"{row['Book']:+.0f}" if row['Book'] >= 0 else f"{row['Book']:.0f}"
#        edge = f"{row['Edge']:+.1f}%"
#        f.write(f"- {row[sim_pitch]:20} {str(row['K'])+'K':>5}: Sim Odds {sim_odds}, Book Odds {book_odds}, Edge {edge}\n")
#print(f"Text report saved to {txt_file}")


## PDF Report
#try:
#    import matplotlib.pyplot as plt
#    from pandas.plotting import table as pd_table
#    pdf_file = report_base + ".pdf"
#    fig, ax = plt.subplots(figsize=(10, min(0.5+0.4*len(out), 12)))
#    ax.axis('off')
#    out_pdf = out.copy()
#    out_pdf['Sim'] = out_pdf['Sim'].apply(lambda x: f"{x:+.0f}" if x >= 0 else f"{x:.0f}")
#    out_pdf['Book'] = out_pdf['Book'].apply(lambda x: f"{x:+.0f}" if x >= 0 else f"{x:.0f}")
#    out_pdf['Edge'] = out_pdf['Edge'].apply(lambda x: f"{x:+.1f}%")
#    pd_table(ax, out_pdf.head(14), loc='center', colWidths=[0.13]*len(out.columns))  # Changed from 20 to 15
#    plt.title("Top Pitcher Alt K Value Edges", fontsize=14, weight='bold')
#    plt.savefig(pdf_file, bbox_inches='tight')
#    plt.close(fig)
#    print(f"PDF report saved to {pdf_file}")
#except Exception as e:
#    print(f"PDF report not created: {e}")