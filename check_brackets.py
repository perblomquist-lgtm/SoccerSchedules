#!/usr/bin/env python3
import requests
import json

# Test the seeding endpoint
division_id = 468295  # U11B - the division from your example
event_id = 28

url = f"https://soccerschedules-backend.fly.dev/api/v1/events/{event_id}/divisions/{division_id}/seeding"

print(f"Testing seeding endpoint: {url}")
print("-" * 80)

try:
    response = requests.get(url, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("-" * 80)
    
    if response.status_code == 200:
        data = response.json()
        print("SUCCESS! Bracket data found:")
        print(json.dumps(data, indent=2))
    elif response.status_code == 404:
        print("404 - No bracket standings found (database empty)")
        print(response.text)
    else:
        print(f"Error response:")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
