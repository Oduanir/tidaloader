
import httpx
from typing import List, Optional, Dict, Any
import logging
from api.models import PlaylistTrack

# Configure logging
logger = logging.getLogger(__name__)

class ListenBrainzClient:
    """Client for ListenBrainz API"""
    
    BASE_URL = "https://api.listenbrainz.org/1"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """Fetch a specific playlist by ID"""
        url = f"{self.BASE_URL}/playlist/{playlist_id}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching playlist {playlist_id}: {e}")
            raise

    async def get_user_playlists(self, username: str) -> List[Dict[str, Any]]:
        """Fetch playlists created for a user (Weekly Jams, etc)"""
        url = f"{self.BASE_URL}/user/{username}/playlists/createdfor"
        try:
            response = await self.client.get(url)
            # 404 means user not found or no playlists
            if response.status_code == 404:
                logger.warning(f"User {username} not found or has no playlists")
                return []
            
            response.raise_for_status()
            data = response.json()
            return data.get("playlists", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching playlists for {username}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching playlists for {username}: {e}")
            raise

    async def get_weekly_jams(self, username: str) -> List[PlaylistTrack]:
        """
        Fetch the 'Weekly Jams' playlist for a user.
        Returns a list of PlaylistTrack objects.
        """
        logger.info(f"Fetching Weekly Jams for {username}")
        
        # 1. List user playlists (created for user)
        playlists = await self.get_user_playlists(username)
        
        # 2. Find 'Weekly Jams'
        weekly_jams_playlist = None
        # Sort by date descending to get the latest?
        # The list order isn't guaranteed, but usually latest is first or we should parse date.
        # For now, let's just picking the first one matching the name, as the API seems to return ordered lists.
        # But if there are multiple, we might want the latest.
        
        candidate_playlists = []
        for pl_wrapper in playlists:
             pl = pl_wrapper.get("playlist", {})
             title = pl.get("title", "")
             if "weekly jams" in title.lower():
                 candidate_playlists.append(pl)
        
        if candidate_playlists:
            # Pick the first one (usually latest)
            weekly_jams_playlist = candidate_playlists[0]
        else:
            # Fallback: Check for other periodic jams like "Weekly Exploration"
            for pl_wrapper in playlists:
                pl = pl_wrapper.get("playlist", {})
                title = pl.get("title", "")
                if "weekly exploration" in title.lower():
                    weekly_jams_playlist = pl
                    break
        
        if not weekly_jams_playlist:
            logger.warning(f"No Weekly Jams playlist found for {username}")
            return []

        # 3. Fetch full playlist details using UUID
        # The playlist object in the list might differ from full detail, specifically for tracks.
        # We need to fetch the full playlist by ID to get tracks if they are not fully populated.
        # However, debug output showed tracks count in the summary? No, debug script fetched details.
        # The 'playlists/createdfor' response format:
        # "playlists": [{"playlist": { ..., "track": [] } }] - track list is empty in summary!
        # So we MUST fetch by ID.
        
        playlist_id_url = weekly_jams_playlist.get("identifier")
        if not playlist_id_url:
            logger.error("Weekly Jams playlist found but has no identifier")
            return []
            
        uuid = playlist_id_url.split('/')[-1]
        logger.info(f"Fetching full details for playlist {uuid}")
        
        try:
            full_playlist_data = await self.get_playlist(uuid)
            weekly_jams_playlist = full_playlist_data.get("playlist", {})
        except Exception as e:
             logger.error(f"Failed to fetch full playlist {uuid}: {e}")
             return []

        # 4. Extract tracks
        tracks_data = weekly_jams_playlist.get("track", [])
        
        playlist_tracks = []
        for t in tracks_data:
            title = t.get("title", "Unknown Title")
            artist = t.get("creator", "Unknown Artist")
            album = t.get("album")
            
            # Extract MBID
            mbid = None
            identifiers = t.get("identifier", [])
            extension = t.get("extension", {})
            
            # primary source: extension
            if "https://musicbrainz.org/doc/jspf#track" in extension:
                meta = extension["https://musicbrainz.org/doc/jspf#track"]
                # Sometimes it is inside additional_metadata -> ...
                # But MBID is usually in identifiers list as a URL
                pass

            # Check identifiers list for MBID URL
            if isinstance(identifiers, list):
                for ident in identifiers:
                    if "musicbrainz.org/recording/" in ident:
                        mbid = ident.split("recording/")[-1]
                        break
            
            # Fallback to extension if valid
            if not mbid and "musicbrainz_track_id" in extension:
                mbid = extension["musicbrainz_track_id"]
            
            playlist_tracks.append(PlaylistTrack(
                title=title,
                artist=artist,
                mbid=mbid,
                album=album
            ))
            
        logger.info(f"Found {len(playlist_tracks)} tracks in Weekly Jams for {username}")
        return playlist_tracks
