import requests
import json
import time
import os
from datetime import datetime, timezone

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"
SPORT = "basketball"
LEAGUE = "usa-nba"
BOOKMAKER = "DraftKings"

TEAM_NAME_TO_ABBR = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA',
    'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
    'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI',
    'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
}


def _parse_event_timestamp(event):
    date_str = event.get("date")
    if date_str:
        try:
            return int(datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            pass

    timestamp = event.get("timestamp")
    if timestamp is None:
        return 0

    try:
        return int(float(timestamp))
    except (TypeError, ValueError):
        return 0


def _load_upcoming_manifest(path="upcoming.json"):
    if not os.path.exists(path):
        return [], {}

    with open(path, "r") as f:
        upcoming_matches = json.load(f)

    target_pairs = {}
    for match in upcoming_matches:
        home_name = match.get("homeName")
        away_name = match.get("awayName")
        if home_name and away_name:
            target_pairs[(home_name, away_name)] = match
    return upcoming_matches, target_pairs


def _build_odds_aliases(event, match=None):
    home_name = event.get("home", "")
    away_name = event.get("away", "")
    home_abbr = TEAM_NAME_TO_ABBR.get(home_name, home_name)
    away_abbr = TEAM_NAME_TO_ABBR.get(away_name, away_name)

    aliases = {
        f"{away_name} @ {home_name}",
        f"{home_name} vs {away_name}",
        f"{away_name} vs {home_name}",
        f"{home_name} @ {away_name}",
        f"{away_abbr} @ {home_abbr}",
        f"{home_abbr} vs {away_abbr}",
        f"{away_abbr} vs {home_abbr}",
        f"{home_abbr} @ {away_abbr}",
    }

    if match:
        match_id = match.get("matchId")
        if match_id:
            aliases.add(str(match_id))

    return {alias for alias in aliases if alias}

def fetch_odds():
    print(f"--- Fetching NBA Odds from odds-api.io ---")
    
    # 0. Clear bookmakers to ensure we can select DraftKings (free plan limit)
    try:
        requests.put(f"https://api.odds-api.io/v3/bookmakers/selected/clear?apiKey={API_KEY}")
    except:
        pass

    upcoming_matches, target_pairs = _load_upcoming_manifest()

    events_url = f"https://api.odds-api.io/v3/events?apiKey={API_KEY}&sport={SPORT}&league={LEAGUE}"
    try:
        response = requests.get(events_url, timeout=10)
        events = response.json()
        if not isinstance(events, list):
            print(f"Error fetching events (invalid response type): {events}")
            return
    except Exception as e:
        print(f"Failed to fetch events (API Timeout or Network Error): {e}")
        return

    now = time.time()
    three_day_sec = 72 * 3600
    pending_events = []
    for event in events:
        if event.get("status") != "pending":
            continue

        event_ts = _parse_event_timestamp(event)
        if event_ts and event_ts < now - 3600:
            continue

        if target_pairs:
            if (event.get("home"), event.get("away")) in target_pairs:
                pending_events.append(event)
        elif event_ts and (event_ts - now) <= three_day_sec:
            pending_events.append(event)

    impending_events = sorted(pending_events, key=_parse_event_timestamp)
    print(f"Found {len(impending_events)} impending matchups (next 24h).")

    odds_map = {}
    
    for e in impending_events:
        eid = e["id"]
        home = e["home"]
        away = e["away"]
        
        print(f"  Fetching odds for {away} @ {home}...")
        odds_url = f"https://api.odds-api.io/v3/odds?apiKey={API_KEY}&eventId={eid}&bookmakers={BOOKMAKER}"
        
        try:
            res = requests.get(odds_url, timeout=10)
            data = res.json()
            
            if "bookmakers" in data and BOOKMAKER in data["bookmakers"]:
                b_odds = data["bookmakers"][BOOKMAKER]
                
                game_odds = {
                    "ml": {"home": None, "away": None},
                    "spread": {"hdp": 0, "home": None, "away": None},
                    "total": {"hdp": 0, "over": None, "under": None},
                    "props": []
                }
                
                for market in b_odds:
                    m_name = market["name"]
                    m_odds = market["odds"][0] if market["odds"] else {}
                    
                    if m_name == "ML":
                        game_odds["ml"] = {"home": m_odds.get("home"), "away": m_odds.get("away")}
                    elif m_name == "Spread":
                        # We take the first one (usually the main line)
                        game_odds["spread"] = {"hdp": m_odds.get("hdp"), "home": m_odds.get("home"), "away": m_odds.get("away")}
                    elif m_name == "Totals":
                        game_odds["total"] = {"hdp": m_odds.get("hdp"), "over": m_odds.get("over"), "under": m_odds.get("under")}
                    elif m_name == "Player Props":
                        game_odds["props"] = market["odds"] # All props

                linked_match = target_pairs.get((home, away))
                for alias in _build_odds_aliases(e, linked_match):
                    odds_map[alias] = game_odds
                
            time.sleep(0.3)
        except Exception as ex:
            print(f"  Error fetching odds for {eid}: {ex}")

    with open("odds.json", "w") as f:
        json.dump(odds_map, f, indent=2)
    
    odds_matches = []
    for e in impending_events:
        ts = _parse_event_timestamp(e)
        linked_match = target_pairs.get((e.get("home"), e.get("away")))
        odds_matches.append({
            "matchId": linked_match.get("matchId", f"odds_{e['id']}") if linked_match else f"odds_{e['id']}",
            "matchTime": ts,
            "gameStatus": linked_match.get("gameStatus") if linked_match else datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%I:%M %p ET'),
            "homeTeam": TEAM_NAME_TO_ABBR.get(e.get("home"), "UNK"),
            "awayTeam": TEAM_NAME_TO_ABBR.get(e.get("away"), "UNK"),
            "homeName": e.get("home", "Unknown"),
            "awayName": e.get("away", "Unknown"),
            "is_odds_fallback": True
        })
    
    with open("odds_matches.json", "w") as f:
        json.dump(odds_matches, f, indent=2)

    print(f"SUCCESS: Saved odds for {len(odds_matches)} games to odds.json and manifest to odds_matches.json")

if __name__ == "__main__":
    fetch_odds()
