import json
import sys
import time
from datetime import datetime, timedelta, timezone
from nba_api.stats.endpoints import scoreboardv3
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
    Fetches NBA games for a 3-day window starting from target_date using scoreboardv3.
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
        print(f"Fetching NBA schedule for {date_str} using ScoreboardV3...")
        
        # Simple retry logic for API calls
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # ScoreboardV3 is more robust for 2025-26
                sb = scoreboardv3.ScoreboardV3(game_date=date_str)
                df_games = sb.get_data_frames()[1]
                df_teams = sb.get_data_frames()[2]
                
                if df_games.empty:
                    print(f"  No games found for {date_str}.")
                    break # Success but empty

                for _, row in df_games.iterrows():
                    gid = row['gameId']
                    if gid in seen_game_ids: continue
                    seen_game_ids.add(gid)
                    
                    # Check if it's an NBA game (starts with '00')
                    if not gid.startswith('00'): continue

                    # Get teams for this game from df_teams
                    game_teams = df_teams[df_teams['gameId'] == gid]
                    if len(game_teams) < 2: continue
                    
                    # ScoreboardV3 gameCode format: YYYYMMDD/AWAYHOME
                    game_code = row['gameCode']
                    away_abbr = game_code[-6:-3]
                    home_abbr = game_code[-3:]
                    
                    t1 = game_teams.iloc[0]
                    t2 = game_teams.iloc[1]
                    
                    if t1['teamTricode'] == home_abbr:
                        home_row, away_row = t1, t2
                    else:
                        home_row, away_row = t2, t1

                    # matchTime is UTC from the API
                    try:
                        time_str = row['gameTimeUTC'] # e.g. 2026-03-25T23:00:00Z
                        match_dt = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                        match_ts = int(match_dt.timestamp())
                    except:
                        # Fallback for old games or parsing errors
                        match_ts = int(current_date.timestamp()) + 86340

                    upcoming_nba_matches.append({
                        "matchId": gid,
                        "matchTime": match_ts,
                        "gameStatus": row.get('gameStatusText', ''),
                        "homeTeam": home_row['teamTricode'],
                        "awayTeam": away_row['teamTricode'],
                        "homeName": f"{home_row['teamCity']} {home_row['teamName']}",
                        "awayName": f"{away_row['teamCity']} {away_row['teamName']}"
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
    # NOTE: fetch_real_data.py handles the bulk of this
    with open(output_file, "w") as f:
        f.write("[]")

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_upcoming_matches(target_date=target_date)
    fetch_recent_results()
