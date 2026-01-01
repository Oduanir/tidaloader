import uuid
import json
import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from api.models import ListenBrainzGenerateRequest, ValidateTrackRequest
from api.auth import require_auth, require_auth_stream
from api.state import lb_progress_queues
from api.services.listenbrainz import listenbrainz_generate_with_progress
from api.services.search import search_track_with_fallback

router = APIRouter()

@router.post("/api/listenbrainz/generate")
async def generate_listenbrainz_playlist(
    request: ListenBrainzGenerateRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(require_auth)
):
    progress_id = str(uuid.uuid4())
    
    # Initialize queue here to prevent race condition
    lb_progress_queues[progress_id] = asyncio.Queue()
    
    background_tasks.add_task(
        listenbrainz_generate_with_progress,
        request.username,
        request.playlist_type,
        progress_id,
        request.should_validate
    )
    
    return {"progress_id": progress_id}

@router.post("/api/listenbrainz/validate-track")
async def validate_listenbrainz_track(
    request: ValidateTrackRequest,
    username: str = Depends(require_auth)
):
    track = request.track
    await search_track_with_fallback(track.artist, track.title, track)
    
    return {
        "title": track.title,
        "artist": track.artist,
        "mbid": track.mbid,
        "tidal_id": track.tidal_id,
        "tidal_artist_id": track.tidal_artist_id,
        "tidal_album_id": track.tidal_album_id,
        "tidal_exists": track.tidal_exists,
        "album": track.album,
        "cover": getattr(track, 'cover', None)
    }

@router.get("/api/listenbrainz/progress/{progress_id}")
async def listenbrainz_progress_stream(
    progress_id: str,
    username: str = Depends(require_auth_stream)
):
    async def event_generator():
        if progress_id not in lb_progress_queues:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid progress ID'})}\n\n"
            return
        
        queue = lb_progress_queues[progress_id]
        
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    if message is None:
                        break
                    
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    
        finally:
            if progress_id in lb_progress_queues:
                del lb_progress_queues[progress_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8"
        }
    )
