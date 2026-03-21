import os
import pandas as pd
from sqlalchemy import create_engine
from database import Game, PlayerStat, DB_URL, Base

# Local SQLite connection
SQLITE_URL = "sqlite:///nba_data.db"

def migrate():
    if not os.environ.get("SUPABASE_DB_URL"):
        print("ERROR: SUPABASE_DB_URL environment variable not set.")
        print("Please set it: $env:SUPABASE_DB_URL='postgresql://user:pass@host:port/db'")
        return

    print(f"Connecting to Supabase...")
    engine_remote = create_engine(DB_URL)
    
    print("Initializing remote schema...")
    Base.metadata.create_all(engine_remote)
    
    if not os.path.exists("nba_data.db"):
        print("Local database 'nba_data.db' not found. Skipping migration of existing records.")
        return

    print("Connecting to local SQLite...")
    engine_local = create_engine(SQLITE_URL)
    
    # Migrate Games
    print("Migrating Games...")
    df_games = pd.read_sql("SELECT * FROM games", engine_local)
    if len(df_games) > 0:
        # Remove 'id' column to let Postgres handle auto-increment if needed
        # or keep it if you want exact matches. 
        # Better to drop 'id' if serial/identity is used in Postgres.
        if 'id' in df_games.columns:
            df_games = df_games.drop(columns=['id'])

        # Fix types to avoid 'bytea' mismatch
        string_cols = ['game_id', 'team', 'opponent']
        for col in df_games.columns:
            if col not in string_cols and col != 'date':
                df_games[col] = pd.to_numeric(df_games[col], errors='coerce').fillna(0).astype(int)
        
        df_games.to_sql('games', engine_remote, if_exists='append', index=False)
        print(f"Successfully migrated {len(df_games)} games.")
    
    # Migrate Player Stats
    print("Migrating Player Stats...")
    df_players = pd.read_sql("SELECT * FROM player_stats", engine_local)
    if len(df_players) > 0:
        if 'id' in df_players.columns:
            df_players = df_players.drop(columns=['id'])
            
        string_cols_p = ['game_id', 'team', 'player']
        for col in df_players.columns:
            if col not in string_cols_p and col != 'date':
                if col == 'min':
                    df_players[col] = pd.to_numeric(df_players[col], errors='coerce').fillna(0.0).astype(float)
                else:
                    df_players[col] = pd.to_numeric(df_players[col], errors='coerce').fillna(0).astype(int)
                    
        df_players.to_sql('player_stats', engine_remote, if_exists='append', index=False)
        print(f"Successfully migrated {len(df_players)} player records.")

    print("Migration complete!")

if __name__ == "__main__":
    import traceback
    try:
        migrate()
    except Exception:
        traceback.print_exc()
