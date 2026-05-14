from sqlalchemy.orm import Session
from app.models.notification_model import Notification
from typing import List

class NotificationService:
    """Business logic for notifications."""

    @staticmethod
    def create_notification(db: Session, user_id: str, title: str, message: str, type_: str) -> Notification:
        notification = Notification(
            user_id=str(user_id),
            title=title,
            message=message,
            type=type_
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def get_notifications(db: Session, user_id: str) -> List[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.user_id == str(user_id))
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .all()
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: int) -> Notification:
        notification = db.get(Notification, notification_id)
        if notification:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
        return notification
