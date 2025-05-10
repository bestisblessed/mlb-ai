### Need to Get Per Game ###
- Lowest strikeout rate, highest hit percentages and the homer percent
- "If you can get the lowest k rate guys from each of the simulated games on ballpark and the highest hit rates and homer percent chance from all those sims"
- Batters and their matchup predictions


The basic simulation file (game_simulations.csv) lists one row per game with summary outcomes:
• game_id – Unique identifier for the game  
• away_team and home_team – Names of the competing teams  
• away_score and home_score – The simulation’s predicted scores (which can be fractional, suggesting expected run totals)  
• time – The scheduled game time  

In contrast, the detailed file (game_simulations_per_game_tables.csv) expands on the simulation by including in‐depth metrics for each game:
• Game basics (game_id, time, away_team, home_team)  
• Starting pitchers (starter_away, starter_home)  
• Predicted run totals (runs_away, runs_home)  
• Win probabilities for both sides (win_away, win_home) that include formatting with betting odds  
• Moneyline odds from specific sportsbooks (ml_away, ml_home)  
• First-5‑innings run predictions (f5_runs_away, f5_runs_home) and corresponding lead metrics (f5_lead_away, f5_lead_home)  
• A series of betting total values across different run thresholds (total_5_5 through total_12_5)  
• Over/under betting lines (under, over)  
• An additional metric labeled YRFI (with percentage and betting reference)  
• A flag for whether the lineups are final (lineups_final)

Thus, for each game, the summary file gives the predicted score and teams at a glance, while the detailed table provides extensive simulation parameters useful for deeper analysis or betting insights.






### STREAMLIT COLOR NOTES ###
Here are some MLB/baseball-themed color combinations you can use for your Streamlit app, inspired by classic MLB colors and the look of a baseball field, ball, and uniforms:

---

### **Classic MLB Red, White, and Blue**
- **Primary color:** `#003087` (MLB blue)
- **Background color:** `#FFFFFF` (white)
- **Text color:** `#222222` (almost black)
- **Secondary background color:** `#E31837` (MLB red)

---

### **Baseball Field Inspired**
- **Primary color:** `#2E8B57` (field green)
- **Background color:** `#F5F5DC` (baseball sand/cream)
- **Text color:** `#222222`
- **Secondary background color:** `#C0C0C0` (silver/bleachers)

---

### **Baseball Ball Inspired**
- **Primary color:** `#E31837` (stitching red)
- **Background color:** `#FFFFFF` (ball white)
- **Text color:** `#222222`
- **Secondary background color:** `#F5F5F5` (light gray)

---

### **Yankees Classic**
- **Primary color:** `#132448` (navy blue)
- **Background color:** `#FFFFFF`
- **Text color:** `#222222`
- **Secondary background color:** `#C4CED4` (gray)

---

### **Dodgers Blue**
- **Primary color:** `#005A9C`
- **Background color:** `#FFFFFF`
- **Text color:** `#222222`
- **Secondary background color:** `#E3E3E3`

---

### **Example for `.streamlit/config.toml` (MLB Red, White, Blue)**
```toml
[theme]
base="light"
primaryColor="#003087"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#E31837"
textColor="#222222"
font="serif"
```

---

**Tip:**  
- For a “night game” look, use a dark base and swap background/text colors.
- You can also use team-specific colors for a more custom feel!

Let me know if you want a config for a specific team or style!

