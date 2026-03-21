import requests
import json

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

# Fetch sports list
url = f"https://api.odds-api.io/v3/sports?apiKey={API_KEY}"

try:
    response = requests.get(url)
    data = response.json()
    with open("test_sports_io.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: Fetched sports list.")
    if isinstance(data, list):
        print(f"Found {len(data)} sports.")
        for s in data[:10]:
            print(f"- {s.get('slug', 'N/A')} ({s.get('name', 'N/A')})")
    else:
        print("Response structure:", data.keys() if isinstance(data, dict) else "Unknown")
except Exception as e:
    print(f"FAILED: {e}")
