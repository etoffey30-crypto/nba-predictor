import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(filename="games.csv", player_filename="players.csv", n_teams=10, games_per_team=30):
    teams = [f"Team{chr(65+i)}" for i in range(n_teams)]
    team_rosters = {team: [f"{team}_Player{j}" for j in range(1, 6)] for team in teams} # 5 key players per team
    
    game_data = []
    player_data = []
    start_date = datetime(2023, 10, 20)
    
    for team in teams:
        opponents = [t for t in teams if t != team]
        for i in range(games_per_team):
            date = start_date + timedelta(days=i*2 + np.random.randint(0, 2))
            opp = np.random.choice(opponents)
            home = np.random.choice([0, 1])
            
            # Generate Quarter Scores (sum up to realistic total)
            q_mean = [27, 27, 27, 27]
            q_scores = [max(15, int(np.random.normal(m, 5))) for m in q_mean]
            opp_q_scores = [max(15, int(np.random.normal(m, 5))) for m in q_mean]
            
            team_pts = sum(q_scores)
            opp_pts = sum(opp_q_scores)
            
            # Basic team stats
            fga = np.random.randint(80, 100)
            fgm = int(fga * np.random.uniform(0.4, 0.55))
            three_pa = np.random.randint(25, 45)
            three_pm = int(three_pa * np.random.uniform(0.3, 0.4))
            fta = np.random.randint(15, 30)
            ftm = int(fta * np.random.uniform(0.7, 0.85))
            
            game_id = f"{team}_{opp}_{i}"
            
            game_data.append({
                "game_id": game_id,
                "date": date,
                "team": team,
                "opponent": opp,
                "home": home,
                "team_pts": team_pts,
                "opp_pts": opp_pts,
                "q1_pts": q_scores[0],
                "q2_pts": q_scores[1],
                "q3_pts": q_scores[2],
                "q4_pts": q_scores[3],
                "opp_q1_pts": opp_q_scores[0],
                "opp_q2_pts": opp_q_scores[1],
                "opp_q3_pts": opp_q_scores[2],
                "opp_q4_pts": opp_q_scores[3],
                "fga": fga,
                "fgm": fgm,
                "3pa": three_pa,
                "3pm": three_pm,
                "fta": fta,
                "tov": np.random.randint(10, 20),
                "oreb": np.random.randint(5, 15),
                "opp_fga": np.random.randint(80, 100),
                "opp_fta": np.random.randint(15, 30),
                "opp_tov": np.random.randint(10, 20)
            })
            
            # Generate Player Stats for this game
            for p_name in team_rosters[team]:
                # distribute points unevenly
                pts_share = np.random.dirichlet(np.ones(5))[team_rosters[team].index(p_name)]
                p_pts = int(team_pts * pts_share * 2) # boost to make it look like stars score more
                
                player_data.append({
                    "game_id": game_id,
                    "date": date,
                    "team": team,
                    "player": p_name,
                    "pts": p_pts,
                    "reb": np.random.randint(0, 15),
                    "ast": np.random.randint(0, 12),
                    "pm3": np.random.randint(0, 6)
                })
            
    df_games = pd.DataFrame(game_data)
    df_players = pd.DataFrame(player_data)
    
    df_games.to_csv(filename, index=False)
    df_players.to_csv(player_filename, index=False)
    
    print(f"Generated {len(df_games)} games in {filename}")
    print(f"Generated {len(df_players)} player stat lines in {player_filename}")

if __name__ == "__main__":
    generate_sample_data()
