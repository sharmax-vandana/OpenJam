"""Queue management service — add tracks, vote, advance playback."""

from sqlalchemy.orm import Session
from backend.models.queue_item import QueueItem
from backend.models.vote import Vote


class QueueManager:
    def add_track(self, db: Session, room_id: str, track_data: dict, user_id: str, user_name: str) -> QueueItem:
        from backend.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, display_name=user_name)
            db.add(user)
            db.commit()

        max_pos = db.query(QueueItem).filter(
            QueueItem.room_id == room_id,
            QueueItem.status != "played",
        ).count()
        item = QueueItem(
            room_id=room_id,
            track_uri=track_data["uri"],
            track_name=track_data["name"],
            artist=track_data["artist"],
            album_art_url=track_data.get("album_art_url"),
            duration_ms=track_data.get("duration_ms", 0),
            added_by_user_id=user_id,
            added_by_name=user_name,
            votes=0,
            position=max_pos,
            status="pending",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def vote_track(self, db: Session, queue_item_id: str, user_id: str) -> bool:
        from backend.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, display_name="Jammer")
            db.add(user)
            db.commit()

        existing = db.query(Vote).filter(
            Vote.queue_item_id == queue_item_id,
            Vote.user_id == user_id,
        ).first()
        if existing:
            return False
        vote = Vote(queue_item_id=queue_item_id, user_id=user_id)
        db.add(vote)
        item = db.query(QueueItem).filter(QueueItem.id == queue_item_id).first()
        if item:
            item.votes += 1
        db.commit()
        return True

    def get_queue(self, db: Session, room_id: str, current_user_id: str | None = None) -> list:
        items = db.query(QueueItem).filter(
            QueueItem.room_id == room_id,
            QueueItem.status != "played",
        ).order_by(
            QueueItem.status.desc(),  # "playing" > "pending"
            QueueItem.votes.desc(),
            QueueItem.position.asc(),
        ).all()
        
        # Determine vote status
        item_dicts = []
        for item in items:
            d = item.to_dict()
            # Fetch all user_ids who voted for this item
            votes = db.query(Vote.user_id).filter(Vote.queue_item_id == item.id).all()
            d["voter_ids"] = [v[0] for v in votes]
            
            # Keep has_voted for backwards compatibility with the REST endpoint
            if current_user_id:
                d["has_voted"] = current_user_id in d["voter_ids"]
            else:
                d["has_voted"] = False
            item_dicts.append(d)
        
        return item_dicts

    def get_now_playing(self, db: Session, room_id: str) -> dict | None:
        item = db.query(QueueItem).filter(
            QueueItem.room_id == room_id,
            QueueItem.status == "playing",
        ).first()
        return item.to_dict() if item else None

    def advance_queue(self, db: Session, room_id: str) -> dict | None:
        current = db.query(QueueItem).filter(
            QueueItem.room_id == room_id,
            QueueItem.status == "playing",
        ).first()
        if current:
            current.status = "played"

        next_item = db.query(QueueItem).filter(
            QueueItem.room_id == room_id,
            QueueItem.status == "pending",
        ).order_by(
            QueueItem.votes.desc(),
            QueueItem.position.asc(),
        ).first()
        if next_item:
            next_item.status = "playing"
            db.commit()
            db.refresh(next_item)
            return next_item.to_dict()
        db.commit()
        return None


queue_manager = QueueManager()
