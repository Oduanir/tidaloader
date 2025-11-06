"""
Test script for backend API
"""
import requests

BASE_URL = "http://localhost:8000"

def test_search():
    """Test track search"""
    response = requests.get(f"{BASE_URL}/api/search/tracks", params={"q": "Radiohead"})
    print(f"Search Status: {response.status_code}")
    print(f"Results: {len(response.json()['items'])} tracks")

def test_troi():
    """Test Troi generation"""
    response = requests.post(
        f"{BASE_URL}/api/troi/generate",
        json={"username": "z3r069", "playlist_type": "periodic-jams"}
    )
    print(f"Troi Status: {response.status_code}")
    data = response.json()
    print(f"Generated: {data['count']} tracks")
    print(f"Found on Tidal: {data['found_on_tidal']} tracks")

if __name__ == "__main__":
    print("Testing API...")
    test_search()
    print("\n" + "="*50 + "\n")
    test_troi()