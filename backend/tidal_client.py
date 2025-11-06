"""
Tidal API Client with endpoint rotation and retry logic
Ported from automate-troi-download.py
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import requests

class TidalAPIClient:
    """Client for Tidal API with automatic endpoint rotation"""
    
    def __init__(self, endpoints_file: Optional[Path] = None):
        if endpoints_file is None:
            endpoints_file = Path(__file__).parent / "api_endpoints.json"
        
        self.endpoints_file = endpoints_file
        self.endpoints = self._load_endpoints()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.success_history = {}
    
    def _load_endpoints(self) -> List[Dict]:
        """Load endpoints from file or create default"""
        default_endpoints = [
            {"name": "kraken", "url": "https://kraken.squid.wtf", "priority": 1},
            {"name": "triton", "url": "https://triton.squid.wtf", "priority": 1},
            {"name": "zeus", "url": "https://zeus.squid.wtf", "priority": 1},
            {"name": "aether", "url": "https://aether.squid.wtf", "priority": 1},
            {"name": "phoenix", "url": "https://phoenix.squid.wtf", "priority": 1},
            {"name": "shiva", "url": "https://shiva.squid.wtf", "priority": 1},
            {"name": "chaos", "url": "https://chaos.squid.wtf", "priority": 1},
            {"name": "hund", "url": "https://hund.qqdl.site", "priority": 2},
            {"name": "katze", "url": "https://katze.qqdl.site", "priority": 2},
            {"name": "maus", "url": "https://maus.qqdl.site", "priority": 2},
            {"name": "vogel", "url": "https://vogel.qqdl.site", "priority": 2},
            {"name": "wolf", "url": "https://wolf.qqdl.site", "priority": 2},
        ]
        
        if self.endpoints_file.exists():
            try:
                with open(self.endpoints_file, 'r') as f:
                    data = json.load(f)
                    return data.get('endpoints', default_endpoints)
            except Exception:
                pass
        
        return default_endpoints
    
    def _sort_endpoints_by_priority(self, operation: Optional[str] = None) -> List[Dict]:
        """Sort endpoints by priority and success history"""
        endpoints = self.endpoints.copy()
        
        if operation and operation in self.success_history:
            last_success = self.success_history[operation]
            for ep in endpoints:
                if ep['name'] == last_success['name']:
                    ep = ep.copy()
                    ep['priority'] = 0
        
        return sorted(endpoints, key=lambda x: (x.get('priority', 999), x['name']))
    
    def _record_success(self, endpoint: Dict, operation: str):
        """Record successful endpoint for operation"""
        self.success_history[operation] = {
            'name': endpoint['name'],
            'url': endpoint['url'],
            'timestamp': time.time()
        }
    
    def _make_request(self, path: str, params: Optional[Dict] = None, operation: Optional[str] = None) -> Optional[Dict]:
        """Make request with automatic endpoint rotation"""
        sorted_endpoints = self._sort_endpoints_by_priority(operation)
        
        for endpoint in sorted_endpoints:
            url = f"{endpoint['url']}{path}"
            
            try:
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code == 429:
                    time.sleep(2)
                    continue
                
                if response.status_code in [500, 404]:
                    continue
                
                if response.status_code == 200:
                    self._record_success(endpoint, operation or path)
                    return response.json()
                
            except requests.exceptions.RequestException:
                continue
        
        return None
    
    def search_tracks(self, query: str) -> Optional[Dict]:
        """Search for tracks"""
        return self._make_request("/search/", {"s": query}, operation="search_tracks")
    
    def search_albums(self, query: str) -> Optional[Dict]:
        """Search for albums"""
        return self._make_request("/search/", {"al": query}, operation="search_albums")
    
    def search_artists(self, query: str) -> Optional[Dict]:
        """Search for artists"""
        return self._make_request("/search/", {"a": query}, operation="search_artists")
    
    def get_track(self, track_id: int, quality: str = "LOSSLESS") -> Optional[Dict]:
        """Get track details with stream URL"""
        return self._make_request("/track/", {"id": track_id, "quality": quality}, operation="get_track")
    
    def get_album(self, album_id: int) -> Optional[Dict]:
        """Get album details"""
        return self._make_request("/album/", {"id": album_id}, operation="get_album")
    
    def get_album_tracks(self, album_id: int) -> Optional[Dict]:
        """Get album tracks specifically"""
        return self._make_request("/album/tracks", {"id": album_id}, operation="get_album_tracks")