import sys
import os
from datetime import datetime

# Add the parent directory to sys.path so we can import nba_api if needed (though it's installed)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fetch_real_data import fetch_and_save_data
from fetch_upcoming import fetch_upcoming_matches

def run_pipeline(target_date=None):
    """
    Runs the full data pipeline:
    1. Syncs historical data (real_games.csv, real_players.csv)
    2. Fetches upcoming matches (upcoming.json)
    """
    print("==========================================")
    print("   NBA Matchup Predictor Data Pipeline    ")
    print("==========================================")
    
    # 1. Sync Historical Data
    print("\n[PHASE 1] Syncing Historical Data...")
    fetch_and_save_data()
    
    # 2. Fetch Upcoming/Target Date Matches
    print("\n[PHASE 2] Fetching Match Schedule...")
    fetch_upcoming_matches(target_date=target_date)
    
    print("\n==========================================")
    print("   Data Pipeline Completed Successfully   ")
    print("==========================================")

if __name__ == "__main__":
    # If a date is passed (YYYY-MM-DD), use it for upcoming matches
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(target_date=date_arg)
