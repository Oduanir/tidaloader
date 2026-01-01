import asyncio
import logging
import aiofiles
from pathlib import Path
from typing import List, Dict, Any
from api.state import lb_progress_queues
from api.utils.logging import log_info, log_error, log_success
from api.utils.text import fix_unicode
from api.services.search import search_track_with_fallback
from api.services.files import get_output_relative_path, sanitize_path_component
from api.settings import DOWNLOAD_DIR, PLAYLISTS_DIR
from api.clients.spotify import SpotifyClient

logger = logging.getLogger(__name__)

async def process_spotify_playlist(playlist_uuid: str, progress_id: str, should_validate: bool = False):
    queue = asyncio.Queue()
    lb_progress_queues[progress_id] = queue
    
    client = SpotifyClient()
    
    try:
        await queue.put({
            "type": "info",
            "message": f"Fetching Spotify playlist {playlist_uuid}...",
            "progress": 0,
            "total": 0
        })
        
        # specific to spotify: get tracks
        # Returns (tracks, is_limited)
        spotify_tracks, is_limited = await client.get_playlist_tracks(playlist_uuid)
        
        if not spotify_tracks:
            raise Exception("No tracks found or playlist is private/invalid.")

        total_tracks = len(spotify_tracks)
        
        limit_msg = " [Truncated to 100 due to guest limit]" if is_limited else ""
        
        # If validating, show starting validation message
        if should_validate:
             await queue.put({
                "type": "info",
                "message": f"Found {total_tracks} tracks{limit_msg}. Starting validation...",
                "progress": 0,
                "total": total_tracks
            })
        else:
            await queue.put({
                "type": "info",
                "message": f"Found {total_tracks} tracks{limit_msg}. Processing...",
                "progress": 0,
                "total": total_tracks
            })
        
        validated_tracks = []
        
        for i, s_track in enumerate(spotify_tracks, 1):
            # Clean up text
            title = fix_unicode(s_track.title)
            artist = fix_unicode(s_track.artist)
            album = fix_unicode(s_track.album) if s_track.album else None
            
            # Create a mutable object to hold results, similar to PlaylistTrack
            # We use a simple class or dict wrapper for compatibility with search_track_with_fallback
            class TrackContainer:
                def __init__(self):
                    self.title = title
                    self.artist = artist
                    self.album = album
                    self.tidal_id = None
                    self.tidal_artist_id = None
                    self.tidal_album_id = None
                    self.tidal_exists = False
                    self.cover = None
            
            track_obj = TrackContainer()
            
            if should_validate:
                display_text = f"{artist} - {title}"
                await queue.put({
                    "type": "validating",
                    "message": f"Validating: {display_text}",
                    "progress": i,
                    "total": total_tracks,
                    "current_track": {
                        "artist": artist,
                        "title": title
                    }
                })
                # Perform search
                await search_track_with_fallback(artist, title, track_obj)
                # Small delay to prevent rate limit hammering (internal queue)
                await asyncio.sleep(0.05)
            
            validated_tracks.append({
                "title": track_obj.title,
                "artist": track_obj.artist,
                "album": track_obj.album,
                "tidal_id": track_obj.tidal_id,
                "tidal_artist_id": track_obj.tidal_artist_id,
                "tidal_album_id": track_obj.tidal_album_id,
                "tidal_exists": track_obj.tidal_exists,
                "cover": track_obj.cover,
                "db_id": s_track.spotify_id # Keep original ID for reference
            })

        found_count = sum(1 for t in validated_tracks if t["tidal_exists"])
        
        await queue.put({
            "type": "complete",
            "message": f"Process complete: {found_count}/{total_tracks} matched" if should_validate else f"Fetched {total_tracks} from Spotify",
            "progress": total_tracks,
            "total": total_tracks,
            "tracks": validated_tracks,
            "found_count": found_count,
            "is_limited": is_limited
        })

    except Exception as e:
        log_error(f"Spotify processing error: {str(e)}")
        await queue.put({
            "type": "error",
            "message": str(e),
            "progress": 0,
            "total": 0
        })
    finally:
        await client.close()
        await queue.put(None) # Signal end of stream


