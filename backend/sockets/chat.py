"""Socket.IO chat event handlers."""

import socketio
from backend.database import SessionLocal
from backend.models.chat_message import ChatMessage
from backend.services.room_manager import room_manager


def register_chat_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def send_chat(sid, data):
        print(f"[chat] Received send_chat from {sid} with data: {data}")
        session = await sio.get_session(sid)
        print(f"[chat] Session for {sid}: {session}")
        if not session:
            print(f"[chat] Rejected: no session")
            return

        # room_id from payload first, fallback to room_manager
        room_id = data.get("room_id")
        if not room_id:
            info = room_manager.get_user_by_sid(sid)
            if not info:
                return
            room_id = info["room_id"]

        content = data.get("message", "").strip()
        if not content:
            return
        if len(content) > 500:
            content = content[:500]

        user_id = session.get("user_id")
        display_name = session.get("display_name", "Unknown")
        avatar_url = session.get("avatar_url")

        if not user_id:
            return

        db = SessionLocal()
        try:
            msg = ChatMessage(
                room_id=room_id,
                user_id=user_id,
                user_name=display_name,
                user_avatar=avatar_url,
                content=content,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            print(f"[chat] Emitting chat_message to room {room_id}: '{content[:40]}'")
            await sio.emit("chat_message", msg.to_dict(), room=room_id)
        except Exception as e:
            print(f"[chat] send_chat error: {e}")
        finally:
            db.close()
