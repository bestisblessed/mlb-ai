## Endpoint: `attendance`
    ### URL: `https://statsapi.mlb.com/api/{ver}/attendance`
    ### Required Parameters
    * teamId
* leagueId
* leagueListid
    ### All Parameters
    * ver
* teamId
* leagueId
* season
* date
* leagueListId
* gameType
* fields
    -----
    ## Endpoint: `awards`
    ### URL: `https://statsapi.mlb.com/api/{ver}/awards{awardId}{recipients}`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* awardId
* recipients
* sportId
* leagueId
* season
* hydrate
* fields
    ### Note
    Call awards endpoint with no parameters to return a list of awardIds.
    -----
    ## Endpoint: `conferences`
    ### URL: `https://statsapi.mlb.com/api/{ver}/conferences`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* conferenceId
* season
* fields
    -----
    ## Endpoint: `divisions`
    ### URL: `https://statsapi.mlb.com/api/{ver}/divisions`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* divisionId
* leagueId
* sportId
* season
    ### Note
    Call divisions endpoint with no parameters to return a list of divisions.
    -----
    ## Endpoint: `draft`
    ### URL: `https://statsapi.mlb.com/api/{ver}/draft{prospects}{year}{latest}`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* prospects
* year
* latest
* limit
* fields
* round
* name
* school
* state
* country
* position
* teamId
* playerId
* bisPlayerId
    ### Note
    No query parameters are honored when "latest" endpoint is queried (year is still required). Prospects and Latest cannot be used together.
    -----
    ## Endpoint: `game`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/live`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* hydrate
* fields
    -----
    ## Endpoint: `game_diff`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/live/diffPatch`
    ### Required Parameters
    * gamePk
* startTimecode + endTimecode
    ### All Parameters
    * ver
* gamePk
* startTimecode
* endTimecode
    -----
    ## Endpoint: `game_timestamps`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/live/timestamps`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
    -----
    ## Endpoint: `game_changes`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/changes`
    ### Required Parameters
    * updatedSince
    ### All Parameters
    * ver
* updatedSince
* sportId
* gameType
* season
* fields
    -----
    ## Endpoint: `game_contextMetrics`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/contextMetrics`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    -----
    ## Endpoint: `game_winProbability`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/winProbability`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    ### Note
    If you only want the current win probability for each team, try the game_contextMetrics endpoint instad.
    -----
    ## Endpoint: `game_boxscore`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/boxscore`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    -----
    ## Endpoint: `game_content`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/content`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* highlightLimit
    -----
    ## Endpoint: `game_color`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/color`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    -----
    ## Endpoint: `game_color_diff`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/color/diffPatch`
    ### Required Parameters
    * gamePk
* startTimeCode + endTimeCode
    ### All Parameters
    * ver
* gamePk
* startTimecode
* endTimecode
    -----
    ## Endpoint: `game_color_timestamps`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/feed/color/timestamps`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
    -----
    ## Endpoint: `game_linescore`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/linescore`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    -----
    ## Endpoint: `game_playByPlay`
    ### URL: `https://statsapi.mlb.com/api/{ver}/game/{gamePk}/playByPlay`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* timecode
* fields
    -----
    ## Endpoint: `game_uniforms`
    ### URL: `https://statsapi.mlb.com/api/{ver}/uniforms/game`
    ### Required Parameters
    * gamePks
    ### All Parameters
    * ver
* gamePks
* fields
    -----
    ## Endpoint: `gamePace`
    ### URL: `https://statsapi.mlb.com/api/{ver}/gamePace`
    ### Required Parameters
    * season
    ### All Parameters
    * ver
* season
* teamIds
* leagueIds
* leagueListId
* sportId
* gameType
* startDate
* endDate
* venueIds
* orgType
* includeChildren
* fields
    -----
    ## Endpoint: `highLow`
    ### URL: `https://statsapi.mlb.com/api/{ver}/highLow/{orgType}`
    ### Required Parameters
    * orgType
* sortStat + season
    ### All Parameters
    * ver
