import pandas as pd

df_list = pd.read_html("data/Pitchers.html")

# Find Table
for t in df_list:
    if {"Pitcher", "0", "10+"}.issubset(t.columns):
        df = t.copy()
        break

# Get Ladder Probs
prob_cols = [str(i) for i in range(10)] + ["10+"]
for k in range(4, 11):
    df[f"{k}plus"] = df[[c for c in prob_cols if int(c.rstrip('+')) >= k]].sum(axis=1)

# Calculate Money Line (no-vig)
for k in range(4, 11):
    df[f"{k}plus_odds"] = df[f"{k}plus"].apply(
        lambda p: None if p == 0 else -round(p/(1-p)*100) if p >= 0.5 else round((1-p)/p*100)
    )

# View/Save
cols = ["Pitcher"] + [f"{k}plus_odds" for k in range(4, 11)]
print(df[cols].head())
df[cols].to_csv("fair_ladder_odds.csv", index=False)
