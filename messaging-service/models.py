from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.db_postgresql import Base


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    type = Column(String(50), default="direct")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_external_id = Column(String(255), nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_muted = Column(Boolean, default=False)
    last_read_at = Column(DateTime)

    conversation = relationship("Conversation", back_populates="participants")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_external_id = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=True)
    message_type = Column(String(50), default="text")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    edited_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)

    conversation = relationship("Conversation", back_populates="messages")
    location = relationship("LocationSnapshot", back_populates="message", uselist=False, cascade="all, delete-orphan")
    receipts = relationship("MessageReadReceipt", back_populates="message", cascade="all, delete-orphan")


class LocationSnapshot(Base):
    __tablename__ = "location_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ttl_sec = Column(Integer, default=3600)

    message = relationship("Message", back_populates="location")


class MessageReadReceipt(Base):
    __tablename__ = "message_read_receipts"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    user_external_id = Column(String(255), nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    message = relationship("Message", back_populates="receipts")
