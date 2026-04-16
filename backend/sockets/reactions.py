"""Socket.IO emoji reaction handlers — real-time reactions with rate limiting."""

import asyncio
import socketio
from datetime import datetime, timezone
from backend.services.room_manager import room_manager


# In-memory rate limiting: {user_id: last_reaction_timestamp}
_reaction_timestamps = {}


def register_reaction_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def send_reaction(sid, data):
        """Frontend emits 'send_reaction' with { room_id, emoji }"""
        session = await sio.get_session(sid)
        if not session:
            return

        room_id = data.get("room_id")
        emoji = data.get("emoji", "").strip()

        if not room_id or not emoji:
            return

        # Verify user is in the room
        info = room_manager.get_user_by_sid(sid)
        if not info or info["room_id"] != room_id:
            return

        user_id = session.get("user_id")
        if not user_id:
            return

        # Rate limiting: max 1 reaction per 500ms per user
        now = datetime.now(timezone.utc).timestamp()
        last_time = _reaction_timestamps.get(user_id, 0)
        if now - last_time < 0.5:  # 500ms
            return  # Rate limited

        _reaction_timestamps[user_id] = now

        # Broadcast to all users in the room
        await sio.emit("reaction_received", {
            "emoji": emoji,
            "user_id": user_id,
            "display_name": session.get("display_name", "Jammer"),
            "timestamp": now,
        }, room=room_id)