* orgType
* statGroup
* sortStat
* season
* gameType
* teamId
* leagueId
* sportIds
* limit
* fields
    ### Note
    Valid values for orgType parameter: player, team, division, league, sport, types.
    -----
    ## Endpoint: `homeRunDerby`
    ### URL: `https://statsapi.mlb.com/api/{ver}/homeRunDerby/{gamePk}{bracket}{pool}`
    ### Required Parameters
    * gamePk
    ### All Parameters
    * ver
* gamePk
* bracket
* pool
* fields
    -----
    ## Endpoint: `league`
    ### URL: `https://statsapi.mlb.com/api/{ver}/league`
    ### Required Parameters
    * sportId
* leagueIds
    ### All Parameters
    * ver
* sportId
* leagueIds
* seasons
* fields
    -----
    ## Endpoint: `league_allStarBallot`
    ### URL: `https://statsapi.mlb.com/api/{ver}/league/{leagueId}/allStarBallot`
    ### Required Parameters
    * leagueId
* season
    ### All Parameters
    * ver
* leagueId
* season
* fields
    -----
    ## Endpoint: `league_allStarWriteIns`
    ### URL: `https://statsapi.mlb.com/api/{ver}/league/{leagueId}/allStarWriteIns`
    ### Required Parameters
    * leagueId
* season
    ### All Parameters
    * ver
* leagueId
* season
* fields
    -----
    ## Endpoint: `league_allStarFinalVote`
    ### URL: `https://statsapi.mlb.com/api/{ver}/league/{leagueId}/allStarFinalVote`
    ### Required Parameters
    * leagueId
* season
    ### All Parameters
    * ver
* leagueId
* season
* fields
    -----
    ## Endpoint: `people`
    ### URL: `https://statsapi.mlb.com/api/{ver}/people`
    ### Required Parameters
    * personIds
    ### All Parameters
    * ver
* personIds
* hydrate
* fields
    -----
    ## Endpoint: `people_changes`
    ### URL: `https://statsapi.mlb.com/api/{ver}/people/changes`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* updatedSince
* fields
    -----
    ## Endpoint: `people_freeAgents`
    ### URL: `https://statsapi.mlb.com/api/{ver}/people/freeAgents`
    ### Required Parameters
    * leagueId
    ### All Parameters
    * ver
* leagueId
* order
* hydrate
* fields
    -----
    ## Endpoint: `person`
    ### URL: `https://statsapi.mlb.com/api/{ver}/people/{personId}`
    ### Required Parameters
    * personId
    ### All Parameters
    * ver
* personId
* hydrate
* fields
    -----
    ## Endpoint: `person_stats`
    ### URL: `https://statsapi.mlb.com/api/{ver}/people/{personId}/stats/game/{gamePk}`
    ### Required Parameters
    * personId
* gamePk
    ### All Parameters
    * ver
* personId
* gamePk
* fields
    ### Note
    Specify "current" instead of a gamePk for a player's current game stats.
    -----
    ## Endpoint: `jobs`
    ### URL: `https://statsapi.mlb.com/api/{ver}/jobs`
    ### Required Parameters
    * jobType
    ### All Parameters
    * ver
* jobType
* sportId
* date
* fields
    -----
    ## Endpoint: `jobs_umpires`
    ### URL: `https://statsapi.mlb.com/api/{ver}/jobs/umpires`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* sportId
* date
* fields
    -----
    ## Endpoint: `jobs_umpire_games`
    ### URL: `https://statsapi.mlb.com/api/{ver}/jobs/umpires/games/{umpireId}`
    ### Required Parameters
    * umpireId
* season
    ### All Parameters
    * ver
* umpireId
* season
* fields
    -----
    ## Endpoint: `jobs_datacasters`
    ### URL: `https://statsapi.mlb.com/api/{ver}/jobs/datacasters`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* sportId
* date
* fields
    -----
    ## Endpoint: `jobs_officialScorers`
    ### URL: `https://statsapi.mlb.com/api/{ver}/jobs/officialScorers`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* timecode
* fields
    -----
    ## Endpoint: `schedule`
    ### URL: `https://statsapi.mlb.com/api/{ver}/schedule`
    ### Required Parameters
    * sportId
* gamePk
* gamePks
    ### All Parameters
    * ver
