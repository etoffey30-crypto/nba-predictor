import json
import sys
import time
from datetime import datetime, timedelta, timezone
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams
from nba_api.stats.library.http import STATS_HEADERS

# Force browser-like headers to prevent blocks on GitHub Actions
STATS_HEADERS['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
STATS_HEADERS['Referer'] = 'https://www.nba.com/'
STATS_HEADERS['Origin'] = 'https://www.nba.com'
STATS_HEADERS['Host'] = 'stats.nba.com'
STATS_HEADERS['Accept-Language'] = 'en-US,en;q=0.9'

# Initialize team mapping from nba_api
all_teams = teams.get_teams()
TEAM_ID_TO_ABBR = {t['id']: t['abbreviation'] for t in all_teams}
TEAM_ID_TO_FULL = {t['id']: t['full_name'] for t in all_teams}

def fetch_upcoming_matches(target_date=None, output_file="upcoming.json"):
    """
    Fetches NBA games for a 3-day window starting from target_date using scoreboardv2.
    """
    if not target_date:
        # Use UTC for consistent scheduling across servers
        start_date = datetime.now(timezone.utc)
    else:
        try:
            start_date = datetime.strptime(target_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            start_date = datetime.now(timezone.utc)
            
    upcoming_nba_matches = []
    seen_game_ids = set()

    # Fetch for 3 days (Yesterday, Today, Tomorrow) as requested
    for i in range(-1, 2):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching NBA schedule for {date_str} using ScoreboardV2...")
        
        # Simple retry logic for API calls
        max_retries = 3
        for attempt in range(max_retries):
            try:
                sb = scoreboardv2.ScoreboardV2(game_date=date_str)
                df = sb.get_data_frames()[0]
                
                if df.empty:
                    print(f"  No games found for {date_str}.")
                    break # Success but empty

                for _, row in df.iterrows():
                    gid = row['GAME_ID']
                    if gid in seen_game_ids: continue
                    seen_game_ids.add(gid)
                    
                    # Check if it's an NBA game (starts with '00')
                    if not gid.startswith('00'): continue

                    # Parse match time (approximate from date and status text)
                    try:
                        date_part = row['GAME_DATE_EST'][:10]
                        status_text = str(row.get('GAME_STATUS_TEXT', '')).lower()
                        
                        # Default to 11:59 PM of that day so it doesn't vanish prematurely
                        match_dt = datetime.strptime(date_part, '%Y-%m-%d').replace(hour=23, minute=59, tzinfo=timezone.utc)
                        
                        # Try to extract "7:00 pm" or similar
                        import re
                        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)', status_text)
                        if time_match:
                            h = int(time_match.group(1))
                            m = int(time_match.group(2))
                            p = time_match.group(3)
                            if p == 'pm' and h < 12: h += 12
                            if p == 'am' and h == 12: h = 0
                            # Times from the API (ScoreboardV2) are in ET.
                            # We create the datetime in ET first.
                            match_dt = datetime.strptime(date_part, '%Y-%m-%d').replace(hour=h, minute=m)
                            # Convert to UTC by adding 4/5 hours (approximate, ET to UTC is +4 in summer, +5 in winter).
                            # We'll use 4 hours as a consistent offset for the predictor's filter.
                            match_dt = (match_dt + timedelta(hours=4)).replace(tzinfo=timezone.utc)
                        
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
                break # Success
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed for {date_str}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2) # Small backoff
                else:
                    print(f"  Failed to fetch schedule for {date_str} after {max_retries} attempts.")

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
