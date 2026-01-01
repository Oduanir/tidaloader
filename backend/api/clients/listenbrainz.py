
import httpx
from typing import List, Optional, Dict, Any
import logging
from api.models import PlaylistTrack

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
            import traceback
            logger.error(f"Error fetching playlists for {username}: {repr(e)}")
            logger.error(traceback.format_exc())
            raise

    async def get_playlist_by_type(self, username: str, playlist_type: str) -> List[PlaylistTrack]:
        """
        Fetch a specific type of playlist for a user.
        Supported types: 'weekly-jams', 'weekly-exploration', 'year-in-review-discoveries', 'year-in-review-missed'
        """
        logger.info(f"Fetching {playlist_type} for {username}")
        
        playlists = await self.get_user_playlists(username)
        
        target_playlist = None
        
        # Define keywords for each type
        keywords = {
            "weekly-jams": "weekly jams",
            "weekly-exploration": "weekly exploration", 
            "year-in-review-discoveries": "top discoveries",
            "year-in-review-missed": "top missed recordings"
        }
        
        search_term = keywords.get(playlist_type)
        if not search_term:
             logger.error(f"Unknown playlist type: {playlist_type}")
             return []

        # Find the latest playlist matching the keyword
        # Playlists are usually ordered by date descending from the API, but we'll checking carefully
        candidate_playlists = []
        
        # Log available playlists for debugging
        available_titles = [p.get("playlist", {}).get("title", "Unknown") for p in playlists]
        logger.info(f"Available playlists for {username}: {available_titles}")
        
        for pl_wrapper in playlists:
             pl = pl_wrapper.get("playlist", {})
             title = pl.get("title", "").lower()
             if search_term in title:
                 candidate_playlists.append(pl)
        
        logger.info(f"Found {len(candidate_playlists)} candidate playlists for '{search_term}'")

        # Sort by title (usually contains date/year) to get the latest? 
        # Actually the API returns them usually sorted, but let's just take the first one found 
        # which is typically the latest for Weeklys. For yearly, we might want the latest year.
        if candidate_playlists:
            # Simple heuristic: first one is usually latest
            target_playlist = candidate_playlists[0]
            logger.info(f"Selected playlist: {target_playlist.get('title')} ({target_playlist.get('identifier')})")
        
        if not target_playlist:
            logger.warning(f"No playlist found for type '{playlist_type}' for {username}")
            return []
        
        playlist_id_url = target_playlist.get("identifier")
        if not playlist_id_url:
            logger.error("Playlist found but has no identifier")
            return []
            
        uuid = playlist_id_url.split('/')[-1]
        logger.info(f"Fetching full details for playlist {uuid}")
        
        try:
            full_playlist_data = await self.get_playlist(uuid)
            target_playlist = full_playlist_data.get("playlist", {})
        except Exception as e:
             logger.error(f"Failed to fetch full playlist {uuid}: {e}")
             return []

        tracks_data = target_playlist.get("track", [])
        
        playlist_tracks = []
        for t in tracks_data:
            title = t.get("title", "Unknown Title")
            artist = t.get("creator", "Unknown Artist")
            album = t.get("album")
            
            mbid = None
            identifiers = t.get("identifier", [])
            extension = t.get("extension", {})
            
            if "https://musicbrainz.org/doc/jspf#track" in extension:
                meta = extension["https://musicbrainz.org/doc/jspf#track"]
                pass

            if isinstance(identifiers, list):
                for ident in identifiers:
                    if "musicbrainz.org/recording/" in ident:
                        mbid = ident.split("recording/")[-1]
                        break
            
            if not mbid and "musicbrainz_track_id" in extension:
                mbid = extension["musicbrainz_track_id"]
            
            playlist_tracks.append(PlaylistTrack(
                title=title,
                artist=artist,
                mbid=mbid,
                album=album
            ))
            
        logger.info(f"Found {len(playlist_tracks)} tracks in {playlist_type} for {username}")
        return playlist_tracks
