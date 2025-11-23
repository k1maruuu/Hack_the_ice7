# app/routers/support_chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_user, get_admin_user
from app.schemas.schemas import (
    SupportChatResponse,
    SupportMessageBase,
    SupportMessageResponse,
    SupportChatShort,
)
from app.models.models import User, UserRole, SupportChat, SupportMessage

router = APIRouter(prefix="/support", tags=["support"])

def _ensure_chat_for_user(db: Session, user: User) -> SupportChat:
    chat = (
        db.query(SupportChat)
        .filter(SupportChat.user_id == user.id)
        .first()
    )
    if not chat:
        chat = SupportChat(user_id=user.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
    return chat

@router.get("/chats/me", response_model=SupportChatResponse)
def get_my_chat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _ensure_chat_for_user(db, current_user)
    return chat

@router.post("/chats/me/messages", response_model=SupportMessageResponse)
def send_message_to_admin(
    payload: SupportMessageBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _ensure_chat_for_user(db, current_user)
    msg = SupportMessage(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

# === ADMIN ===

@router.get("/chats", response_model=List[SupportChatShort])
def list_chats_admin(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    chats = db.query(SupportChat).all()
    result: list[SupportChatShort] = []

    for chat in chats:
        last_msg = (
            db.query(SupportMessage)
            .filter(SupportMessage.chat_id == chat.id)
            .order_by(SupportMessage.created_at.desc())
            .first()
        )
        result.append(
            SupportChatShort(
                id=chat.id,
                user_id=chat.user_id,
                user_full_name=chat.user.full_name,
                last_message=last_msg.content if last_msg else None,
                last_message_at=last_msg.created_at if last_msg else None,
            )
        )
    return result

@router.get("/chats/{chat_id}", response_model=SupportChatResponse)
def get_chat_admin(
    chat_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    chat = db.query(SupportChat).filter(SupportChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.post("/chats/{chat_id}/messages", response_model=SupportMessageResponse)
def send_message_admin(
    chat_id: int,
    payload: SupportMessageBase,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    chat = db.query(SupportChat).filter(SupportChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    msg = SupportMessage(
      chat_id=chat.id,
      sender_id=admin.id,
      content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
