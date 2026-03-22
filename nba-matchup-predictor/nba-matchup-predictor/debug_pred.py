import pandas as pd
from predictor import load_games, rolling_last10, predict_matchup, load_players, add_base_metrics, add_sos_metrics, apply_advanced_analytics, add_player_rolling

df = load_games()
df_p = load_players()
df = add_base_metrics(df)
df = rolling_last10(df)
df = add_sos_metrics(df)
df = apply_advanced_analytics(df)
df_p = add_player_rolling(df_p)

# Pick a team
teamA = "PHX"
teamB = "DEN"

lastA = df[df["team"] == teamA].iloc[-1]
print(f"Team {teamA} last game date: {lastA['date']}")
for q in range(1, 5):
    col = f"adj_q{q}_share_10"
    print(f"{col}: {lastA.get(col, 'MISSING')}")

res = predict_matchup(teamA, teamB, df, df_p)
print("\nPrediction Result for PHX vs DEN:")
print(f"PtsA: {res['main']['ptsA']}")
print(f"Quarters index 0: {res['quarters'][0]}")
print(f"Halves: {res['halves']}")
