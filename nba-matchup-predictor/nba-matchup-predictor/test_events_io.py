import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

# Try fetching events for NBA
url = f"https://api.odds-api.io/v3/events?apiKey={API_KEY}&sport=basketball_nba"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_events_io.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched events data from odds-api.io.")
    if isinstance(data, dict) and "error" in data:
        print("Error message:", data["error"])
    elif isinstance(data, list):
        print(f"Found {len(data)} events.")
    else:
        print("Response keys:", data.keys() if isinstance(data, dict) else "Unknown response type")
except Exception as e:
    print(f"FAILED: {e}")
