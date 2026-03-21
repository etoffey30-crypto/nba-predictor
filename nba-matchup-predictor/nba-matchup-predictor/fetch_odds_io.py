import requests
import json
import time

API_KEY = "22503add9f32506e2af3115737fc5989a08b0a5822de5dd01de7f59d1be66c5a"

def fetch_all_odds():
    # 1. Load events
    with open("test_events_nba_io_combined.json", "r") as f:
        events = json.load(f)
    
    pending_events = [e for e in events if e.get("status") == "pending"]
    print(f"Found {len(pending_events)} pending events.")
    
    all_odds = []
    for e in pending_events[:5]: # Let's test with first 5 to avoid too many requests
        eid = e["id"]
        print(f"Fetching odds for {e['home']} vs {e['away']} (ID: {eid})...")
        url = f"https://api.odds-api.io/v3/odds?apiKey={API_KEY}&eventId={eid}"
        try:
            res = requests.get(url)
            odds_data = res.json()
            all_odds.append({
                "eventId": eid,
                "home": e["home"],
                "away": e["away"],
                "date": e["date"],
                "odds": odds_data
            })
            time.sleep(0.5) # Be nice to the API
        except Exception as ex:
            print(f"Error for {eid}: {ex}")
            
    with open("odds_data_io.json", "w") as f:
        json.dump(all_odds, f, indent=2)
    print("DONE: Saved odds for 5 games.")

if __name__ == "__main__":
    fetch_all_odds()
