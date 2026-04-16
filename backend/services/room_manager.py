"""In-memory room state manager for tracking active users and playback."""

from datetime import datetime, timezone


class RoomManager:
    def __init__(self):
        # {room_id: {users: {user_id: {sid, display_name, avatar_url, joined_at}}, host_sid: str, playback: {...}}}
        self._rooms: dict = {}
        # {sid: {user_id, room_id}}
        self._sid_map: dict = {}

    def join_room(self, room_id: str, user_id: str, sid: str, display_name: str, avatar_url: str = None):
        if room_id not in self._rooms:
            self._rooms[room_id] = {
                "users": {},
                "host_sid": None,
                "playback": {
                    "track_uri": None,
                    "track_name": None,
                    "artist": None,
                    "album_art_url": None,
                    "position_ms": 0,
                    "duration_ms": 0,
                    "is_playing": False,
                    "updated_at": None,
                    "skip_voters": set(),
                },
            }
        self._rooms[room_id]["users"][user_id] = {
            "sid": sid,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sid_map[sid] = {"user_id": user_id, "room_id": room_id}

    def leave_room(self, sid: str) -> dict | None:
        info = self._sid_map.pop(sid, None)
        if not info:
            return None
        room_id = info["room_id"]
        user_id = info["user_id"]
        if room_id in self._rooms:
            self._rooms[room_id]["users"].pop(user_id, None)
            if not self._rooms[room_id]["users"]:
                del self._rooms[room_id]
        return info

    def get_user_by_sid(self, sid: str) -> dict | None:
        return self._sid_map.get(sid)

    def set_host(self, room_id: str, sid: str):
        if room_id in self._rooms:
            self._rooms[room_id]["host_sid"] = sid

    def is_host(self, room_id: str, sid: str) -> bool:
        if room_id in self._rooms:
            return self._rooms[room_id]["host_sid"] == sid
        return False

    def get_host_sid(self, room_id: str) -> str | None:
        if room_id in self._rooms:
            return self._rooms[room_id]["host_sid"]
        return None

    def get_listener_count(self, room_id: str) -> int:
        if room_id in self._rooms:
            return len(self._rooms[room_id]["users"])
        return 0

    def get_listeners(self, room_id: str) -> list:
        if room_id not in self._rooms:
            return []
        return [
            {"user_id": uid, "display_name": info["display_name"], "avatar_url": info["avatar_url"]}
            for uid, info in self._rooms[room_id]["users"].items()
        ]

    def reassign_host(self, room_id: str) -> str | None:
        """Reassign host to the earliest joined active user. Returns new host_sid or None."""
        if room_id not in self._rooms:
            return None
        
        users = self._rooms[room_id]["users"]
        if not users:
            self._rooms[room_id]["host_sid"] = None
            return None
        
        # Find earliest joined user
        earliest_user = min(users.items(), key=lambda x: x[1]["joined_at"])
        new_host_sid = earliest_user[1]["sid"]
        self._rooms[room_id]["host_sid"] = new_host_sid
        return new_host_sid

    def get_host_user_id(self, room_id: str) -> str | None:
        """Get the user_id of the current host."""
        if room_id not in self._rooms:
            return None
        host_sid = self._rooms[room_id]["host_sid"]
        if not host_sid:
            return None
        user_info = self._sid_map.get(host_sid)
        return user_info["user_id"] if user_info else None

    def get_active_room_ids(self) -> list:
        return list(self._rooms.keys())

    def get_listener_counts(self) -> dict:
        return {rid: len(data["users"]) for rid, data in self._rooms.items()}

    def update_playback(self, room_id: str, track_uri: str, track_name: str, artist: str,
                        album_art_url: str, position_ms: int, duration_ms: int, is_playing: bool):
        if room_id in self._rooms:
            # Carry over old skip voters if the track uri hasn't changed (just a pause/play/seek update)
            old_pb = self._rooms[room_id].get("playback", {})
            skip_voters = set()
            if old_pb and old_pb.get("track_uri") == track_uri:
                skip_voters = old_pb.get("skip_voters", set())

            self._rooms[room_id]["playback"] = {
                "track_uri": track_uri,
                "track_name": track_name,
                "artist": artist,
                "album_art_url": album_art_url,
                "position_ms": position_ms,
                "duration_ms": duration_ms,
                "is_playing": is_playing,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "skip_voters": skip_voters,
            }

    def get_playback(self, room_id: str) -> dict | None:
        if room_id in self._rooms:
            return self._rooms[room_id]["playback"]
        return None

    def update_display_name(self, user_id: str, new_name: str):
        """Update display name for a user across all rooms they are in."""
        for room_data in self._rooms.values():
            if user_id in room_data["users"]:
                room_data["users"][user_id]["display_name"] = new_name

    def add_skip_vote(self, room_id: str, user_id: str) -> bool:
        """Returns True if the vote was added, False if already voted."""
        if room_id in self._rooms:
            pb = self._rooms[room_id].get("playback")
            if pb and user_id not in pb.get("skip_voters", set()):
                pb["skip_voters"].add(user_id)
                return True
        return False

    def reset_skip_votes(self, room_id: str):
        """Reset skip votes when track changes."""
        if room_id in self._rooms:
            pb = self._rooms[room_id].get("playback")
            if pb:
                pb["skip_voters"] = set()


room_manager = RoomManager()
