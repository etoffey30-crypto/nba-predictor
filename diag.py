import os
import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Use absolute path to be sure
base_dir = r"c:\Users\EDTOFFEY\OneDrive\Desktop\telosyne\project\nba_api-master\nba_api-master\nba-matchup-predictor\nba-matchup-predictor"
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

url = os.getenv("SUPABASE_DB_URL")
print(f"Connecting to: {url}")

try:
    engine = create_engine(url)
    conn = engine.connect()
    print("SUCCESS")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
