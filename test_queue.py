import asyncio
from backend.database import SessionLocal
from backend.models.room import Room
from backend.sockets.queue import _db_add_and_get_queue
from backend.services.room_manager import room_manager
from backend.services.queue_manager import queue_manager

def test_add():
    room_id = "test-room"
    db = SessionLocal()
    room = Room(id=room_id, host_user_id="host", name="Test Room")
    db.add(room)
    db.commit()
    
    room_manager._rooms[room_id] = {"users": {}, "host_sid": None, "playback": None}

    print("Adding track...")
    queue, next_item = _db_add_and_get_queue(room_id, {"uri": "xyz", "name": "hi", "artist": "art", "duration_ms": 100}, "host", "Host")
    print("Success. Next item:", next_item)

if __name__ == "__main__":
    test_add()