* scheduleType
* eventTypes
* hydrate
* teamId
* leagueId
* sportId
* gamePk
* gamePks
* venueIds
* gameTypes
* date
* startDate
* endDate
* opponentId
* fields
* season
    -----
    ## Endpoint: `schedule_tied`
    ### URL: `https://statsapi.mlb.com/api/{ver}/schedule/games/tied`
    ### Required Parameters
    * season
    ### All Parameters
    * ver
* gameTypes
* season
* hydrate
* fields
    -----
    ## Endpoint: `schedule_postseason`
    ### URL: `https://statsapi.mlb.com/api/{ver}/schedule/postseason`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* gameTypes
* seriesNumber
* teamId
* sportId
* season
* hydrate
* fields
    -----
    ## Endpoint: `schedule_postseason_series`
    ### URL: `https://statsapi.mlb.com/api/{ver}/schedule/postseason/series`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* gameTypes
* seriesNumber
* teamId
* sportId
* season
* fields
    -----
    ## Endpoint: `schedule_postseason_tuneIn`
    ### URL: `https://statsapi.mlb.com/api/{ver}/schedule/postseason/tuneIn`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* teamId
* sportId
* season
* hydrate
* fields
    ### Note
    The schedule_postseason_tuneIn endpoint appears to return no data.
    -----
    ## Endpoint: `seasons`
    ### URL: `https://statsapi.mlb.com/api/{ver}/seasons{all}`
    ### Required Parameters
    * sportId
* divisionId
* leagueId
    ### All Parameters
    * ver
* all
* season
* sportId
* divisionId
* leagueId
* fields
    ### Note
    Include "all" parameter with value of True to query all seasons. The divisionId and leagueId parameters are supported when "all" is used.
    -----
    ## Endpoint: `season`
    ### URL: `https://statsapi.mlb.com/api/{ver}/seasons/{seasonId}`
    ### Required Parameters
    * seasonId
* sportId
    ### All Parameters
    * ver
* seasonId
* sportId
* fields
    -----
    ## Endpoint: `sports`
    ### URL: `https://statsapi.mlb.com/api/{ver}/sports`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* sportId
* fields
    -----
    ## Endpoint: `sports_players`
    ### URL: `https://statsapi.mlb.com/api/{ver}/sports/{sportId}/players`
    ### Required Parameters
    * sportId
* season
    ### All Parameters
    * ver
* sportId
* season
* gameType
* fields
    -----
    ## Endpoint: `standings`
    ### URL: `https://statsapi.mlb.com/api/{ver}/standings`
    ### Required Parameters
    * leagueId
    ### All Parameters
    * ver
* leagueId
* season
* standingsTypes
* date
* hydrate
* fields
    -----
    ## Endpoint: `stats`
    ### URL: `https://statsapi.mlb.com/api/{ver}/stats`
    ### Required Parameters
    * stats + group
    ### All Parameters
    * ver
* stats
* playerPool
* position
* teamId
* leagueId
* limit
* offset
* group
* gameType
* season
* sportIds
* sortStat
* order
* hydrate
* fields
* personId
* metrics
* startDate
* endDate
    ### Note
    If no limit is specified, the response will be limited to 50 records.
    -----
    ## Endpoint: `stats_leaders`
    ### URL: `https://statsapi.mlb.com/api/{ver}/stats/leaders`
    ### Required Parameters
    * leaderCategories
    ### All Parameters
    * ver
* leaderCategories
* playerPool
* leaderGameTypes
* statGroup
* season
* leagueId
* sportId
* hydrate
* limit
* fields
* statType
    ### Note
    If excluding season parameter to get all time leaders, include statType=statsSingleSeason or you will likely not get any results.
    -----
    ## Endpoint: `stats_streaks`
    ### URL: `https://statsapi.mlb.com/api/{ver}/stats/streaks`
    ### Required Parameters
    * streakType + streakSpan + season + sportId + limit
    ### All Parameters
    * ver
* streakType
* streakSpan
* gameType
* season
* sportId
* limit
* hydrate
* fields
    ### Note
    Valid streakType values: "hittingStreakOverall" "hittingStreakHome" "hittingStreakAway" "onBaseOverall" "onBaseHome" "onBaseAway". Valid streakSpan values: "career" "season" "currentStreak" "currentStreakInSeason" "notable" "notableInSeason".
    -----
    ## Endpoint: `teams`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams`
    ### Required Parameters
    * *None*
    ### All Parameters
    * ver
