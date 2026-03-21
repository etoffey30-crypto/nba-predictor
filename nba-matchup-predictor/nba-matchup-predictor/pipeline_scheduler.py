import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from fetch_real_data import fetch_and_save_data
from fetch_upcoming import fetch_upcoming_matches, fetch_recent_results
from fetch_injuries import fetch_injuries
from fetch_odds import fetch_odds
from predictor import run_pipeline
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_and_retrain(target_date=None):
    logger.info("Starting daily update and retrain process...")
    
    try:
        # 1. Fetch historical data (updates CSV and SQLite)
        logger.info("Step 1: Fetching latest historical data...")
        fetch_and_save_data()
        
        # 2. Fetch upcoming matches and recent results
        logger.info("Step 2: Fetching upcoming matchups and recent results...")
        fetch_upcoming_matches(target_date=target_date)
        fetch_recent_results()
        
        # 3. Fetch Injuries and Odds
        logger.info("Step 3: Syncing Injuries and Betting Odds (odds-api.io)...")
        fetch_injuries()
        fetch_odds()
        
        # 4. Run prediction pipeline (Preprocess, Add Analytics, Retrain ML, Export data.js)
        logger.info("Step 4: Running prediction engine, retraining ML, and exporting...")
        run_pipeline()
        
        logger.info("Success: Daily update completed.")
    except Exception as e:
        logger.error(f"Error during daily update: {e}")

def main():
    if "--now" in sys.argv:
        target_date = None
        if "--date" in sys.argv:
            idx = sys.argv.index("--date")
            if idx + 1 < len(sys.argv):
                target_date = sys.argv[idx+1]
        update_and_retrain(target_date)
        return

    scheduler = BlockingScheduler()
    
    # Schedule update for 6:00 AM every day
    scheduler.add_job(update_and_retrain, 'cron', hour=6, minute=0)
    
    logger.info("NBA Matchup Predictor Scheduler started. Waiting for next scheduled run (06:00 daily)...")
    logger.info("To run immediately for testing, use: python pipeline_scheduler.py --now")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    main()
