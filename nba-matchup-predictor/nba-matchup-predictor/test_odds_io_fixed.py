import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

# Correction: use apiKey instead of apikey
url = f"https://api.odds-api.io/v3/odds?apiKey={API_KEY}&sport=basketball_nba"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_odds_io_fixed.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched odds data from odds-api.io.")
    if isinstance(data, dict) and "error" in data:
        print("Error message:", data["error"])
    else:
        print("Response keys:", data.keys() if isinstance(data, dict) else "List response")
except Exception as e:
    print(f"FAILED: {e}")
