import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"
EID = 62924493 # Detroit vs Golden State

# Try with capitalized bookmaker names
url = f"https://api.odds-api.io/v3/odds?apiKey={API_KEY}&eventId={EID}&bookmakers=DraftKings,FanDuel"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_odds_final_check.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Attempted fetch.")
    if isinstance(data, dict) and "error" in data:
        print("Error:", data["error"])
    else:
        print("Response structure:", data.keys() if isinstance(data, dict) else "List")
except Exception as e:
    print(f"FAILED: {e}")
