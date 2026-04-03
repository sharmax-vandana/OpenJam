"""Room CRUD routes."""

import json
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from backend.database import get_db
from backend.models.room import Room
from backend.models.user import User
from backend.middleware.auth import get_current_user_id, require_auth
from backend.services.room_manager import room_manager
from backend.services.queue_manager import queue_manager
from backend.schemas import CreateRoomRequest, RoomListResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=RoomListResponse)
async def list_rooms(
    request: Request,
    db: Session = Depends(get_db),
    search: str = Query("", min_length=0, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    query = db.query(Room).options(selectinload(Room.host)).filter(Room.is_active == True)
    if search:
        query = query.filter(Room.name.ilike(f"%{search.strip().lower()}%"))

    total = query.count()
    rooms = query.order_by(Room.created_at.desc()).offset(skip).limit(limit).all()

    listener_counts = room_manager.get_listener_counts()
    result = []
    for room in rooms:
        host_name = room.host.display_name if room.host else "Unknown"
        now_playing = queue_manager.get_now_playing(db, room.id)
        result.append(room.to_dict(
            listener_count=listener_counts.get(room.id, 0),
            current_track=now_playing,
            host_name=host_name,
        ))
    result.sort(key=lambda r: r["listener_count"], reverse=True)
    return {"rooms": result, "total": total}


@router.post("")
async def create_room(request: Request, create_room_req: CreateRoomRequest, db: Session = Depends(get_db)):
    """Create a new room. Upserts a lightweight User record for the host."""
    user_data = get_current_user_id(request, include_name=True)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = user_data["id"]
    display_name = user_data["display_name"]

    # Ensure a User row exists so the Room FK is satisfied
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, display_name=display_name)
        db.add(user)
        db.commit()
        db.refresh(user)

    room = Room(
        name=create_room_req.name,
        host_user_id=user_id,
        genre_tags=json.dumps(create_room_req.genre_tags),
        description=create_room_req.description,
        queue_mode=create_room_req.queue_mode,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return {"room": room.to_dict(host_name=display_name)}


@router.get("/{room_id}")
async def get_room(room_id: str, request: Request, db: Session = Depends(get_db)):
    room = db.query(Room).options(selectinload(Room.host)).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    host_name = room.host.display_name if room.host else "Unknown"
    now_playing = queue_manager.get_now_playing(db, room.id)
    current_user = get_current_user_id(request, include_name=True)
    current_user_id = current_user["id"] if current_user else None
    queue = queue_manager.get_queue(db, room.id, current_user_id)
    listeners = room_manager.get_listeners(room_id)
    return {
        "room": room.to_dict(
            listener_count=room_manager.get_listener_count(room_id),
            current_track=now_playing,
            host_name=host_name,
        ),
        "queue": queue,
        "listeners": listeners,
    }


@router.delete("/{room_id}")
async def close_room(room_id: str, request: Request, db: Session = Depends(get_db)):
    user_data = get_current_user_id(request, include_name=True)
    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_user_id != user_data["id"]:
        raise HTTPException(status_code=403, detail="Only the host can close the room")
    room.is_active = False
    db.commit()
    return {"message": "Room closed"}
