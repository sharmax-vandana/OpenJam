"""Queue and voting routes + track search."""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.room import Room
from backend.middleware.auth import get_current_user_id
from backend.services.queue_manager import queue_manager
from backend.services.lastfm import lastfm_service

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
