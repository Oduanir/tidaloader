
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import aiofiles

from api.settings import settings, DOWNLOAD_DIR, PLAYLISTS_DIR
from api.clients import tidal_client
from api.services.files import get_output_relative_path
# from api.utils.logging import log_info, log_error, log_warning (Using standard logger instead)
from queue_manager import queue_manager, QueueItem

logger = logging.getLogger(__name__)

# Persistence file - Store in PLAYLISTS_DIR to survive container rebuilds
MONITORED_PLAYLISTS_FILE = PLAYLISTS_DIR / "monitored_playlists.json"

@dataclass
class MonitoredPlaylist:
    uuid: str
    name: str
    path: str  # Relative path to m3u8 in PLAYLISTS_DIR (e.g. "My Playlist.m3u8")
    sync_frequency: str  # "manual", "daily", "weekly"
    last_sync: Optional[str] = None
    auto_download_tracks: bool = True
    quality: str = "LOSSLESS"
    track_count: int = 0

class PlaylistManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._playlists: List[MonitoredPlaylist] = []
        self._load_state()

    def _load_state(self):
        if MONITORED_PLAYLISTS_FILE.exists():
            try:
                with open(MONITORED_PLAYLISTS_FILE, 'r') as f:
                    data = json.load(f)
                    self._playlists = [MonitoredPlaylist(**item) for item in data.get('playlists', [])]
            except Exception as e:
                logger.error(f"Failed to load monitored playlists: {e}")

    def _save_state(self):
        try:
            logger.info(f"Saving state to {MONITORED_PLAYLISTS_FILE}")
            data = {'playlists': [asdict(p) for p in self._playlists]}
            with open(MONITORED_PLAYLISTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"State saved successfully. {len(self._playlists)} playlists.")
        except Exception as e:
            logger.error(f"Failed to save monitored playlists: {e}")

    def get_monitored_playlists(self) -> List[Dict]:
        return [asdict(p) for p in self._playlists]
    
    def get_playlist(self, uuid: str) -> Optional[MonitoredPlaylist]:
        return next((p for p in self._playlists if p.uuid == uuid), None)

    def add_monitored_playlist(self, uuid: str, name: str, frequency: str = "manual", quality: str = "LOSSLESS") -> tuple[MonitoredPlaylist, bool]:
        logger.info(f"Adding/Updating playlist: {uuid} - {name} (Freq: {frequency}, Qual: {quality})")
        # Check if exists
        existing = self.get_playlist(uuid)
        if existing:
            logger.info(f"Found existing playlist {uuid}. Updating settings.")
            existing.sync_frequency = frequency
            existing.quality = quality
            # Start sync immediately? No, caller decides.
            self._save_state()
            logger.info(f"Playlist {uuid} updated. Current list size: {len(self._playlists)}")
            return existing, False

        logger.info(f"Playlist {uuid} not found. Creating new.")
        # Sanitize name for filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_name}.m3u8"
        
        playlist = MonitoredPlaylist(
            uuid=uuid,
            name=name,
            path=filename,
            sync_frequency=frequency,
            quality=quality
        )
        self._playlists.append(playlist)
        self._save_state()
        logger.info(f"Playlist {uuid} created. Current list size: {len(self._playlists)}")
        return playlist, True

    def remove_monitored_playlist(self, uuid: str):
        playlist = self.get_playlist(uuid)
        if not playlist:
            logger.warning(f"Attempted to remove non-existent playlist {uuid}")
            return
            
        self._playlists = [p for p in self._playlists if p.uuid != uuid]
        self._save_state()
        
        # Delete m3u8 file
        try:
            file_path = PLAYLISTS_DIR / playlist.path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted playlist file: {file_path}")
            else:
                logger.warning(f"Playlist file not found for deletion: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete playlist file {playlist.path}: {e}")

    async def sync_playlist(self, uuid: str) -> Dict[str, Any]:
        playlist = self.get_playlist(uuid)
        if not playlist:
            raise ValueError("Playlist not found")

        logger.info(f"Syncing playlist: {playlist.name} ({playlist.uuid})")
        
        # 1. Fetch tracks
        try:
            result = tidal_client.get_playlist_tracks(playlist.uuid)
        except Exception as e:
            logger.error(f"Failed to fetch tracks for playlist {playlist.uuid}: {e}")
            return {'status': 'error', 'message': str(e)}
        
        # Unwrap v2 wrapper if present
        if isinstance(result, dict) and 'data' in result and 'version' in result:
            result = result['data']
            
        raw_items = []
        if isinstance(result, dict):
            if 'items' in result:
                raw_items = result.get('items', [])
            elif 'tracks' in result and isinstance(result['tracks'], dict):
                raw_items = result['tracks'].get('items', [])
            elif isinstance(result.get('tracks'), list):
                raw_items = result.get('tracks', [])
            elif isinstance(result.get('data'), list):
                raw_items = result.get('data')
        elif isinstance(result, list):
            raw_items = result
            
        logger.info(f"Fetched {len(raw_items)} raw items for playlist {playlist.uuid}")
        
        if not raw_items:
            logger.warning(f"No tracks found for playlist {playlist.name} (result type: {type(result)})")
            return {'status': 'empty', 'added': 0}

        # 2. Process tracks & M3U8 content
        m3u8_lines = ["#EXTM3U"]
        items_to_download = []
        
        for i, item in enumerate(raw_items):
            # Robust extraction logic mirrored from search.py
            track = item.get('item', item) if isinstance(item, dict) else item
            if not isinstance(track, dict) or 'id' not in track:
                continue

            album_data = track.get('album', {}) if isinstance(track.get('album'), dict) else {}
            artist_data = track.get('artist', {}) if isinstance(track.get('artist'), dict) else (track.get('artists', [{}])[0] if track.get('artists') else {})
            
            # Extract fields
            artist_name = artist_data.get('name', 'Unknown Artist')
            album_name = album_data.get('title', 'Unknown Album')
            title = track.get('title', 'Unknown Title')
            
            track_num = track.get('trackNumber') or track.get('track_number')
            if not track_num and isinstance(item, dict):
                 track_num = item.get('index')
            
            # Simple check for compilation
            album_artist_data = album_data.get('artist', {}) if isinstance(album_data, dict) else {} # Album artist might be inside album
            if not album_artist_data and isinstance(track.get('artists'), list):
                 # Fallback? No, album artist is usually specific
                 pass
            
            album_artist = album_artist_data.get('name')
            
            is_compilation = False
            if isinstance(album_data, dict):
                is_compilation = album_data.get('type') == 'COMPILATION'
            
            # Metadata structure expected by get_output_relative_path
            metadata = {
                'artist': artist_name,
                'album': album_name,
                'title': title,
                'track_number': track_num,
                'album_artist': album_artist,
                'compilation': is_compilation
            }
            
            found_rel_path = None
            
            # Check FLAC (Common default for lossless)
            metadata['file_ext'] = '.flac'
            rel_flac = get_output_relative_path(metadata)
            if (DOWNLOAD_DIR / rel_flac).exists():
                logger.info(f"Found existing file (FLAC): {rel_flac}")
                found_rel_path = rel_flac
            else:
                # logger.debug(f"File not found at: {DOWNLOAD_DIR / rel_flac}")
                # Check M4A
                metadata['file_ext'] = '.m4a'
                rel_m4a = get_output_relative_path(metadata)
                if (DOWNLOAD_DIR / rel_m4a).exists():
                    logger.info(f"Found existing file (M4A): {rel_m4a}")
                    found_rel_path = rel_m4a
                else:
                    # Check MP3
                    metadata['file_ext'] = '.mp3'
                    rel_mp3 = get_output_relative_path(metadata)
                    if (DOWNLOAD_DIR / rel_mp3).exists():
                        logger.info(f"Found existing file (MP3): {rel_mp3}")
                        found_rel_path = rel_mp3
                    # Check OPUS
                    else:
                        metadata['file_ext'] = '.opus'
                        rel_opus = get_output_relative_path(metadata)
                        if (DOWNLOAD_DIR / rel_opus).exists():
                            logger.info(f"Found existing file (OPUS): {rel_opus}")
                            found_rel_path = rel_opus

            if found_rel_path:
                duration = track.get('duration', -1)
                m3u8_lines.append(f"#EXTINF:{duration},{artist_name} - {title}")
                m3u8_lines.append(f"../{found_rel_path}")
            else:
                # File missing
                if playlist.auto_download_tracks:
                    item_id = track.get('id')
                    if not item_id:
                        logger.warning(f"Track missing ID at index {i}: {title}")
                        continue
                        
                    items_to_download.append(QueueItem(
                        track_id=item_id,
                        title=title,
                        artist=artist_name,
                        album=album_name,
                        album_artist=album_artist,
                        track_number=track_num,
                        cover=album_data.get('cover') if album_data else (track.get('cover') if isinstance(track.get('cover'), str) else None),
                        quality=playlist.quality,
                        tidal_track_id=str(item_id),
                        tidal_artist_id=str(artist_data.get('id')) if artist_data.get('id') else None,
                        tidal_album_id=str(album_data.get('id')) if album_data.get('id') else None,
                        auto_clean=True,
                        organization_template=settings.organization_template,
                        group_compilations=settings.group_compilations,
                        run_beets=settings.run_beets,
                        embed_lyrics=settings.embed_lyrics
                    ))
                    
                    target_ext = '.flac'
                    if playlist.quality in ['LOW', 'HIGH']:
                        target_ext = '.m4a'
                    
                    metadata['file_ext'] = target_ext
                    predicted_path = get_output_relative_path(metadata)
                    
                    duration = track.get('duration', -1)
                    m3u8_lines.append(f"#EXTINF:{duration},{artist_name} - {title}")
                    m3u8_lines.append(f"../{predicted_path}")

        # 3. Queue downloads
        queued_count = 0
        if items_to_download:
            logger.info(f"Adding {len(items_to_download)} missing tracks to queue")
            try:
                res = await queue_manager.add_many_to_queue(items_to_download)
                queued_count = res.get('added', 0)
                logger.info(f"Successfully queued {queued_count} tracks")
            except Exception as e:
                logger.error(f"Failed to queue tracks: {e}")
        else:
            logger.info("No missing tracks to download.")

        # 4. Write M3U8
        playlist_file = PLAYLISTS_DIR / playlist.path
        try:
            async with aiofiles.open(playlist_file, 'w', encoding='utf-8') as f:
                await f.write("\n".join(m3u8_lines))
            logger.info(f"M3U8 written to {playlist_file}")
        except Exception as e:
            logger.error(f"Failed to write M3U8: {e}")
            
        # Update last sync
        playlist.last_sync = datetime.now().isoformat()
        playlist.track_count = len(raw_items)
        self._save_state()
        
        return {'status': 'success', 'queued': queued_count, 'total_tracks': len(tracks)}

playlist_manager = PlaylistManager()
