import requests
import json
import time
import os

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

def fetch_odds():
    print(f"--- Fetching NBA Odds from odds-api.io ---")
    
    # 0. Clear bookmakers to ensure we can select DraftKings (free plan limit)
    try:
        requests.put(f"https://api.odds-api.io/v3/bookmakers/selected/clear?apiKey={API_KEY}")
    except:
        pass

    # 1. Fetch upcoming events
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

    # Filter for games in the next 24 hours to stay within rate limits (free plan: 100/hr)
    now = time.time()
    one_day_sec = 24 * 3600
    impending_events = [e for e in events if e.get("status") == "pending" and (int(e.get("timestamp", 0)) - now) < one_day_sec]
    
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
                
                odds_map[f"{away} @ {home}"] = game_odds
                odds_map[f"{home} vs {away}"] = game_odds # Dual mapping for easier lookup
                
            time.sleep(0.3)
        except Exception as ex:
            print(f"  Error fetching odds for {eid}: {ex}")

    with open("odds.json", "w") as f:
        json.dump(odds_map, f, indent=2)
    
    # Also save a manifest of upcoming matches in the same format as upcoming.json
    # This serves as a CRITICAL fallback for GitHub Actions when the NBA API is blocked
    odds_matches = []
    from datetime import datetime, timezone
    for e in impending_events:
        ts = int(e.get("timestamp", 0))
        # Ensure we have the same fields as upcoming.json
        # NOTE: odds-api.io uses full names, we need to map them back to abbreviations
        # But for now we'll just use what we have and let predictor handle it
        odds_matches.append({
            "matchId": f"odds_{e['id']}",
            "matchTime": ts,
            "gameStatus": datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%I:%M %p ET'), # Rough estimate
            "homeTeam": TEAM_NAME_TO_ABBR.get(e.get("home"), "UNK"),
            "awayTeam": TEAM_NAME_TO_ABBR.get(e.get("away"), "UNK"),
            "homeName": e.get("home", "Unknown"),
            "awayName": e.get("away", "Unknown"),
            "is_odds_fallback": True
        })
    
    with open("odds_matches.json", "w") as f:
        json.dump(odds_matches, f, indent=2)

    print(f"SUCCESS: Saved odds for {len(odds_map)//2} games to odds.json and manifest to odds_matches.json")

if __name__ == "__main__":
    fetch_odds()
