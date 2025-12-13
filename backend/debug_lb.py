
import asyncio
import httpx
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "z3r069"
BASE_URL = "https://api.listenbrainz.org/1"

async def test_endpoint(client, name, url):
    logger.info(f"--- Testing {name} ---")
    logger.info(f"URL: {url}")
    try:
        response = await client.get(url)
        logger.info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Summarize
            if "playlists" in data:
                logger.info(f"Found {len(data['playlists'])} playlists")
                for pl_wrapper in data['playlists']:
                    pl = pl_wrapper.get('playlist', {})
                    title = pl.get('title', 'Unknown')
                    identifier = pl.get('identifier', 'No ID')
                    creator = pl.get('creator', 'Unknown')
                    logger.info(f"  - {title} (Creator: {creator})")
                    logger.info(f"    ID: {identifier}")
                    
                    # If this is a weekly jam, try to fetch its tracks
                    if "Weekly Jams" in title:
                         await fetch_playlist_tracks(client, identifier)
            else:
                logger.info("Response format unknown or empty playlists list")
                # print first 200 chars
                print(str(data)[:500])
        else:
            logger.error(f"Failed: {response.text}")
    except Exception as e:
         logger.error(f"Exception: {e}")

async def fetch_playlist_tracks(client, playlist_id_url):
    # identifier might be full URL like https://listenbrainz.org/playlist/UID
    # API expects UUID
    uuid = playlist_id_url.split('/')[-1]
    url = f"{BASE_URL}/playlist/{uuid}"
    logger.info(f"  -> Fetching tracks for {uuid}...")
    
    try:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            tracks = data.get('playlist', {}).get('track', [])
            logger.info(f"  -> Found {len(tracks)} tracks")
            if tracks:
                t0 = tracks[0]
                logger.info(f"  -> First track: {t0.get('title')} by {t0.get('creator')}")
                # Check for MBID
                logger.info(f"  -> First track identifiers: {t0.get('identifier')}")
                logger.info(f"  -> First track extension: {t0.get('extension')}")
        else:
            logger.error(f"  -> Failed to get tracks: {response.status_code}")
    except Exception as e:
        logger.error(f"  -> Exception fetching tracks: {e}")

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Standard User Playlists
        await test_endpoint(client, "User Playlists", f"{BASE_URL}/user/{USERNAME}/playlists")
        
        # 2. Recommendations (This is likely the one)
        await test_endpoint(client, "User Recommendations", f"{BASE_URL}/user/{USERNAME}/playlists/recommendations")
        
        # 3. Created For (Just in case)
        await test_endpoint(client, "Playlists Created For User", f"{BASE_URL}/user/{USERNAME}/playlists/createdfor")

if __name__ == "__main__":
    asyncio.run(main())
