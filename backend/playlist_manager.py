
import json
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import aiofiles

from api.settings import settings, DOWNLOAD_DIR, PLAYLISTS_DIR
from api.clients import tidal_client
from api.services.files import get_output_relative_path, sanitize_path_component
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
        
        # Delete m3u8 file and cover (or entire folder if using new strategy)
        try:
            file_path = PLAYLISTS_DIR / playlist.path
            
            # Check if using Folder Strategy (Path contains a parent directory relative to PLAYLISTS_DIR)
            # playlist.path like "Name/Name.m3u8"
            if len(Path(playlist.path).parts) > 1:
                # It's in a subfolder, remove the parent folder
                parent_folder = file_path.parent
                if parent_folder.exists() and parent_folder != PLAYLISTS_DIR:
                    import shutil
                    shutil.rmtree(parent_folder)
                    logger.info(f"Deleted playlist folder: {parent_folder}")
            else:
                # Legacy: Flat file
                base_name = str(Path(playlist.path).stem)
                cover_path = PLAYLISTS_DIR / f"{base_name}.jpg"
                
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted playlist file: {file_path}")
                
                if cover_path.exists():
                    cover_path.unlink()
                    logger.info(f"Deleted playlist cover: {cover_path}")
                
        except Exception as e:
            logger.error(f"Failed to delete playlist file/cover: {e}")

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
                # Use ../../ because m3u8 is now in tidaloader_playlists/{PlaylistName}/
                m3u8_lines.append(f"../../{found_rel_path}")
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
                    m3u8_lines.append(f"../../{predicted_path}")

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
        # Folder Strategy: Create folder for playlist
        safe_name = sanitize_path_component(playlist.name)
        playlist_folder = PLAYLISTS_DIR / safe_name
        playlist_folder.mkdir(parents=True, exist_ok=True)
        
        # New M3U8 Path: {Name}/{Name}.m3u8
        m3u8_filename = f"{safe_name}.m3u8"
        playlist_file = playlist_folder / m3u8_filename
        
        try:
            async with aiofiles.open(playlist_file, 'w', encoding='utf-8') as f:
                await f.write("\n".join(m3u8_lines))
            logger.info(f"M3U8 written to {playlist_file}")
            
            # Update path in playlist object (Relative to PLAYLISTS_DIR)
            # Must use forward slash for consistency
            playlist.path = f"{safe_name}/{m3u8_filename}"
            
        except Exception as e:
            logger.error(f"Failed to write M3U8: {e}")
            
        # 5. Download playlist cover (for Media Servers)
        try:
           await self._ensure_playlist_cover(playlist, playlist_folder, safe_name)
        except Exception as e:
           logger.warning(f"Failed to ensure playlist cover: {e}")

        # Update last sync
        playlist.last_sync = datetime.now().isoformat()
        playlist.track_count = len(raw_items)
        self._save_state()
        
        return {'status': 'success', 'queued': queued_count, 'total_tracks': len(raw_items)}

    async def _ensure_playlist_cover(self, playlist: MonitoredPlaylist, folder_path: Path, safe_name: str):
        """Downloads the playlist cover image to {PlaylistFolder}/{safe_name}.jpg if missing"""
        # Target filename: {safe_name}.jpg (Same basename as m3u8)
        cover_path = folder_path / f"{safe_name}.jpg"
        
        if cover_path.exists():
            return
            
        logger.info(f"Downloading cover for playlist {playlist.name}...")
        
        try:
            pl_info = tidal_client.get_playlist(playlist.uuid)
            if not pl_info:
                logger.warning(f"No playlist info returned for {playlist.name}")
                return
            
            # Wrapper unwrapping logic
            if 'data' in pl_info:
                pl_info = pl_info['data']
            
            if 'item' in pl_info:
                pl_info = pl_info['item']
            elif 'playlist' in pl_info:
                pl_info = pl_info['playlist']

            # Robust ID extraction (like search.py)
            priority_keys = ['squareImage', 'image', 'cover', 'picture', 'imageId']
            image_guid = None
            for key in priority_keys:
                if val := pl_info.get(key):
                    image_guid = str(val).strip()
                    break
            
            if not image_guid:
                logger.warning(f"No image GUID found for playlist {playlist.name}")
                return
                
            # Construct URL (Tidal Resource URL)
            # Must split UUID with slashes: c825... -> c825/....
            image_path = image_guid.replace('-', '/')
            
            # Try 1280x1280 first (often High Res), fallback to 640x640 if needed (frontend uses various)
            # But let's stick to 640x640 as safety for now as it matched downloads.py
            image_url = f"https://resources.tidal.com/images/{image_path}/640x640.jpg"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(cover_path, 'wb') as f:
                            await f.write(await resp.read())
                        logger.info(f"Cover saved: {cover_path}")
                    else:
                        logger.warning(f"Failed cover download: {resp.status} from {image_url}")
                        
        except Exception as e:
            logger.error(f"Error downloading cover: {e}")

playlist_manager = PlaylistManager()
