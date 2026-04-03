"""Queue and voting routes + track search."""

import json
import urllib.parse
import urllib.request
import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.room import Room
from backend.middleware.auth import get_current_user_id
from backend.services.queue_manager import queue_manager
from backend.services.lastfm import lastfm_service
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["queue"])


@router.post("/rooms/{room_id}/queue")
async def add_to_queue(room_id: str, request: Request, db: Session = Depends(get_db)):
    user_data = get_current_user_id(request, include_name=True)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    room = db.query(Room).filter(Room.id == room_id, Room.is_active == True).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    body = await request.json()
    user_id = user_data["id"]
    user_name = user_data["display_name"]
    item = queue_manager.add_track(db, room_id, body, user_id, user_name)
    return {"item": item.to_dict()}


@router.post("/rooms/{room_id}/queue/{item_id}/vote")
async def vote_track(room_id: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    user_data = get_current_user_id(request, include_name=True)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    success = queue_manager.vote_track(db, item_id, user_data["id"])
    if not success:
        raise HTTPException(status_code=409, detail="Already voted")
    queue = queue_manager.get_queue(db, room_id)
    return {"queue": queue}


@router.get("/search/tracks")
async def search_tracks(q: str = ""):
    if not q.strip():
        return {"tracks": []}
    tracks = lastfm_service.search_tracks(q.strip())
    return {"tracks": tracks}


@router.get("/search/resolve")
async def resolve_youtube(q: str = ""):
    """Resolve a YouTube video ID from a search query — runs server-side so the API key is never exposed."""
    if not q.strip():
        return {"video_id": None}

    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        # Fallback: use noembed/invidious open API (no key, less reliable)
        return {"video_id": None, "error": "no_key"}

    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": q.strip(),
        "type": "video",
        "maxResults": 1,
        "videoCategoryId": "10",  # Music category
        "key": api_key,
    })
    try:
        req = urllib.request.Request(
            f"https://www.googleapis.com/youtube/v3/search?{params}",
            headers={"User-Agent": "OpenJam/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        video_id = data.get("items", [{}])[0].get("id", {}).get("videoId")
        return {"video_id": video_id}
    except Exception as e:
        logger.error(f"YouTube resolve error for '{q}': {e}")
        return {"video_id": None}


@router.get("/search/recommendations")
async def get_recommendations():
    """Return trending/popular tracks as search starting suggestions (no key needed)."""
    # Use iTunes top songs chart (US, no auth)
    try:
        req = urllib.request.Request(
            "https://itunes.apple.com/us/rss/topsongs/limit=20/json",
            headers={"User-Agent": "OpenJam/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        entries = data.get("feed", {}).get("entry", [])
        tracks = []
        for e in entries[:12]:
            name   = e.get("im:name", {}).get("label", "")
            artist = e.get("im:artist", {}).get("label", "")
            art100 = e.get("im:image", [{}])[-1].get("label", "")
            art    = art100.replace("55x55bb", "600x600bb").replace("170x170bb", "600x600bb")
            tracks.append({
                "name": name,
                "artist": artist,
                "album_art_url": art,
                "uri": f"{name} {artist} official audio",
                "duration_ms": 0,
            })
        return {"tracks": tracks}
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return {"tracks": []}

