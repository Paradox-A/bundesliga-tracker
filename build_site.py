import json
import os
from datetime import datetime, timezone
from collections import defaultdict

API_TOKEN = os.environ.get("FOOTBALL_DATA_API_TOKEN")
STANDINGS_PATH = "standings.json"
MATCHES_PATH = "matches.json"
SCORERS_PATH = "scorers.json"
BL_GOALS_PATH = "bl_goals.json"
BL_ASSISTS_PATH = "bl_assists.json"
BL_YELLOW_PATH = "bl_yellow.json"
BL_SAVES_PATH = "bl_saves.json"
OUT_PATH = "index.html"

SAFETY_THRESHOLD = 34
TOTAL_GAMES = 34

standings_data = json.load(open(STANDINGS_PATH))
table = standings_data["standings"][0]["table"]
season = standings_data["season"]
matchday = season["currentMatchday"]
table = sorted(table, key=lambda t: (t["position"], -t["points"], -t["goalDifference"]))
# football-data.org reports every team at position=1 before the season starts (no real
# ranking exists yet) — use sort order for display rank instead of trusting that field.
for i, t in enumerate(table, start=1):
    t["displayPos"] = i

matches_data = json.load(open(MATCHES_PATH))
finished = [m for m in matches_data["matches"] if m["status"] == "FINISHED"]

scorers_data = json.load(open(SCORERS_PATH))
scorers = scorers_data["scorers"]

def load_bl_stat(path):
    data = json.load(open(path))
    return data or {}

bl_goals = load_bl_stat(BL_GOALS_PATH)
bl_assists = load_bl_stat(BL_ASSISTS_PATH)
bl_yellow = load_bl_stat(BL_YELLOW_PATH)
bl_saves = load_bl_stat(BL_SAVES_PATH)

def zone_for(pos):
    if pos <= 4:
        return ("cl", "Champions League")
    if pos == 5:
        return ("el", "Europa League")
    if pos == 6:
        return ("ecl", "Conference League")
    if pos == 16:
        return ("relp", "Relegation Play-off")
    if pos >= 17:
        return ("rel", "Relegation")
    return ("", "")

# ---------- League table rows ----------
rows_html = []
for t in table:
    pos = t["displayPos"]
    zone_class, _ = zone_for(pos)
    played = t["playedGames"]
    pts = t["points"]
    gd = t["goalDifference"]
    gd_str = f"+{gd}" if gd > 0 else str(gd)
    form = t.get("form") or "—"
    rows_html.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{played}</td><td>{t['won']}</td><td>{t['draw']}</td><td>{t['lost']}</td>
      <td>{t['goalsFor']}</td><td>{t['goalsAgainst']}</td><td>{gd_str}</td>
      <td class="pts">{pts}</td><td class="form">{form}</td>
    </tr>""")

euro_zone = [t for t in table if t["displayPos"] <= 8]
euro_rows = []
fourth = table[3]["points"]
for t in euro_zone:
    pos = t["displayPos"]
    zone_class, zone_label = zone_for(pos)
    label = zone_label if zone_label else "Chasing pack"
    remaining = TOTAL_GAMES - t["playedGames"]
    gap = fourth - t["points"]
    euro_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{label}</td><td>{t['points']}</td><td>{remaining}</td>
      <td>{'—' if pos <= 4 else (f'{gap} pt behind 4th' if gap > 0 else 'Level with 4th')}</td>
    </tr>""")

