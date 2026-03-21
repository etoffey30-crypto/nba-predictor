import json
import sys
import time
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams

# Initialize team mapping from nba_api
all_teams = teams.get_teams()
TEAM_ID_TO_ABBR = {t['id']: t['abbreviation'] for t in all_teams}
TEAM_ID_TO_FULL = {t['id']: t['full_name'] for t in all_teams}

def fetch_upcoming_matches(target_date=None, output_file="upcoming.json"):
    """
    Fetches NBA games for a 3-day window starting from target_date using scoreboardv2.
    """
    if not target_date:
        start_date = datetime.now()
    else:
        try:
            start_date = datetime.strptime(target_date, '%Y-%m-%d')
        except:
            start_date = datetime.now()
            
    upcoming_nba_matches = []
    seen_game_ids = set()

    # Fetch for 3 days to ensure we catch upcoming games
    for i in range(3):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching NBA schedule for {date_str} using ScoreboardV2...")
        
        try:
            sb = scoreboardv2.ScoreboardV2(game_date=date_str)
            df = sb.get_data_frames()[0]
            
            if df.empty:
                print(f"  No games found for {date_str}.")
                continue

            for _, row in df.iterrows():
                gid = row['GAME_ID']
                if gid in seen_game_ids: continue
                seen_game_ids.add(gid)
                
                # Check if it's an NBA game (starts with '00')
                if not gid.startswith('00'): continue

                # Parse match time (approximate from date and status text)
                # GAME_DATE_EST is 2026-03-19T00:00:00
                # GAME_STATUS_TEXT is "7:00 pm ET"
                try:
                    date_part = row['GAME_DATE_EST'][:10]
                    status_text = str(row.get('GAME_STATUS_TEXT', '')).lower()
                    
                    # Default to 11:59 PM of that day so it doesn't vanish prematurely
                    match_dt = datetime.strptime(date_part, '%Y-%m-%d').replace(hour=23, minute=59)
                    
                    # Try to extract "7:00 pm" or similar
                    import re
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)', status_text)
                    if time_match:
                        h = int(time_match.group(1))
                        m = int(time_match.group(2))
                        p = time_match.group(3)
                        if p == 'pm' and h < 12: h += 12
                        if p == 'am' and h == 12: h = 0
                        match_dt = match_dt.replace(hour=h, minute=m)
                    
                    match_ts = int(match_dt.timestamp())
                except Exception as e:
                    print(f"    Time parse error for {gid}: {e}")
                    match_ts = int(current_date.timestamp()) + 86340 # 23:59:00

                upcoming_nba_matches.append({
                    "matchId": gid,
                    "matchTime": match_ts,
                    "gameStatus": row.get('GAME_STATUS_TEXT', ''),
                    "homeTeam": TEAM_ID_TO_ABBR.get(row['HOME_TEAM_ID'], "UNK"),
                    "awayTeam": TEAM_ID_TO_ABBR.get(row['VISITOR_TEAM_ID'], "UNK"),
                    "homeName": TEAM_ID_TO_FULL.get(row['HOME_TEAM_ID'], "Unknown"),
                    "awayName": TEAM_ID_TO_FULL.get(row['VISITOR_TEAM_ID'], "Unknown")
                })
        except Exception as e:
            print(f"  Error fetching {date_str}: {e}")

    with open(output_file, "w") as f:
        json.dump(upcoming_nba_matches, f, indent=2)
        
    print(f"Saved {len(upcoming_nba_matches)} NBA matches to {output_file}")

def fetch_recent_results(output_file="recent_results.json"):
    """
    Fetches recent results to ensure the database has the most current scores.
    """
    print("Fetching recent results using nba_api...")
    # NOTE: fetch_real_data.py handles the bulk of this, 
    # but we'll provide a placeholder or small update here if needed.
    # For now, we'll just skip to avoid redundancy with the main pipeline.
    with open(output_file, "w") as f:
        f.write("[]")

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_upcoming_matches(target_date=target_date)
    fetch_recent_results()
