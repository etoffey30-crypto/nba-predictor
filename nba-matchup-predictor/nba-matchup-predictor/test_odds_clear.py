import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

# 1. Clear selected bookmakers
clear_url = f"https://api.odds-api.io/v3/bookmakers/selected/clear?apiKey={API_KEY}"
print("Clearing bookmakers...")
try:
    res = requests.put(clear_url) # Documentation says PUT
    print("Clear response:", res.json())
except Exception as e:
    print("Clear failed:", e)

# 2. Try to fetch with DraftKings now
url = f"https://api.odds-api.io/v3/odds?apiKey={API_KEY}&eventId=62924493&bookmakers=DraftKings"
try:
    res = requests.get(url)
    data = res.json()
    with open("test_odds_after_clear.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Fetch response:", data.get("error") if "error" in data else "SUCCESS")
except Exception as e:
    print("Fetch failed:", e)