rel_zone = sorted(table, key=lambda t: t["displayPos"])[-6:]
rel_rows = []
for t in rel_zone:
    pos = t["displayPos"]
    remaining = TOTAL_GAMES - t["playedGames"]
    pts = t["points"]
    pts_needed = max(SAFETY_THRESHOLD - pts, 0)
    ppg_needed = (pts_needed / remaining) if remaining > 0 else float('inf')
    if remaining == 0 and pts < SAFETY_THRESHOLD:
        verdict = "Relegated (out of games)"
    elif ppg_needed <= 0:
        verdict = "Already past safety benchmark"
    elif ppg_needed <= 1.0:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game pace)"
    elif ppg_needed <= 1.8:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game — above league-average pace)"
    else:
        verdict = f"Needs {pts_needed} pts from {remaining} games ({ppg_needed:.2f} pts/game — steep, needs a big turnaround)"
    zone_class, _ = zone_for(pos)
    rel_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{pts}</td><td>{remaining}</td><td>{verdict}</td>
    </tr>""")

# ---------- Club stats derived from finished matches ----------
club = defaultdict(lambda: {
    "name": None, "crest": None, "gf": 0, "ga": 0, "clean_sheets": 0, "failed_to_score": 0,
    "home_pts": 0, "home_played": 0, "away_pts": 0, "away_played": 0,
    "results": [],  # chronological list of 'W'/'D'/'L'
    "biggest_win": None, "heaviest_loss": None,
})

finished_sorted = sorted(finished, key=lambda m: m["utcDate"])
for m in finished_sorted:
    home = m["homeTeam"]; away = m["awayTeam"]
    hs = m["score"]["fullTime"]["home"]; as_ = m["score"]["fullTime"]["away"]
    for side, opp_side, gf, ga, is_home in [(home, away, hs, as_, True), (away, home, as_, hs, False)]:
        c = club[side["id"]]
        c["name"] = side["shortName"]; c["crest"] = side["crest"]
        c["gf"] += gf; c["ga"] += ga
        if ga == 0:
            c["clean_sheets"] += 1
        if gf == 0:
            c["failed_to_score"] += 1
        margin = gf - ga
        result = "W" if margin > 0 else ("D" if margin == 0 else "L")
        c["results"].append(result)
        pts = 3 if result == "W" else (1 if result == "D" else 0)
        if is_home:
            c["home_pts"] += pts; c["home_played"] += 1
        else:
            c["away_pts"] += pts; c["away_played"] += 1
        if result == "W":
            if c["biggest_win"] is None or margin > c["biggest_win"][0]:
                c["biggest_win"] = (margin, f"{gf}-{ga} vs {opp_side['shortName']}")
        if result == "L":
            deficit = ga - gf
            if c["heaviest_loss"] is None or deficit > c["heaviest_loss"][0]:
                c["heaviest_loss"] = (deficit, f"{gf}-{ga} vs {opp_side['shortName']}")

clean_sheet_rows = []
for cid, c in sorted(club.items(), key=lambda kv: (-kv[1]["clean_sheets"], kv[1]["ga"])):
    played = len(c["results"])
    if played == 0:
        continue
    clean_sheet_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{played}</td><td>{c['clean_sheets']}</td>
      <td>{c['ga']/played:.2f}</td><td>{c['failed_to_score']}</td>
    </tr>""")

form_home_away_rows = []
for cid, c in sorted(club.items(), key=lambda kv: -( (kv[1]["home_pts"]+kv[1]["away_pts"]) )):
    played = len(c["results"])
    if played == 0:
        continue
    last5 = "".join(c["results"][-5:])
    home_ppg = (c["home_pts"]/c["home_played"]) if c["home_played"] else 0
    away_ppg = (c["away_pts"]/c["away_played"]) if c["away_played"] else 0
    form_home_away_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{last5 or '—'}</td>
      <td>{c['home_pts']}pts / {c['home_played']}g ({home_ppg:.2f}/g)</td>
      <td>{c['away_pts']}pts / {c['away_played']}g ({away_ppg:.2f}/g)</td>
    </tr>""")

biggest_wins = sorted([ (c["biggest_win"][0], c["name"], c["biggest_win"][1]) for c in club.values() if c["biggest_win"]], reverse=True)[:5]
heaviest_losses = sorted([ (c["heaviest_loss"][0], c["name"], c["heaviest_loss"][1]) for c in club.values() if c["heaviest_loss"]], reverse=True)[:5]
biggest_win_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in biggest_wins) or "<tr><td colspan='2'>Not enough results yet</td></tr>"
heaviest_loss_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in heaviest_losses) or "<tr><td colspan='2'>Not enough results yet</td></tr>"

# ---------- Player stats: combined table from football-data scorers ----------
def player_row(s, highlight_field):
    goals = s.get("goals") or 0
    assists_raw = s.get("assists")
    assists = assists_raw or 0
    pens_raw = s.get("penalties")
    pens = pens_raw or 0
    played = s.get("playedMatches") or 0
    involvements = goals + assists
    per_game = (goals/played) if played else 0
    cls = lambda f: "pts" if f == highlight_field else ""
    return f"""
    <tr>
      <td class="team"><img src="{s['team']['crest']}" alt="" class="crest"> {s['player']['name']}</td>
      <td>{s['team']['shortName']}</td>
      <td>{played}</td>
      <td class="{cls('goals')}">{goals}</td>
      <td class="{cls('assists')}">{assists if assists_raw is not None else '—'}</td>
      <td class="{cls('inv')}">{involvements}</td>
      <td>{pens if pens_raw is not None else '—'}</td>
      <td>{per_game:.2f}</td>
    </tr>"""

by_goals = sorted(scorers, key=lambda s: (-(s.get("goals") or 0), -(s.get("assists") or 0)))
by_involvements = sorted(scorers, key=lambda s: (-((s.get("goals") or 0) + (s.get("assists") or 0))))

goals_rows = "".join(player_row(s, "goals") for s in by_goals)
involvements_rows = "".join(player_row(s, "inv") for s in by_involvements)

PLAYER_TABLE_HEAD = """<thead><tr><th class="team">Player</th><th>Club</th><th>Games</th><th>Goals</th><th>Assists</th><th>Goal Inv.</th><th>Pens</th><th>Goals/Game</th></tr></thead>"""

no_scorer_data_note = "" if scorers else """<div class="note">⚠ No scorer data yet — the 2026-27 season hasn't kicked off. This table will populate once matches are played and the site is refreshed.</div>"""