async def generate_spotify_m3u8(playlist_name: str, tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate an m3u8 playlist file from validated Spotify tracks.
    Only includes tracks that:
    1. Have tidal_exists = True (validated on Tidal)
    2. Actually exist as downloaded files on disk
    
    Returns info about the generated playlist.
    """
    if not playlist_name or not playlist_name.strip():
        raise ValueError("Playlist name is required")
    
    if not tracks:
        raise ValueError("No tracks provided")
    
    # Filter to only tracks that exist on Tidal
    valid_tracks = [t for t in tracks if t.get('tidal_exists') and t.get('tidal_id')]
    
    if not valid_tracks:
        raise ValueError("No validated tracks found. Please check tracks on Tidal first.")
    
    logger.info(f"Generating m3u8 for '{playlist_name}' with {len(valid_tracks)}/{len(tracks)} validated tracks")
    
    # Sanitize playlist name for folder/file
    safe_name = sanitize_path_component(playlist_name.strip())
    
    # Create playlist folder structure (same as Tidal playlists)
    playlist_folder = PLAYLISTS_DIR / safe_name
    playlist_folder.mkdir(parents=True, exist_ok=True)
    
    m3u8_filename = f"{safe_name}.m3u8"
    playlist_file = playlist_folder / m3u8_filename
    
    # Build m3u8 content
    m3u8_lines = ["#EXTM3U", "# Source: Spotify"]
    included_count = 0
    skipped_count = 0
    
    for track in valid_tracks:
        title = track.get('title', 'Unknown Title')
        artist = track.get('artist', 'Unknown Artist')
        album = track.get('album', 'Unknown Album')
        
        # Build metadata to find the file path
        metadata = {
            'artist': artist,
            'album': album,
            'title': title,
            'track_number': None,  # We don't have this from Spotify data
            'album_artist': None,
            'compilation': False
        }
        
        found_rel_path = None
        
        # Check for existing files in various formats
        for ext in ['.flac', '.m4a', '.mp3', '.opus']:
            metadata['file_ext'] = ext
            rel_path = get_output_relative_path(metadata)
            full_path = DOWNLOAD_DIR / rel_path
            
            if full_path.exists():
                found_rel_path = rel_path
                logger.debug(f"Found file: {rel_path}")
                break
        
        if found_rel_path:
            # Duration is optional (we might not have it)
            duration = track.get('duration_ms', -1000) // 1000 if track.get('duration_ms') else -1
            m3u8_lines.append(f"#EXTINF:{duration},{artist} - {title}")
            # Use ../../ because m3u8 is in tidaloader_playlists/{PlaylistName}/
            m3u8_lines.append(f"../../{found_rel_path}")
            included_count += 1
        else:
            # File not downloaded yet - skip it
            logger.debug(f"File not found for: {artist} - {title}")
            skipped_count += 1
    
    if included_count == 0:
        raise ValueError("No downloaded tracks found. Please download tracks first before generating the playlist.")
    
    # Write the m3u8 file
    try:
        async with aiofiles.open(playlist_file, 'w', encoding='utf-8') as f:
            await f.write("\n".join(m3u8_lines))
        
        log_success(f"M3U8 written to {playlist_file} with {included_count} tracks")
        
        return {
            "status": "success",
            "message": f"Playlist '{playlist_name}' created with {included_count} tracks",
            "path": str(playlist_file.relative_to(PLAYLISTS_DIR)),
            "included_count": included_count,
            "skipped_count": skipped_count,
            "total_validated": len(valid_tracks)
        }
        
    except Exception as e:
        logger.error(f"Failed to write m3u8: {e}")
        raise
