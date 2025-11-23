from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.logging_config import logger
from app.models.models import User, Notification, UserRole
from typing import Optional


def create_notification(db: Session, user_id: int, message: str):
    if db.query(Notification).filter(Notification.user_id == user_id, Notification.message == message).first():
        return None
    db_notification = Notification(user_id=user_id, message=message)
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification




def has_block_notification(db: Session, user_id: int) -> bool:
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.message.like("%заблокирован%")
    ).first() is not None




def get_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()




def mark_notification_as_read(db: Session, notification_id: int, user_id: int):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if notification:
        notification.is_read = True
        db.commit()
        return notification
    return None
