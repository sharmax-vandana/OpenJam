"""Socket.IO chat event handlers — non-blocking DB via asyncio.to_thread()."""

import asyncio
import socketio
from datetime import datetime, timezone
from backend.database import SessionLocal
from backend.models.chat_message import ChatMessage
from backend.services.room_manager import room_manager


def _db_save_message(room_id: str, user_id: str, display_name: str, avatar_url, content: str) -> dict:
    """Synchronous DB write — runs in a thread pool, never blocks the event loop."""
    db = SessionLocal()
    try:
        msg = ChatMessage(
            room_id=room_id,
            user_id=user_id,
            user_name=display_name,
            user_avatar=avatar_url,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg.to_dict()
    finally:
        db.close()


def register_chat_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def chat_message(sid, data):
        session = await sio.get_session(sid)
        if not session:
            return

        content = (data.get("content") or "").strip()
        if not content or len(content) > 500:
            return

        info = room_manager.get_user_by_sid(sid)
        if not info:
            return

        room_id = info["room_id"]
        user_id = session.get("user_id") or f"guest_{sid}"
        display_name = session.get("display_name", "Jammer")
        avatar_url = session.get("avatar_url")

        # Run DB write in thread pool — keeps the event loop free
        msg_dict = await asyncio.to_thread(
            _db_save_message, room_id, user_id, display_name, avatar_url, content
        )

        await sio.emit("chat_message", msg_dict, room=room_id)

    @sio.event
    async def reaction(sid, data):
        """Micro-chat: broadcast an emoji reaction to the room."""
        emoji = data.get("emoji")
        if not emoji:
            return
        
        info = room_manager.get_user_by_sid(sid)
        if not info:
            return
            
        await sio.emit("room_reaction", {"emoji": emoji[:2]}, room=info["room_id"])
