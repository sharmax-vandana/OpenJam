"""Socket.IO queue event handlers — all members can add tracks and vote."""

import socketio
from backend.database import SessionLocal
from backend.services.room_manager import room_manager
from backend.services.queue_manager import queue_manager


def register_queue_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def add_to_queue(sid, data):
        session = await sio.get_session(sid)
        if not session:
            return

        room_id = data.get("room_id")
        if not room_id:
            info = room_manager.get_user_by_sid(sid)
            if not info:
                return
            room_id = info["room_id"]

        user_id = session.get("user_id") or f"guest_{sid}"
        display_name = session.get("display_name", "Jammer")

        track_data = {
            "uri": data.get("track_uri", ""),
            "name": data.get("track_name", ""),
            "artist": data.get("artist", ""),
            "album_art_url": data.get("album_art_url"),
            "duration_ms": data.get("duration_ms", 0),
        }

        db = SessionLocal()
        try:
            queue_manager.add_track(db, room_id, track_data, user_id, display_name)
            queue = queue_manager.get_queue(db, room_id, None)

            # Auto-play if nothing is currently playing
            now_playing = queue_manager.get_now_playing(db, room_id)
            if not now_playing:
                next_item = queue_manager.advance_queue(db, room_id)
                if next_item:
                    room_manager.update_playback(
                        room_id=room_id,
                        track_uri=next_item["track_uri"],
                        track_name=next_item["track_name"],
                        artist=next_item["artist"],
                        album_art_url=next_item.get("album_art_url", ""),
                        position_ms=0,
                        duration_ms=next_item.get("duration_ms", 0),
                        is_playing=True,
                    )
                    from backend.sockets.playback import ensure_sync_loop
                    ensure_sync_loop(room_id, sio)
                    await sio.emit("track_changed", next_item, room=room_id)
                    queue = queue_manager.get_queue(db, room_id)
        except Exception as e:
            print(f"[queue] add_to_queue error: {e}")
            return
        finally:
            db.close()

        await sio.emit("queue_updated", {"queue": queue}, room=room_id)

    @sio.event
    async def vote_track(sid, data):
        session = await sio.get_session(sid)
        if not session:
            return

        room_id = data.get("room_id")
        if not room_id:
            info = room_manager.get_user_by_sid(sid)
            if not info:
                return
            room_id = info["room_id"]

        queue_item_id = data.get("queue_item_id")
        if not queue_item_id:
            return

        user_id = session.get("user_id") or f"guest_{sid}"

        db = SessionLocal()
        try:
            queue_manager.vote_track(db, queue_item_id, user_id)
            queue = queue_manager.get_queue(db, room_id, None)
        except Exception as e:
            print(f"[queue] vote_track error: {e}")
            return
        finally:
            db.close()

        await sio.emit("queue_updated", {"queue": queue}, room=room_id)
