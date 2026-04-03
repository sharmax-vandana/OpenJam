"""Socket.IO playback synchronization handlers — democratic control (any member can play/pause/skip)."""

import asyncio
import socketio
from backend.services.room_manager import room_manager

# Tracks which rooms have an active sync loop
_sync_tasks: dict = {}


async def _playback_sync_loop(room_id: str, sio: socketio.AsyncServer):
    """Broadcast playback state every 2 seconds to keep all clients in sync."""
    while True:
        await asyncio.sleep(2)
        playback = room_manager.get_playback(room_id)
        if not playback or not playback.get("track_uri"):
            continue
        if not playback.get("is_playing"):
            continue
        playback = dict(playback)
        playback["position_ms"] = min(
            playback.get("position_ms", 0) + 2000,
            playback.get("duration_ms", 0) or 99999999,
        )
        room_manager.update_playback(
            room_id=room_id,
            track_uri=playback["track_uri"],
            track_name=playback.get("track_name", ""),
            artist=playback.get("artist", ""),
            album_art_url=playback.get("album_art_url", ""),
            position_ms=playback["position_ms"],
            duration_ms=playback.get("duration_ms", 0),
            is_playing=True,
        )
        await sio.emit("playback_sync", room_manager.get_playback(room_id), room=room_id)


def ensure_sync_loop(room_id: str, sio: socketio.AsyncServer):
    if room_id not in _sync_tasks or _sync_tasks[room_id].done():
        _sync_tasks[room_id] = asyncio.create_task(_playback_sync_loop(room_id, sio))


def stop_sync_loop(room_id: str):
    task = _sync_tasks.pop(room_id, None)
    if task and not task.done():
        task.cancel()


def register_playback_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def sync_request(sid, data):
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = data.get("room_id") or info["room_id"]
        playback = room_manager.get_playback(room_id)
        if playback:
            await sio.emit("playback_sync", playback, to=sid)

    @sio.event
    async def playback_update(sid, data):
        """Any jam member can update playback state (democratic control)."""
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = info["room_id"]

        room_manager.update_playback(
            room_id=room_id,
            track_uri=data.get("track_uri", ""),
            track_name=data.get("track_name", ""),
            artist=data.get("artist", ""),
            album_art_url=data.get("album_art_url", ""),
            position_ms=data.get("position_ms", 0),
            duration_ms=data.get("duration_ms", 0),
            is_playing=data.get("is_playing", False),
        )
        if data.get("is_playing"):
            ensure_sync_loop(room_id, sio)
        await sio.emit("playback_sync", room_manager.get_playback(room_id), room=room_id, skip_sid=sid)

    @sio.event
    async def next_track(sid, data):
        """Any jam member can skip to the next track."""
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = info["room_id"]

        from backend.database import SessionLocal
        from backend.services.queue_manager import queue_manager

        def _advance(room_id):
            db = SessionLocal()
            try:
                next_item = queue_manager.advance_queue(db, room_id)
                queue = queue_manager.get_queue(db, room_id)
                return next_item, queue
            finally:
                db.close()

        next_item, queue = await asyncio.to_thread(_advance, room_id)

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
            ensure_sync_loop(room_id, sio)
            await sio.emit("track_changed", next_item, room=room_id)
        else:
            stop_sync_loop(room_id)
            room_manager.update_playback(room_id, "", "", "", "", 0, 0, False)
            await sio.emit("track_changed", None, room=room_id)

        await sio.emit("queue_updated", {"queue": queue}, room=room_id)

