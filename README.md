# Bundesliga 2026-27 Tracker

A static tracker for the Bundesliga (Germany's top flight), mirroring the Premier League tracker, with three tabs:
- **League Table**: full standings, color-coded by European qualification zone (Champions League, Europa League, Conference League), the relegation play-off spot (16th), and automatic relegation (17th-18th), plus a "European Race" view of the top 8 and a "Relegation Watch" view of what each bottom-table team needs to reach safety.
- **Club Stats**: clean sheets, home/away form splits, biggest wins & heaviest losses — all derived from match results.
- **Player Stats**: Top Scorer race, plus expandable lists for Most Goals, Most Assists, Most Yellow Cards, and Most Shots Saved (goalkeepers).

## Data sources
- [football-data.org](https://www.football-data.org/) free API (Bundesliga competition code `BL1`) — standings, matches, goals/penalties.
- **bundesliga.com's own public backend** (`wapp.bapi.bundesliga.com`) — real goals, assists, yellow cards, and goalkeeper shots-saved data, keyed by DFL's own competition/season IDs (`DFL-COM-000001` / `DFL-SEA-0001KA` for 2026-27). No API key needed, and each player record includes a direct club crest URL, so no cross-source team-name matching is needed (unlike the LaLiga tracker). No dedicated Red Cards ranking or individual clean-sheet stat is published on their site, so those aren't included.

**Note on season IDs**: `DFL-SEA-0001KA` is hardcoded in `fetch_data.sh` for the 2026-27 season. It'll need updating to a new season ID once 2026-27 concludes — check the season dropdown on bundesliga.com's stats page and inspect the URL/network requests to find the new ID the same way this one was discovered.

## Regenerating

```bash
export FOOTBALL_DATA_API_TOKEN=your_token_here
./fetch_data.sh
git add index.html
git commit -m "Refresh standings"
git push
```

Not live-updating — rebuild after each matchday (or whenever) to refresh the table. The 2026-27 season starts August 28, 2026 — until then, standings show all-zero rows and player stat sections will be empty.
