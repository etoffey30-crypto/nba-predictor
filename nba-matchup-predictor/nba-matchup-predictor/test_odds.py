import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"
SPORT = "basketball_nba"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
ODDS_FORMAT = "american"

url = f"https://api.the-odds-api.com/v3/odds?api_key={API_KEY}&sport={SPORT}&region={REGIONS}&mkt={MARKETS}&oddsFormat={ODDS_FORMAT}"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_odds.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched odds data.")
    if 'data' in data:
        print(f"Found {len(data['data'])} games.")
    else:
        print("Response layout:", data.keys())
except Exception as e:
    print(f"FAILED: {e}")