# ---------- Single-stat lists from bundesliga.com's own site (real data, no clean sheets/red cards available) ----------
def bl_stat_table_head(label):
    return f"""<thead><tr><th class="team">Player</th><th>Club</th><th>{label}</th></tr></thead>"""

def bl_stat_rows(stat_dict, limit=15):
    players = sorted(stat_dict.values(), key=lambda p: -(p.get("value") or 0))[:limit]
    if not players:
        return "<tr><td colspan=3>No data yet — season hasn't started</td></tr>"
    rows = []
    for p in players:
        crest = p.get("club", {}).get("logoUrl", "")
        crest_html = f'<img src="{crest}" alt="" class="crest">' if crest else ""
        rows.append(f"""
        <tr>
          <td class="team">{crest_html}{p['name']}</td>
          <td>{p.get('club', {}).get('dflDatalibraryClubId', '')}</td>
          <td class="pts">{int(p.get('value') or 0)}</td>
        </tr>""")
    return "".join(rows)

GOALS_TABLE_HEAD = bl_stat_table_head("Goals")
ASSISTS_TABLE_HEAD = bl_stat_table_head("Assists")
YELLOW_TABLE_HEAD = bl_stat_table_head("Yellow Cards")
SAVES_TABLE_HEAD = bl_stat_table_head("Shots Saved")

bl_goals_rows = bl_stat_rows(bl_goals)
bl_assists_rows = bl_stat_rows(bl_assists)
bl_yellow_rows = bl_stat_rows(bl_yellow)
bl_saves_rows = bl_stat_rows(bl_saves)

season_not_started_note = "" if finished else """<div class="note">⚠ The 2026-27 Bundesliga season hasn't kicked off yet (first matchday is August 28, 2026) — these sections will fill in once matches are played and the site is refreshed.</div>"""

