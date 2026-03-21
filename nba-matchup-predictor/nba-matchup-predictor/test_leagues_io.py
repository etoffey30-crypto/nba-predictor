import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

# Fetch leagues for basketball
url = f"https://api.odds-api.io/v3/leagues?apiKey={API_KEY}&sport=basketball"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_leagues_io.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched leagues.")
    if isinstance(data, list):
        print(f"Found {len(data)} leagues.")
        for l in data:
            print(f"- {l.get('slug', 'N/A')} ({l.get('name', 'N/A')})")
    else:
        print("Response structure:", data.keys() if isinstance(data, dict) else "Unknown")
except Exception as e:
    print(f"FAILED: {e}")
