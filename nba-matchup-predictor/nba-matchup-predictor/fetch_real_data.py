import pandas as pd
import numpy as np
import time
import json
from nba_api.stats.endpoints import leaguegamelog, playergamelogs, leaguestandingsv3, scoreboardv2
from datetime import datetime, timedelta
from database import get_session, Game, PlayerStat, init_db, DB_URL

# Dynamically import the correct insert dialect based on DB_URL
if DB_URL.startswith("postgresql"):
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

def fetch_and_save_data(seasons=['2025-26'], games_filename="real_games.csv", players_filename="real_players.csv"):
    init_db()
    session = get_session()
    all_games = []
    all_players = []
    
    # Season dates (approximate for 2025-26)
    season_start = datetime(2025, 10, 22)
    current_date = datetime.now()
    
    for season in seasons:
        print(f"\n--- Processing Season: {season} ---")
        print(f"Fetching team game logs...")
        try:
            # 1. Fetch Team Game Logs
            log = leaguegamelog.LeagueGameLog(season=season, season_type_all_star='Regular Season')
            df_teams = log.get_data_frames()[0]
            
            # 1b. Fetch Real Quarter Scores (LineScores) via ScoreboardV3
            # We'll fetch daily for the whole season to get period scores
            print("Fetching real quarter scores (LineScore)... This may take a moment.")
            all_line_scores = []
            temp_date = season_start
            total_days = (current_date - season_start).days + 1
            day_count = 0
            while temp_date <= current_date:
                try:
                    day_count += 1
                    if day_count % 10 == 0:
                        print(f"  Syncing Scores: Day {day_count}/{total_days}...")
                    date_str = temp_date.strftime('%Y-%m-%d')
                    sb = scoreboardv2.ScoreboardV2(game_date=date_str)
                    ls = sb.line_score.get_data_frame()
                    if not ls.empty:
                        all_line_scores.append(ls)
                    temp_date += timedelta(days=1)
                    time.sleep(0.5) # Prevent rate limiting
                except:
                    temp_date += timedelta(days=1)
                    continue
            
            df_line = pd.concat(all_line_scores) if all_line_scores else pd.DataFrame()
            
            # Map columns to our schema
            df_teams['date'] = pd.to_datetime(df_teams['GAME_DATE'])
            
            def get_opp(matchup):
                parts = matchup.split(' ')
                return parts[2]
            
            df_teams['team'] = df_teams['TEAM_ABBREVIATION']
            df_teams['opponent'] = df_teams['MATCHUP'].apply(get_opp)
            df_teams['home'] = df_teams['MATCHUP'].apply(lambda x: 1 if 'vs.' in x else 0)
            
            games_clean = []
            
            for gid, group in df_teams.groupby('GAME_ID'):
                if len(group) != 2: continue
                
                t1 = group.iloc[0]
                t2 = group.iloc[1]
                
                # Try to get real quarter scores from df_line
                t1_line = df_line[(df_line['GAME_ID'] == gid) & (df_line['TEAM_ABBREVIATION'] == t1['team'])]
                t2_line = df_line[(df_line['GAME_ID'] == gid) & (df_line['TEAM_ABBREVIATION'] == t2['team'])]
                
                if not t1_line.empty and not t2_line.empty:
                    t1_l = t1_line.iloc[0]
                    t2_l = t2_line.iloc[0]
                    q1 = t1_l.get('PTS_QTR1') or 0
                    q2 = t1_l.get('PTS_QTR2') or 0
                    q3 = t1_l.get('PTS_QTR3') or 0
                    q4 = t1_l.get('PTS_QTR4') or 0
                    oq1 = t2_l.get('PTS_QTR1') or 0
                    oq2 = t2_l.get('PTS_QTR2') or 0
                    oq3 = t2_l.get('PTS_QTR3') or 0
                    oq4 = t2_l.get('PTS_QTR4') or 0
                else:
                    # Fallback to smart distribution if line score missing
                    def get_q_scores(pts):
                        q = pts // 4
                        rem = pts % 4
                        return [q + (1 if i < rem else 0) for i in range(4)]
                    q1, q2, q3, q4 = get_q_scores(t1['PTS'])
                    oq1, oq2, oq3, oq4 = get_q_scores(t2['PTS'])
                
                # Row for Team 1
                row1 = {
                    "game_id": gid,
                    "date": t1['date'],
                    "team": t1['team'],
                    "opponent": t2['team'],
                    "home": t1['home'],
                    "team_pts": int(t1['PTS']),
                    "opp_pts": int(t2['PTS']),
                    "q1_pts": int(q1), "q2_pts": int(q2), "q3_pts": int(q3), "q4_pts": int(q4),
                    "opp_q1_pts": int(oq1), "opp_q2_pts": int(oq2), "opp_q3_pts": int(oq3), "opp_q4_pts": int(oq4),
                    "fga": int(t1['FGA']), "fgm": int(t1['FGM']), "pm3_a": int(t1['FG3A']), "pm3_m": int(t1['FG3M']),
                    "fta": int(t1['FTA']), "tov": int(t1['TOV']), "oreb": int(t1['OREB']), "dreb": int(t1['DREB']),
                    "ast": int(t1['AST']), "stl": int(t1['STL']), "blk": int(t1['BLK']),
                    "opp_fgm": int(t2['FGM']), "opp_pm3_m": int(t2['FG3M']),
                    "opp_fga": int(t2['FGA']), "opp_fta": int(t2['FTA']), "opp_tov": int(t2['TOV']),
                    "opp_stl": int(t2['STL']), "opp_blk": int(t2['BLK']), "opp_oreb": int(t2['OREB']), "opp_dreb": int(t2['DREB'])
                }
                games_clean.append(row1)
                
                # DB Insert with upsert logic (OVERWRITE existing to ensure real data)
                stmt = insert(Game).values(**row1)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['game_id', 'team'],
                    set_={c.name: c for c in stmt.excluded if c.name not in ['game_id', 'team']}
                )
                session.execute(stmt)
                
                # Row for Team 2
                row2 = {
                    "game_id": gid,
                    "date": t2['date'],
                    "team": t2['team'],
                    "opponent": t1['team'],
                    "home": t2['home'],
                    "team_pts": int(t2['PTS']),
                    "opp_pts": int(t1['PTS']),
                    "q1_pts": int(oq1), "q2_pts": int(oq2), "q3_pts": int(oq3), "q4_pts": int(oq4),
                    "opp_q1_pts": int(q1), "opp_q2_pts": int(q2), "opp_q3_pts": int(q3), "opp_q4_pts": int(q4),
                    "fga": int(t2['FGA']), "fgm": int(t2['FGM']), "pm3_a": int(t2['FG3A']), "pm3_m": int(t2['FG3M']),
                    "fta": int(t2['FTA']), "tov": int(t2['TOV']), "oreb": int(t2['OREB']), "dreb": int(t2['DREB']),
                    "ast": int(t2['AST']), "stl": int(t2['STL']), "blk": int(t2['BLK']),
                    "opp_fgm": int(t1['FGM']), "opp_pm3_m": int(t1['FG3M']),
                    "opp_fga": int(t1['FGA']), "opp_fta": int(t1['FTA']), "opp_tov": int(t1['TOV']),
                    "opp_stl": int(t1['STL']), "opp_blk": int(t1['BLK']), "opp_oreb": int(t1['OREB']), "opp_dreb": int(t1['DREB'])
                }
                games_clean.append(row2)
                
                stmt = insert(Game).values(**row2)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['game_id', 'team'],
                    set_={c.name: c for c in stmt.excluded if c.name not in ['game_id', 'team']}
                )
                session.execute(stmt)

            all_games.extend(games_clean)
            session.commit()
            print(f"Collected and saved {len(games_clean)} game rows for {season}")
            
            # 2. Fetch Player Stats
            print("Fetching player data...")
            time.sleep(1) # API requirement
            p_log = playergamelogs.PlayerGameLogs(season_nullable=season, season_type_nullable='Regular Season')
            df_p = p_log.get_data_frames()[0]
            
            # Additional player stats for advanced analytics
            players_clean = df_p[[
                'GAME_ID', 'GAME_DATE', 'TEAM_ABBREVIATION', 'PLAYER_NAME', 
                'PTS', 'REB', 'AST', 'FG3M', 'MIN', 'OREB', 'DREB', 'STL', 'BLK', 'TOV',
                'FGM', 'FGA', 'FTM', 'FTA', 'PF', 'PLUS_MINUS'
            ]].copy()
            
            players_clean.columns = ['game_id', 'date', 'team', 'player', 'pts', 'reb', 'ast', 'pm3', 'min', 'oreb', 'dreb', 'stl', 'blk', 'tov', 'fgm', 'fga', 'ftm', 'fta', 'pf', 'plus_minus']
            players_clean['date'] = pd.to_datetime(players_clean['date'])
            
            # DB Insert for Players
            for _, row in players_clean.iterrows():
                p_row = row.to_dict()
                # Handle potential string minutes (e.g., '25:30')
                if isinstance(p_row['min'], str) and ':' in p_row['min']:
                    parts = p_row['min'].split(':')
                    p_row['min'] = float(parts[0]) + float(parts[1])/60
                
                stmt = insert(PlayerStat).values(**p_row)
                stmt = stmt.on_conflict_do_nothing(index_elements=['game_id', 'player'])
                session.execute(stmt)
            
            session.commit()
            all_players.append(players_clean)
            print(f"Collected and saved {len(players_clean)} player entries for {season}")
            
            # Delay to avoid rate limiting between seasons
            time.sleep(1)
            
        except Exception as e:
            print(f"Failed to fetch data for season {season}: {e}")
            session.rollback()

    session.close()

    if all_games:
        df_final_games = pd.DataFrame(all_games)
        df_final_games.to_csv(games_filename, index=False)
        print(f"\nSUCCESS: Synced {len(df_final_games)} game rows to {games_filename}")

    if all_players:
        df_final_players = pd.concat(all_players)
        df_final_players.to_csv(players_filename, index=False)
        print(f"SUCCESS: Synced {len(df_final_players)} player entries to {players_filename}")

    # 3. Fetch Standings
    print("\nFetching current league standings...")
    try:
        from nba_api.stats.static import teams as static_teams
        all_teams = static_teams.get_teams()
        id_to_abbr = {t['id']: t['abbreviation'] for t in all_teams}
        
        standings = leaguestandingsv3.LeagueStandingsV3(season=seasons[-1])
        df_standings = standings.get_data_frames()[0]
        
        df_standings['TeamAbbreviation'] = df_standings['TeamID'].map(id_to_abbr)
        
        # Save to JSON for easy dashboard access
        standings_data = df_standings[['TeamID', 'TeamAbbreviation', 'TeamName', 'WINS', 'LOSSES', 'WinPCT', 'Conference', 'PlayoffRank']].to_dict(orient='records')
        with open("standings.json", "w") as f:
            json.dump(standings_data, f, indent=2)
        print(f"SUCCESS: Saved standings for {len(standings_data)} teams.")
    except Exception as e:
        print(f"Failed to fetch standings: {e}")

if __name__ == "__main__":
    fetch_and_save_data()
