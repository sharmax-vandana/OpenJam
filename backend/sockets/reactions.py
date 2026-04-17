"""Socket.IO reaction handlers for queue items and chat messages."""

import socketio

from backend.services.room_manager import room_manager


ALLOWED_EMOJIS = {"🔥", "❤️", "😂"}
_reactions_by_room: dict[str, dict[str, dict[str, list[str]]]] = {}


def register_reaction_handlers(sio: socketio.AsyncServer):

    @sio.event
    async def react_to_item(sid, data):
        room_id = str(data.get("room_id") or "").strip()
        item_id = str(data.get("item_id") or "").strip()
        emoji = str(data.get("emoji") or "").strip()
        user_id = str(data.get("user_id") or "").strip()

        if not room_id or not item_id or not emoji or not user_id:
            return
        if emoji not in ALLOWED_EMOJIS:
            return

        info = room_manager.get_user_by_sid(sid)
        if not info or info.get("room_id") != room_id or info.get("user_id") != user_id:
            return

        room_reactions = _reactions_by_room.setdefault(room_id, {})
        item_reactions = room_reactions.setdefault(item_id, {})
        users = item_reactions.setdefault(emoji, [])

        if user_id in users:
            users.remove(user_id)
            if not users:
                item_reactions.pop(emoji, None)
        else:
            users.append(user_id)

        if not item_reactions:
            room_reactions.pop(item_id, None)

        await sio.emit(
            "reaction_updated",
            {
                "item_id": item_id,
                "reactions": room_reactions.get(item_id, {}),
            },
            room=room_id,
        )
