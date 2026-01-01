import asyncio
from typing import Optional, Callable, Dict, List, Awaitable
from api.state import lb_progress_queues
from api.utils.logging import log_info, log_error
from api.utils.text import fix_unicode
from api.services.search import search_track_with_fallback
from api.clients.listenbrainz import ListenBrainzClient

async def fetch_and_validate_listenbrainz_playlist(
    username: str, 
    playlist_type: str, 
    progress_callback: Optional[Callable[[Dict], Awaitable[None]]] = None,
    validate: bool = True
) -> List[Dict]:
    """
    Reusable function to fetch and optionally validate ListenBrainz playlist.
    Used by both UI (via progress_callback) and Background Sync.
    """
    client = ListenBrainzClient()
    
    async def report(data: Dict):
        if progress_callback:
            await progress_callback(data)
            
    try:
        display_name = playlist_type.replace("-", " ").title()
        await report({
            "type": "info",
            "message": f"Fetching {display_name} for {username}...",
            "progress": 0,
            "total": 0
        })
        
        tracks = await client.get_playlist_by_type(username, playlist_type)
        
        if not tracks:
             raise Exception(f"No playlist found for type '{display_name}' for this user.")

        for track in tracks:
            track.title = fix_unicode(track.title)
            track.artist = fix_unicode(track.artist)
            if track.album:
                track.album = fix_unicode(track.album)
        
        await report({
            "type": "info",
            "message": f"Found {len(tracks)} tracks from ListenBrainz",
            "progress": 0,
            "total": len(tracks)
        })
        
        validated_tracks = []
        if validate:
            for i, track in enumerate(tracks, 1):
                display_text = f"{track.artist} - {track.title}"
                
                await report({
                    "type": "validating",
                    "message": f"Validating: {display_text}",
                    "progress": i,
                    "total": len(tracks),
                    "current_track": {
                        "artist": track.artist,
                        "title": track.title
                    }
                })
                
                log_info(f"[{i}/{len(tracks)}] Validating: {display_text}")
                
                await search_track_with_fallback(track.artist, track.title, track)
                
                validated_tracks.append({
                    "title": track.title,
                    "artist": track.artist,
                    "mbid": track.mbid,
                    "tidal_id": track.tidal_id,
                    "tidal_artist_id": track.tidal_artist_id,
                    "tidal_album_id": track.tidal_album_id,
                    "tidal_exists": track.tidal_exists,
                    "album": track.album,
                    "cover": getattr(track, 'cover', None)
                })
                
                await asyncio.sleep(0.1)
        else:
             for track in tracks:
                validated_tracks.append({
                    "title": track.title,
                    "artist": track.artist,
                    "mbid": track.mbid,
                    "tidal_id": None,
                    "tidal_artist_id": None,
                    "tidal_album_id": None,
                    "tidal_exists": False,
                    "album": track.album,
                    "cover": None
                })
             
             await report({
                "type": "info",
                "message": "Skipping validation as requested.",
                "progress": len(tracks),
                "total": len(tracks)
             })
        
        found_count = sum(1 for t in validated_tracks if t.get("tidal_exists"))
        
        log_info(f"Validation complete: {found_count}/{len(validated_tracks)} found on Tidal")
        
        await report({
            "type": "complete",
            "message": f"Validation complete: {found_count}/{len(validated_tracks)} found on Tidal",
            "progress": len(tracks),
            "total": len(tracks),
            "tracks": validated_tracks,
            "found_count": found_count
        })
        
        return validated_tracks

    finally:
        await client.close()

async def listenbrainz_generate_with_progress(username: str, playlist_type: str, progress_id: str, validate: bool = True):
    # Queue is already initialized in router to prevent race conditions
    queue = lb_progress_queues.get(progress_id)
    if not queue:
        # Fallback if somehow missing
        queue = asyncio.Queue()
        lb_progress_queues[progress_id] = queue
    
    async def callback(data: Dict):
        await queue.put(data)
    
    try:
        await fetch_and_validate_listenbrainz_playlist(username, playlist_type, callback, validate)
    except Exception as e:
        log_error(f"ListenBrainz generation error: {str(e)}")
        await queue.put({
            "type": "error",
            "message": str(e),
            "progress": 0,
            "total": 0
        })
    finally:
        await queue.put(None)
