import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"
# The user provided: https://api.odds-api.io/v3
# I need to find the correct endpoint for NBA odds on this specific API.
# Usually it's /odds or /sports/basketball_nba/odds

url = f"https://api.odds-api.io/v3/odds?apikey={API_KEY}&sport=basketball_nba"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_odds_io.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched odds data from odds-api.io.")
    print("Keys found:", data.keys() if isinstance(data, dict) else "List response")
except Exception as e:
    print(f"FAILED: {e}")