* season
* activeStatus
* leagueIds
* sportId
* sportIds
* gameType
* hydrate
* fields
    -----
    ## Endpoint: `teams_history`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/history`
    ### Required Parameters
    * teamIds
    ### All Parameters
    * ver
* teamIds
* startSeason
* endSeason
* fields
    -----
    ## Endpoint: `teams_stats`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/stats`
    ### Required Parameters
    * season + group + stats
    ### All Parameters
    * ver
* season
* sportIds
* group
* gameType
* stats
* order
* sortStat
* fields
* startDate
* endDate
    ### Note
    Use meta('statGroups') to look up valid values for group, and meta('statTypes') for valid values for stats.
    -----
    ## Endpoint: `teams_affiliates`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/affiliates`
    ### Required Parameters
    * teamIds
    ### All Parameters
    * ver
* teamIds
* sportId
* season
* hydrate
* fields
    -----
    ## Endpoint: `team`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}`
    ### Required Parameters
    * teamId
    ### All Parameters
    * ver
* teamId
* season
* sportId
* hydrate
* fields
    -----
    ## Endpoint: `team_alumni`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/alumni`
    ### Required Parameters
    * teamId
* season + group
    ### All Parameters
    * ver
* teamId
* season
* group
* hydrate
* fields
    -----
    ## Endpoint: `team_coaches`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/coaches`
    ### Required Parameters
    * teamId
    ### All Parameters
    * ver
* teamId
* season
* date
* fields
    -----
    ## Endpoint: `team_personnel`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/personnel`
    ### Required Parameters
    * teamId
    ### All Parameters
    * ver
* teamId
* date
* fields
    -----
    ## Endpoint: `team_leaders`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/leaders`
    ### Required Parameters
    * teamId
* leaderCategories + season
    ### All Parameters
    * ver
* teamId
* leaderCategories
* season
* leaderGameTypes
* hydrate
* limit
* fields
    -----
    ## Endpoint: `team_roster`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/roster`
    ### Required Parameters
    * teamId
    ### All Parameters
    * ver
* teamId
* rosterType
* season
* date
* hydrate
* fields
    -----
    ## Endpoint: `team_stats`
    ### URL: `https://statsapi.mlb.com/api/{ver}/teams/{teamId}/stats`
    ### Required Parameters
    * teamId
* season + group
    ### All Parameters
    * ver
* teamId
* season
* group
* gameType
* stats
* sportIds
* sitCodes
* fields
    ### Note
    Use meta('statGroups') to look up valid values for group, meta('statTypes') for valid values for stats, and meta('situationCodes') for valid values for sitCodes. Use sitCodes with stats=statSplits.
    -----
    ## Endpoint: `team_uniforms`
    ### URL: `https://statsapi.mlb.com/api/{ver}/uniforms/team`
    ### Required Parameters
    * teamIds
    ### All Parameters
    * ver
* teamIds
* season
* fields
    -----
    ## Endpoint: `transactions`
    ### URL: `https://statsapi.mlb.com/api/{ver}/transactions`
    ### Required Parameters
    * teamId
* playerId
* date
* startDate + endDate
    ### All Parameters
    * ver
* teamId
* playerId
* date
* startDate
* endDate
* sportId
* fields
    -----
    ## Endpoint: `venue`
    ### URL: `https://statsapi.mlb.com/api/{ver}/venues`
    ### Required Parameters
    * venueIds
    ### All Parameters
    * ver
* venueIds
* season
* hydrate
* fields
    -----
    ## Endpoint: `meta`
    ### URL: `https://statsapi.mlb.com/api/{ver}/{type}`
    ### Required Parameters
    * type
    ### All Parameters
    * ver
* type
    ### Note
    The meta endpoint is used to retrieve values to be used within other API calls. Available types: awards, baseballStats, eventTypes, gameStatus, gameTypes, hitTrajectories, jobTypes, languages, leagueLeaderTypes, logicalEvents, metrics, pitchCodes, pitchTypes, platforms, positions, reviewReasons, rosterTypes, scheduleEventTypes, situationCodes, sky, standingsTypes, statGroups, statTypes, windDirection.
    -----
    