updated = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bundesliga 2026-27 Tracker</title>
<style>
  :root {{
    --bg: #f6f1e7; --card: #ffffff; --text: #1a1a1a; --muted: #6b6b6b; --border: #e2ddd0;
    --cl: #d6f5d6; --cl-text: #1a6b1a; --el: #d6e8ff; --el-text: #1a4a8a;
    --ecl: #e0d6ff; --ecl-text: #4a1a8a; --relp: #ffe9c2; --relp-text: #8a5a1a;
    --rel: #ffd6d6; --rel-text: #8a1a1a;
    --accent: #d3010c; --tab-bg: #eee6d6; --tab-active: #d3010c; --tab-active-text: #ffffff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
      --cl: #143d14; --cl-text: #8fe08f; --el: #143355; --el-text: #9cc4f5;
      --ecl: #2e1a55; --ecl-text: #c9b3f5; --relp: #4a3410; --relp-text: #f5c98a;
      --rel: #551a1a; --rel-text: #f5a3a3;
      --accent: #ff5a63; --tab-bg: #2a2534; --tab-active: #ff5a63; --tab-active-text: #16131a;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
    --cl: #143d14; --cl-text: #8fe08f; --el: #143355; --el-text: #9cc4f5;
    --ecl: #2e1a55; --ecl-text: #c9b3f5; --relp: #4a3410; --relp-text: #f5c98a;
    --rel: #551a1a; --rel-text: #f5a3a3;
    --accent: #ff5a63; --tab-bg: #2a2534; --tab-active: #ff5a63; --tab-active-text: #16131a;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px 16px 60px; }}
  .wrap {{ max-width: 940px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: var(--accent); }}
  .updated {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 18px; }}
  .dash-link {{ margin-bottom: 10px; }}
  .dash-link a {{ color: var(--muted); font-size: 0.8rem; text-decoration: none; }}
  .dash-link a:hover {{ text-decoration: underline; color: var(--accent); }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }}
  .tab-btn {{
    background: var(--tab-bg); color: var(--text); border: none; border-radius: 8px;
    padding: 10px 16px; font-size: 0.9rem; font-weight: 600; cursor: pointer;
  }}
  .tab-btn.active {{ background: var(--tab-active); color: var(--tab-active-text); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 20px; overflow-x: auto; }}
  h2 {{ font-size: 1.1rem; margin-top: 0; }}
  .intro {{ font-size: 0.88rem; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; white-space: nowrap; }}
  th, td {{ padding: 6px 8px; text-align: center; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; }}
  td.team, th.team {{ text-align: left; }}
  .crest {{ width: 16px; height: 16px; vertical-align: middle; margin-right: 6px; }}
  .pos {{ font-weight: 700; }} .pts {{ font-weight: 700; }}
  tr.cl {{ background: var(--cl); color: var(--cl-text); }}
  tr.el {{ background: var(--el); color: var(--el-text); }}
  tr.ecl {{ background: var(--ecl); color: var(--ecl-text); }}
  tr.relp {{ background: var(--relp); color: var(--relp-text); }}
  tr.rel {{ background: var(--rel); color: var(--rel-text); }}
  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.78rem; margin-top: 10px; color: var(--muted); }}
  .legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
  .dot.cl {{ background: var(--cl); }} .dot.el {{ background: var(--el); }}
  .dot.ecl {{ background: var(--ecl); }} .dot.relp {{ background: var(--relp); }}
  .dot.rel {{ background: var(--rel); }}
  .note {{ color: var(--muted); font-size: 0.8rem; margin-top: 8px; }}
  .explainer {{ background: var(--tab-bg); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem; color: var(--text); margin-bottom: 12px; line-height: 1.5; }}
  .explainer b {{ color: var(--accent); }}
  footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 30px; }}
  details.stat-accordion {{ border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; overflow: hidden; }}
  details.stat-accordion summary {{
    cursor: pointer; padding: 14px 16px; font-weight: 700; font-size: 0.98rem;
    list-style: none; display: flex; justify-content: space-between; align-items: center;
    background: var(--card);
  }}
  details.stat-accordion summary::-webkit-details-marker {{ display: none; }}
  details.stat-accordion summary::after {{ content: "+"; font-size: 1.2rem; color: var(--muted); }}
  details.stat-accordion[open] summary::after {{ content: "−"; }}
  details.stat-accordion summary .sub {{ font-weight: 400; font-size: 0.78rem; color: var(--muted); margin-top: 2px; display: block; }}
  details.stat-accordion .accordion-body {{ padding: 0 16px 16px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="dash-link"><a href="https://paradox-a.github.io/football-dashboard/">&larr; All Trackers (Dashboard)</a></div>
  <h1>Bundesliga 2026-27 Tracker</h1>
  <div class="updated">Matchday {matchday} · Last updated {updated}</div>
  {season_not_started_note}

  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('table')">League Table</button>
    <button class="tab-btn" onclick="showTab('club')">Club Stats</button>
    <button class="tab-btn" onclick="showTab('player')">Player Stats</button>
  </div>

  <div id="tab-table" class="tab-panel active">
    <div class="card">
      <h2>League Table</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th><th>Form</th></tr></thead>
        <tbody>{"".join(rows_html)}</tbody>
      </table>
      <div class="note"><b>P</b> Played &nbsp;·&nbsp; <b>W</b> Won &nbsp;·&nbsp; <b>D</b> Drawn &nbsp;·&nbsp; <b>L</b> Lost &nbsp;·&nbsp; <b>GF</b> Goals For &nbsp;·&nbsp; <b>GA</b> Goals Against &nbsp;·&nbsp; <b>GD</b> Goal Difference (GF minus GA — the first tiebreaker when teams are level on points) &nbsp;·&nbsp; <b>Pts</b> Points (3 for a win, 1 for a draw, 0 for a loss) &nbsp;·&nbsp; <b>Form</b> results of the last 5 games, oldest to newest</div>
      <div class="legend">
        <span><span class="dot cl"></span>Champions League (1-4)</span>
        <span><span class="dot el"></span>Europa League (5)</span>
        <span><span class="dot ecl"></span>Conference League (6)</span>
        <span><span class="dot relp"></span>Relegation Play-off (16)</span>
        <span><span class="dot rel"></span>Relegation (17-18)</span>
      </div>
      <div class="explainer"><b>New to the Bundesliga?</b> Unlike most leagues, 18th and 17th are relegated automatically, but <b>16th place gets a lifeline</b>: a two-legged play-off against the 3rd-place team from 2. Bundesliga (the second tier), with the Bundesliga side needing only a draw across both legs (on aggregate goals) to stay up since they have the away-goals-style tiebreak advantage as the higher-division club in a tie. European qualification spots can also shift based on cup-competition winners already qualifying via league position.</div>
    </div>

    <div class="card">
      <h2>European Race</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Zone</th><th>Pts</th><th>Games Left</th><th>Gap to 4th</th></tr></thead>
        <tbody>{"".join(euro_rows)}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Relegation Watch</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Pts</th><th>Games Left</th><th>What it takes to stay up</th></tr></thead>
        <tbody>{"".join(rel_rows)}</tbody>
      </table>
      <div class="note">"Safety" modeled as ~{SAFETY_THRESHOLD} points, a rough historical Bundesliga survival benchmark. 16th place isn't necessarily safe even above this line — see the play-off note above.</div>
    </div>
  </div>

  <div id="tab-club" class="tab-panel">
    <div class="explainer">
      <b>New to the Bundesliga?</b> The table tells you <i>where</i> a team stands, but not <i>how</i> they got there. These stats show the underlying strengths and weaknesses — a team can have a good record while quietly being fragile defensively, or vice versa.
    </div>

    <div class="card">
      <h2>Defensive Strength: Clean Sheets</h2>
      <div class="explainer">A <b>clean sheet</b> is a game where a team doesn't concede at all. It's the single clearest sign of defensive solidity — Bundesliga title winners are almost always among the league's clean-sheet leaders, because you can't lose a game you don't concede in.</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Played</th><th>Clean Sheets</th><th>Goals Conceded / Game</th><th>Failed to Score</th></tr></thead>
        <tbody>{"".join(clean_sheet_rows) or "<tr><td colspan=5>No finished matches yet</td></tr>"}</tbody>
      </table>
      <div class="note"><b>Failed to Score</b> counts games where a team didn't score at all — a blunt but telling sign of attacking struggles.</div>
    </div>

    <div class="card">
      <h2>Home Fortress vs. Road Warriors</h2>
      <div class="explainer">Some teams are much stronger at home than away (or the reverse) — this is one of the oldest storylines in football, and the Bundesliga is famous for it given the size and atmosphere of grounds like Dortmund's Signal Iduna Park. <b>Points per game (PPG)</b> at home vs. away shows exactly how lopsided that split is. <b>Form</b> is the last 5 results (most recent last) — a better read on momentum than the season-long record.</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Form (last 5)</th><th>Home Record</th><th>Away Record</th></tr></thead>
        <tbody>{"".join(form_home_away_rows) or "<tr><td colspan=4>No finished matches yet</td></tr>"}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Biggest Wins &amp; Heaviest Losses</h2>
      <div class="explainer">Goal margin matters beyond the 3 points — a big win boosts goal difference (which breaks ties in the table) and can be a statement result against a rival, especially in Der Klassiker (Bayern vs. Dortmund) or a regional derby.</div>
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Biggest Win</th></tr></thead>
          <tbody>{biggest_win_rows}</tbody>
        </table>
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Heaviest Loss</th></tr></thead>
          <tbody>{heaviest_loss_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="note" style="margin-top: -8px;">Not shown: possession, shots, passing accuracy, tackles, or expected goals (xG) — these require a paid data source. Everything above is derived directly from final match scores.</div>
  </div>

  <div id="tab-player" class="tab-panel">
    <div class="explainer">
      <b>New to the Bundesliga?</b> The top scorer title doesn't have as iconic a name as the Premier League's Golden Boot or LaLiga's Pichichi, but it's followed just as closely. Goals alone don't capture everything a player contributes — this table adds context.
    </div>
    {season_not_started_note}
    <div class="card">
      <h2>Top Scorer Race &amp; Goal Involvements</h2>
      <div class="explainer">
        <b>Goals</b>: the headline number, and what decides the top scorer title.<br>
        <b>Assists</b>: the pass that directly leads to a goal — a measure of creativity, not just finishing.<br>
        <b>Goal Involvements</b> (goals + assists): a fuller picture of a player's attacking output — a player with 8 goals and 10 assists is arguably more valuable than one with 12 goals and 0 assists.<br>
        <b>Goals/Game</b>: raw totals favor players who've played more games — this rate stat levels the comparison.<br>
        <b>Penalties</b>: shown separately since penalty goals are viewed differently from open-play goals (some fans discount them when judging a striker's true quality).
      </div>
      <table>{PLAYER_TABLE_HEAD}<tbody>{goals_rows or "<tr><td colspan=8>No scorer data yet</td></tr>"}</tbody></table>
      {no_scorer_data_note}
      <div class="note">Not shown: shots, expected goals (xG), key passes, dribbles, or tackles — this combined table's data source only tracks goals, assists, penalties, and appearances. Deeper stats (like xG) require a paid provider.</div>
    </div>

    <div class="explainer" style="margin-top: 4px;">
      <b>Want just one ranking at a time?</b> The sections below pull real numbers directly from Bundesliga.com's own stats hub — Goals, Assists, Yellow Cards, and (for goalkeepers) Shots Saved.
    </div>

    <details class="stat-accordion">
      <summary>Most Goals <span class="sub">The top scorer race — decided by goals alone, nothing else</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Goals</b> is the headline number and what the top scorer title is decided by. It's the most-watched individual stat in the league, but it rewards finishers over creators — see "Most Assists" below for the fuller picture.</div>
        <table>{GOALS_TABLE_HEAD}<tbody>{bl_goals_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Assists <span class="sub">Who's creating goals for others, not just scoring them</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Assists</b> credit the pass (or occasionally the touch) that directly leads to a goal. It's the clearest single measure of creativity — a player can be hugely valuable to a team's attack without scoring much themselves.</div>
        <table>{ASSISTS_TABLE_HEAD}<tbody>{bl_assists_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Yellow Cards <span class="sub">Discipline — persistent fouling, five in a season triggers an automatic ban</span></summary>
      <div class="accordion-body">
        <div class="explainer">A <b>yellow card</b> is a caution for a foul or unsporting behavior. Two in one match means a red card and an early shower. Accumulate enough yellows across the season and the player serves an automatic one-match ban — so this list is also a rough guide to who's one bad tackle away from missing a game.</div>
        <table>{YELLOW_TABLE_HEAD}<tbody>{bl_yellow_rows}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Shots Saved <span class="sub">The clearest individual goalkeeper stat — stops made, regardless of team result</span></summary>
      <div class="accordion-body">
        <div class="explainer">Unlike a team clean sheet (which depends on the whole defense), <b>shots saved</b> credits the goalkeeper directly for stops made, win or lose. A keeper can rack up saves behind a leaky defense just as easily as behind a strong one — it measures individual shot-stopping, not team results.</div>
        <table>{SAVES_TABLE_HEAD}<tbody>{bl_saves_rows}</tbody></table>
      </div>
    </details>

    <div class="note">No dedicated Red Cards ranking is included — Bundesliga.com's own stats hub doesn't publish one (red cards are rare enough that the site folds them into a combined "Cards" tally instead of breaking them out separately), and no other free source was found for this competition.</div>
  </div>

  <footer>Data: football-data.org &amp; bundesliga.com · Rebuilt periodically, not live-updating</footer>
</div>
<script>
function showTab(name) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>
"""

with open(OUT_PATH, "w") as f:
    f.write(html)
print("wrote", OUT_PATH, len(html), "bytes")
