from sqlalchemy.orm import Session
import models
from datetime import datetime


def create_conversation(db: Session, title: str | None, participant_ids: list[str]):
    conv = models.Conversation(title=title)
    db.add(conv)
    db.flush()
    for pid in participant_ids:
        part = models.ConversationParticipant(conversation_id=conv.id, user_external_id=pid)
        db.add(part)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversations_for_user(db: Session, external_user_id: str):
    return (
        db.query(models.Conversation)
        .join(models.ConversationParticipant)
        .filter(models.ConversationParticipant.user_external_id == external_user_id)
        .order_by(models.Conversation.updated_at.desc())
        .all()
    )


def create_message(db: Session, conversation_id: int, sender_external_id: str, body: str | None, message_type: str = "text"):
    msg = models.Message(
        conversation_id=conversation_id,
        sender_external_id=sender_external_id,
        body=body,
        message_type=message_type,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    # update conversation updated_at
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if conv:
        conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def list_messages(db: Session, conversation_id: int, limit: int = 50, offset: int = 0):
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
