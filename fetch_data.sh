#!/bin/bash
# Requires FOOTBALL_DATA_API_TOKEN env var set (free key from football-data.org)
set -e
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/standings" -o standings.json
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/matches" -o matches.json
curl -s -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/scorers?limit=50" -o scorers.json

# Bundesliga's own public backend — real yellow cards, assists, goals, and goalkeeper
# shots-saved data. No API key needed. Season ID DFL-SEA-0001KA is the 2026-27 season;
# will need updating once that season concludes and a new one begins.
curl -s "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/shotsAtGoalSuccessful.json" -o bl_goals.json
curl -s "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/assists.json" -o bl_assists.json
curl -s "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/cardsYellow.json" -o bl_yellow.json
curl -s "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/goalkeeperSaves.json" -o bl_saves.json

python3 build_site.py
echo "Rebuilt site/index.html"
