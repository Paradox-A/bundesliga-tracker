#!/bin/bash
# Requires FOOTBALL_DATA_API_TOKEN env var set (free key from football-data.org)
set -e

fetch() {
  # $1 = output file, rest = curl args (URL, headers, etc.)
  local out="$1"; shift
  curl -s "$@" -o "$out"
  if grep -q '"errorCode"' "$out" 2>/dev/null; then
    echo "ERROR: fetch failed for $out — $(cat "$out")" >&2
    exit 1
  fi
  sleep 7
}

fetch standings.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/standings"
fetch matches.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/matches"
fetch scorers.json -H "X-Auth-Token: $FOOTBALL_DATA_API_TOKEN" "https://api.football-data.org/v4/competitions/BL1/scorers?limit=50"

# Bundesliga's own public backend — real yellow cards, assists, goals, and goalkeeper
# shots-saved data. No API key needed. Season ID DFL-SEA-0001KA is the 2026-27 season;
# will need updating once that season concludes and a new one begins.
fetch bl_goals.json "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/shotsAtGoalSuccessful.json"
fetch bl_assists.json "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/assists.json"
fetch bl_yellow.json "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/cardsYellow.json"
fetch bl_saves.json "https://wapp.bapi.bundesliga.com/all/DFL-COM-000001/seasons/DFL-SEA-0001KA/stats/playerRankings/goalkeeperSaves.json"

python3 build_site.py
echo "Rebuilt site/index.html"
