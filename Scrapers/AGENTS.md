# AGENTS.md – Guide for Future Automation Agents

### Introduction
This project maintains automated scrapers that pull MLB roster information.

---

### CSV Schema
Both CSVs share exactly the same column layout.  The only difference is logical: the "pitchers" file contains rows where `Position == "P"`, while the "hitters" file contains everyone else.

# pitchers_with_game_logs.csv (mlb savant)
Name - Player's full name from the MLB roster.
Player URL - Link to the player's MLB.com profile.
Jersey Number - Depth-chart uniform number (blank if not listed).
Status - Current roster status from the depth-chart.
B/T - Bats/Throws handedness abbreviation.
Height - Height string as it appears on MLB.
Weight - Weight in pounds as a string.
DOB - Date of birth in `MM/DD/YYYY` format.
Team - Friendly team name from the depth-chart filename.
Player ID - Numeric MLB player identifier (used by Baseball Savant and StatsAPI).
Position - Primary position abbreviation from the player header.
Game Log URL - Link to the player's current-season game-log tab.

# hitters_with_game_logs.csv (mlb savant)
Name - Player's full name from the MLB roster.
Player URL - Link to the player's MLB.com profile.
Jersey Number - Depth-chart uniform number (blank if not listed).
Status - Current roster status from the depth-chart.
B/T - Bats/Throws handedness abbreviation.
Height - Height string as it appears on MLB.
Weight - Weight in pounds as a string.
DOB - Date of birth in `MM/DD/YYYY` format.
Team - Friendly team name from the depth-chart filename.
Player ID - Numeric MLB player identifier (used by Baseball Savant and StatsAPI).
Position - Primary position abbreviation from the player header.
Game Log URL - Link to the player's current-season game-log tab.

# batters_details_2025_statsapi.csv (statsapi)
player_id, id, fullName, link, firstName, lastName, primaryNumber, birthDate, currentAge, birthCity, birthStateProvince, birthCountry, height, weight, active, primaryPosition, useName, useLastName, middleName, boxscoreName, gender, isPlayer, isVerified, draftYear, mlbDebutDate, batSide, pitchHand, nameFirstLast, nameSlug, firstLastName, lastFirstName, lastInitName, initLastName, fullFMLName, fullLFMName, strikeZoneTop, strikeZoneBottom, pronunciation, nameTitle, nameSuffix, nickName, nameMatrilineal

# pitchers_details_2025_statsapi.csv (statsapi)
player_id, id, fullName, link, firstName, lastName, primaryNumber, birthDate, currentAge, birthCity, birthCountry, height, weight, active, primaryPosition, useName, useLastName, middleName, boxscoreName, gender, nameMatrilineal, isPlayer, isVerified, pronunciation, mlbDebutDate, batSide, pitchHand, nameFirstLast, nameSlug, firstLastName, lastFirstName, lastInitName, initLastName, fullFMLName, fullLFMName, strikeZoneTop, strikeZoneBottom, birthStateProvince, draftYear, nickName, nameTitle, nameSuffix

# batters_gamelogs_2025_statsapi.csv (statsapi)
player_id, date, team, opponent, summary, gamesPlayed, flyOuts, groundOuts, airOuts, runs, doubles, triples, homeRuns, strikeOuts, baseOnBalls, intentionalWalks, hits, hitByPitch, avg, atBats, obp, slg, ops, caughtStealing, stolenBases, stolenBasePercentage, groundIntoDoublePlay, groundIntoTriplePlay, numberOfPitches, plateAppearances, totalBases, rbi, leftOnBase, sacBunts, sacFlies, babip, groundOutsToAirouts, catchersInterference, atBatsPerHomeRun

# pitchers_gamelogs_2025_statsapi.csv (statsapi)
player_id, date, team, opponent, summary, gamesPlayed, gamesStarted, flyOuts, groundOuts, airOuts, runs, doubles, triples, homeRuns, strikeOuts, baseOnBalls, intentionalWalks, hits, hitByPitch, avg, atBats, obp, slg, ops, caughtStealing, stolenBases, stolenBasePercentage, groundIntoDoublePlay, numberOfPitches, era, inningsPitched, wins, losses, saves, saveOpportunities, holds, blownSaves, earnedRuns, whip, battersFaced, outs, gamesPitched, completeGames, shutouts, strikes, strikePercentage, hitBatsmen, balks, wildPitches, pickoffs, totalBases, groundOutsToAirouts, winPercentage, pitchesPerInning, gamesFinished, strikeoutWalkRatio, strikeoutsPer9Inn, walksPer9Inn, hitsPer9Inn, runsScoredPer9, homeRunsPer9, inheritedRunners, inheritedRunnersScored, catchersInterference, sacBunts, sacFlies

---

### Quick-Start Tips for Agents
1. **Player lookup** – Need Baseball Savant?  Build the URL using:<br>`https://baseballsavant.mlb.com/savant-player/{Player ID}` (append query params as needed).
2. **Injury filtering** – To ignore injured players, filter rows where `Status` is not null.
3. **Speed over completeness** – `mlb_savant_scraper_faster.py` uses StatsAPI for positions first; it's ~10× quicker than the pure-browser fallback.
4. **Season awareness** – `Game Log URL` is templated for the year the scraper was run.  If you open logs in a new season, regenerate the CSVs.
5. **Re-parsing logs only** – All raw HTML is stored under:
   * Hitters → `data/mlb/raw_player_game_logs_hitters/`
   * Pitchers → `data/mlb/raw_player_game_logs_pitchers/`
   You can re-run just the parsers via `_parse_game_logs()` without re-scraping.

> **Need more data?** Combine these roster CSVs with the raw/player-level Savant HTML (in `data/mlb/savant/`) or call the MLB StatsAPI directly using the `Player ID` column.

---
Happy hacking! 