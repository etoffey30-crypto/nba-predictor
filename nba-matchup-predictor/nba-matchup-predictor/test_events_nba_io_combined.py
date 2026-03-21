import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"
SPORT = "basketball"
LEAGUE = "usa-nba"

# Fetch events with both sport and league
url = f"https://api.odds-api.io/v3/events?apiKey={API_KEY}&sport={SPORT}&league={LEAGUE}"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_events_nba_io_combined.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched combined events data.")
    if isinstance(data, list):
        print(f"Found {len(data)} events.")
        for e in data[:5]:
            print(f"- {e.get('name', 'N/A')} (ID: {e.get('id', 'N/A')})")
    else:
        print("Response structure:", data.keys() if isinstance(data, dict) else "Unknown")
except Exception as e:
    print(f"FAILED: {e}")
