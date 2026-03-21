import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint

# Load environment variables from .env if present
load_dotenv(override=True)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database Configuration
# Primary: Supabase (PostgreSQL) via environment variable
# Fallback: Local SQLite for development
SUPABASE_URL = os.environ.get("SUPABASE_DB_URL")
if SUPABASE_URL:
    SUPABASE_URL = SUPABASE_URL.strip()
DB_URL = SUPABASE_URL if SUPABASE_URL else "sqlite:///nba_data.db"

if DB_URL.startswith("postgres://"):
    # SQLAlchemy requires 'postgresql://' instead of 'postgres://' for some versions
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(String)
    date = Column(DateTime)
    team = Column(String)
    opponent = Column(String)
    home = Column(Integer)
    team_pts = Column(Integer)
    opp_pts = Column(Integer)
    q1_pts = Column(Integer); q2_pts = Column(Integer); q3_pts = Column(Integer); q4_pts = Column(Integer)
    opp_q1_pts = Column(Integer); opp_q2_pts = Column(Integer); opp_q3_pts = Column(Integer); opp_q4_pts = Column(Integer)
    fga = Column(Integer); fgm = Column(Integer); pm3_a = Column(Integer); pm3_m = Column(Integer)
    fta = Column(Integer); tov = Column(Integer); oreb = Column(Integer); dreb = Column(Integer)
    ast = Column(Integer); stl = Column(Integer); blk = Column(Integer)
    opp_fgm = Column(Integer); opp_pm3_m = Column(Integer); opp_fga = Column(Integer)
    opp_fta = Column(Integer); opp_tov = Column(Integer); opp_stl = Column(Integer)
    opp_blk = Column(Integer); opp_oreb = Column(Integer); opp_dreb = Column(Integer)

    __table_args__ = (UniqueConstraint('game_id', 'team', name='_game_team_uc'),)

class PlayerStat(Base):
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(String)
    date = Column(DateTime)
    team = Column(String)
    player = Column(String)
    pts = Column(Integer)
    reb = Column(Integer)
    ast = Column(Integer)
    pm3 = Column(Integer)
    min = Column(Float)
    oreb = Column(Integer)
    dreb = Column(Integer)
    stl = Column(Integer)
    blk = Column(Integer)
    tov = Column(Integer)
    fgm = Column(Integer)
    fga = Column(Integer)
    ftm = Column(Integer)
    fta = Column(Integer)
    pf = Column(Integer)
    plus_minus = Column(Integer)

    __table_args__ = (UniqueConstraint('game_id', 'player', name='_game_player_uc'),)

def init_db():
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
