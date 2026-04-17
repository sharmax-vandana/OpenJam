"""Socket.IO playback synchronization handlers."""

import asyncio
import math
import socketio
from datetime import datetime, timezone
from backend.logger import get_logger
from backend.services.room_manager import room_manager

# Tracks which rooms have an active sync loop
_sync_tasks: dict = {}
room_votes: dict = {}
logger = get_logger(__name__)


def _threshold(total_users: int) -> int:
    if total_users <= 0:
        return 0
    if total_users == 1:
        return 1
    if total_users == 2:
        return 2
    if total_users <= 6:
        return math.ceil(0.5 * total_users)
    return math.ceil(0.65 * total_users)


def _vote_payload(room_id: str, user_id: str | None = None) -> dict:
    total_users = room_manager.get_listener_count(room_id)
    threshold = _threshold(total_users)
    voter_ids = list(room_votes.get(room_id, {}).get("votes", set()))
    votes = len(voter_ids)
    percentage = int((votes / total_users) * 100) if total_users else 0
    payload = {
        "votes": votes,
        "total_users": total_users,
        "threshold": threshold,
        "percentage": min(100, percentage),
        "voter_ids": voter_ids,
    }
    if user_id:
        payload["has_voted"] = user_id in room_votes.get(room_id, {}).get("votes", set())
    return payload


def _reset_votes(room_id: str, track_uri: str | None = None):
    existing_votes = room_votes.get(room_id, {}).get("votes")
    if existing_votes:
        existing_votes.clear()
    if track_uri:
        room_votes[room_id] = {"track_uri": track_uri, "votes": set()}
    else:
        room_votes.pop(room_id, None)


async def emit_skip_votes(room_id: str, sio: socketio.AsyncServer):
    await sio.emit("skip_votes_updated", _vote_payload(room_id), room=room_id)


async def reset_skip_votes(room_id: str, track_uri: str | None, sio: socketio.AsyncServer):
    _reset_votes(room_id, track_uri)
    await emit_skip_votes(room_id, sio)


async def _playback_sync_loop(room_id: str, sio: socketio.AsyncServer):
    """Broadcast playback state every 2 seconds, using wall-clock for accurate position."""
    last_tick = datetime.now(timezone.utc)

    while True:
        await asyncio.sleep(2)

        playback = room_manager.get_playback(room_id)
        if not playback or not playback.get("track_uri"):
            continue
        if not playback.get("is_playing"):
            continue

        # Wall-clock delta — accurate even if loop drifts
        now = datetime.now(timezone.utc)
        elapsed_ms = int((now - last_tick).total_seconds() * 1000)
        last_tick = now

        new_pos = min(
            playback.get("position_ms", 0) + elapsed_ms,
            playback.get("duration_ms", 0) or 999_999_999,
        )

        # Auto-advance when track ends
        duration = playback.get("duration_ms", 0)
        if duration and new_pos >= duration - 500:
            stop_sync_loop(room_id)
            await skip_track(room_id, sio)
            return

        # Update server-side position
        room_manager.update_playback(
            room_id=room_id,
            track_uri=playback["track_uri"],
            track_name=playback.get("track_name", ""),
            artist=playback.get("artist", ""),
            album_art_url=playback.get("album_art_url", ""),
            position_ms=new_pos,
            duration_ms=playback.get("duration_ms", 0),
            is_playing=True,
        )

        # Emit only to non-host listeners to prevent host jitter
        host_sid = room_manager.get_host_sid(room_id)
        updated = room_manager.get_playback(room_id)
        await sio.emit("playback_sync", updated, room=room_id, skip_sid=host_sid)


def ensure_sync_loop(room_id: str, sio: socketio.AsyncServer):
    if room_id not in _sync_tasks or _sync_tasks[room_id].done():
        _sync_tasks[room_id] = asyncio.create_task(_playback_sync_loop(room_id, sio))


def stop_sync_loop(room_id: str):
    task = _sync_tasks.pop(room_id, None)
    if task and not task.done():
        task.cancel()


async def skip_track(room_id: str, sio: socketio.AsyncServer):
    from backend.database import SessionLocal
    from backend.services.queue_manager import queue_manager

    def _advance(rid):
        db = SessionLocal()
        try:
            next_item = queue_manager.advance_queue(db, rid)
            queue = queue_manager.get_queue(db, rid)
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
        _reset_votes(room_id, next_item["track_uri"])
        ensure_sync_loop(room_id, sio)
        await sio.emit("track_changed", next_item, room=room_id)
    else:
        stop_sync_loop(room_id)
        room_manager.update_playback(room_id, "", "", "", "", 0, 0, False)
        _reset_votes(room_id)
        await sio.emit("track_changed", None, room=room_id)

    await sio.emit("queue_updated", {"queue": queue}, room=room_id)
    await emit_skip_votes(room_id, sio)


async def remove_user_skip_vote(room_id: str, user_id: str, sio: socketio.AsyncServer):
    if room_manager.get_listener_count(room_id) == 0:
        _reset_votes(room_id)
        await emit_skip_votes(room_id, sio)
        return
    votes = room_votes.get(room_id, {}).get("votes")
    if votes:
        votes.discard(user_id)
    await emit_skip_votes(room_id, sio)


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
        """Only the current host can update playback state."""
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = info["room_id"]
        if sid != room_manager.get_host_sid(room_id):
            logger.info(f"Ignored playback_update from non-host: {sid} in room {room_id}")
            return

        old_track_uri = (room_manager.get_playback(room_id) or {}).get("track_uri")
        new_track_uri = data.get("track_uri", "")

        room_manager.update_playback(
            room_id=room_id,
            track_uri=new_track_uri,
            track_name=data.get("track_name", ""),
            artist=data.get("artist", ""),
            album_art_url=data.get("album_art_url", ""),
            position_ms=data.get("position_ms", 0),
            duration_ms=data.get("duration_ms", 0),
            is_playing=data.get("is_playing", False),
        )
        if new_track_uri != old_track_uri:
            await reset_skip_votes(room_id, new_track_uri or None, sio)
        if data.get("is_playing"):
            ensure_sync_loop(room_id, sio)
        await sio.emit("playback_sync", room_manager.get_playback(room_id), room=room_id, skip_sid=sid)

    @sio.event
    async def vote_skip(sid, data):
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = info["room_id"]
        if data.get("room_id") and data.get("room_id") != room_id:
            return

        playback = room_manager.get_playback(room_id)
        track_uri = playback.get("track_uri") if playback else None
        if not track_uri:
            return

        user_id = info["user_id"]
        state = room_votes.get(room_id)
        if not state or state.get("track_uri") != track_uri:
            state = {"track_uri": track_uri, "votes": set()}
            room_votes[room_id] = state

        if user_id in state["votes"]:
            state["votes"].remove(user_id)
        else:
            state["votes"].add(user_id)

        total_users = room_manager.get_listener_count(room_id)
        votes_count = len(state["votes"])
        threshold = _threshold(total_users)
        print("Votes:", votes_count)
        print("Total users:", total_users)
        print("Threshold:", threshold)
        if votes_count >= threshold and threshold > 0:
            await skip_track(room_id, sio)
            return

        await sio.emit("skip_votes_updated", _vote_payload(room_id, user_id), room=room_id)

    @sio.event
    async def next_track(sid, data):
        """Only the current host can skip to the next track."""
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
        room_id = info["room_id"]
        if data.get("room_id") and data.get("room_id") != room_id:
            return
        if sid != room_manager.get_host_sid(room_id):
            logger.info(f"Ignored next_track from non-host: {sid} in room {room_id}")
            return
        await skip_track(room_id, sio)

