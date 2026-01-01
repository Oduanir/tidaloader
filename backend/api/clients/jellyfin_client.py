import logging
import requests
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin
from api.settings import settings

logger = logging.getLogger(__name__)

class JellyfinClient:
    def __init__(self):
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict[str, str]:
        if not settings.jellyfin_api_key:
            return {}
        
        return {
            "X-Emby-Token": settings.jellyfin_api_key,
            "Content-Type": "application/json",
            # Standard Jellyfin/Emby client headers
            "X-Emby-Authorization": f'MediaBrowser Client="Tidaloader", Device="Server", DeviceId="TidaloaderServer", Version="1.0.0", Token="{settings.jellyfin_api_key}"'
        }

    def _get_base_url(self) -> Optional[str]:
        if not settings.jellyfin_url:
            return None
        return settings.jellyfin_url.rstrip("/")

    def get_system_info(self, url: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Test connection and authentication.
        Returns system info dict or raises Exception.
        """
        # Determine actual URL and Key
        target_url = url.rstrip("/") if url else self._get_base_url()
        target_key = api_key if api_key else settings.jellyfin_api_key

        if not target_url or not target_key:
            raise ValueError("Jellyfin URL or API Key not configured")

        endpoint = f"{target_url}/System/Info"
        
        # Prepare headers for this request specifically if overrides are used
        headers = {
            "X-Emby-Token": target_key,
            "Content-Type": "application/json",
            "X-Emby-Authorization": f'MediaBrowser Client="Tidaloader", Device="Server", DeviceId="TidaloaderServer", Version="1.0.0", Token="{target_key}"'
        }

        try:
            response = self.session.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Jellyfin connection failed: {e}")
            raise Exception(f"Failed to connect to Jellyfin: {str(e)}")

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from Jellyfin.
        """
        base_url = self._get_base_url()
        if not base_url:
            logger.error("get_users: No base_url configured")
            return []

        url = f"{base_url}/Users"
        try:
            # According to Jellyfin API, /Users gets all users if admin
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            users = response.json()
            return users
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return []

    def get_user_image(self, user_id: str) -> Optional[bytes]:
        """
        Get user profile image.
        """
        base_url = self._get_base_url()
        if not base_url:
            return None
            
        # Jellyfin API: /Users/{Id}/Images/Primary
        url = f"{base_url}/Users/{user_id}/Images/Primary"
        
        try:
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None

    def find_playlist_id(self, name: str) -> Optional[str]:
        """
        Search for a playlist by name with robust fallback strategies.
        Strategies:
        1. API Search with exact name
        2. API Search with sanitized name (often how Jellyfin indexes filename-based playlists)
        3. Manual scan of ALL playlists (fallback if search index is broken)
        """
        base_url = self._get_base_url()
        if not base_url:
            return None

        # Helper for search
        def search_api(term: str) -> Optional[str]:
            url = f"{base_url}/Items"
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "Playlist",
                "SearchTerm": term,
                "Limit": 1
            }
            try:
                response = self.session.get(url, params=params, headers=self._get_headers(), timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get("TotalRecordCount", 0) > 0 and data.get("Items"):
                    return data["Items"][0]["Id"]
            except Exception as e:
                logger.error(f"Search API failed for term '{term}': {e}")
            return None

        # Strategy 1: Exact Name
        logger.info(f"Strategy 1: Searching for playlist '{name}'")
        if found_id := search_api(name):
            return found_id

        # Strategy 2: Sanitized Name
        from api.services.files import sanitize_path_component
        safe_name = sanitize_path_component(name)
        if safe_name != name:
            logger.info(f"Strategy 2: Searching for sanitized name '{safe_name}'")
            if found_id := search_api(safe_name):
                return found_id

        # Strategy 3: Fetch All & Match (Brute Force)
        logger.info(f"Strategy 3: Fetching all playlists to match '{name}' or '{safe_name}'")
        try:
            url = f"{base_url}/Items"
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "Playlist",
                # "Fields": "Path" # Optional
            }
            response = self.session.get(url, params=params, headers=self._get_headers(), timeout=15)
            response.raise_for_status()
            data = response.json()
            items = data.get("Items", [])
            
            for item in items:
                # Check against original name
                if item.get("Name") == name:
                    return item.get("Id")
                # Check against sanitized name
                if item.get("Name") == safe_name:
                    return item.get("Id")
                    
        except Exception as e:
            logger.error(f"Strategy 3 failed: {e}")

        logger.warning(f"Failed to find playlist '{name}' after all strategies.")
        return None

    def upload_image(self, item_id: str, image_data: bytes, image_type: str = "Primary") -> bool:
        """
        Upload an image (cover) for an item.
        """
        base_url = self._get_base_url()
        if not base_url:
            return False

        # Jellyfin API: POST /Items/{Id}/Images/{Type}
        # Content-Type should be image/* (e.g. image/jpeg) but requests handles it if we pass data
        # Actually jellyfin expects binary body.
        
        url = f"{base_url}/Items/{item_id}/Images/{image_type}"
        try:
            # Detect format for logging/metadata (Jellyfin is lenient with Base64 but good to know)
            content_type = "image/jpeg"
            if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
                content_type = "image/png"
            elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
                content_type = "image/webp"

            # Use Base64 encoding for upload to avoid 500 Errors with some Jellyfin/Proxy setups
            import base64
            b64_data = base64.b64encode(image_data)
            
            headers = self._get_headers()
            headers["Content-Type"] = content_type
            
            logger.info(f"Uploading image (Base64): {len(b64_data)} bytes, Type: {content_type}")
            response = self.session.post(url, data=b64_data, headers=headers, timeout=30)
            
            response.raise_for_status()
            logger.info(f"Successfully uploaded image for item {item_id}")
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to upload image for {item_id}: {e}")
            if e.response is not None:
                logger.error(f"Server Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload image for {item_id}: {e}")
            return False

    def refresh_library(self) -> bool:
        """
        Triggers a library scan to pick up new files immediately.
        """
        base_url = self._get_base_url()
        if not base_url:
            return False
            
        url = f"{base_url}/Library/Refresh"
        try:
            logger.info("Triggering Jellyfin Library Refresh...")
            # Using POST usually works for triggering scheduled tasks
            response = self.session.post(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh library: {e}")
            return False

jellyfin_client = JellyfinClient()
