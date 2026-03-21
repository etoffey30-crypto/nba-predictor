import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Path to the .env file
env_path = os.path.join('nba-matchup-predictor', 'nba-matchup-predictor', '.env')
load_dotenv(env_path)

url = os.getenv('SUPABASE_DB_URL')

with open('error_log.txt', 'w') as f:
    f.write(f"Attempting to connect to: {url}\n")
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            f.write("SUCCESS: Connection established.\n")
    except OperationalError as e:
        f.write("\n--- OPERATIONAL ERROR ---\n")
        f.write(f"Error: {e}\n")
    except Exception as e:
        f.write("\n--- OTHER ERROR ---\n")
        f.write(f"Type: {type(e)}\n")
        f.write(f"Error: {e}\n")
