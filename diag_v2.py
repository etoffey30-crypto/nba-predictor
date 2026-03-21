import os
import sys
from dotenv import load_dotenv

# Add the nested project directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'nba-matchup-predictor', 'nba-matchup-predictor'))

# Path to the .env file in the root
load_dotenv(".env")

from database import DB_URL
print(f"Connecting to: {DB_URL}")

from sqlalchemy import create_engine
try:
    engine = create_engine(DB_URL)
    conn = engine.connect()
    print("SUCCESS")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
