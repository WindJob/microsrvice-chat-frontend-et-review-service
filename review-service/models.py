from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class ReviewStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class NotificationTypeEnum(str, enum.Enum):
    REVIEW_CREATED = "review_created"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    REVIEW_FLAGGED = "review_flagged"
    PROVIDER_REPLY = "provider_reply"
    REVIEW_REMINDER = "review_reminder"
    NEW_REVIEW = "new_review"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, nullable=False, index=True)
    provider_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    status = Column(Enum(ReviewStatusEnum), default=ReviewStatusEnum.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    edited_until = Column(DateTime, nullable=True)
    
    # Relations
    replies = relationship("ReviewReply", back_populates="review", cascade="all, delete-orphan")
    flags = relationship("ReviewFlag", back_populates="review", cascade="all, delete-orphan")


class ReviewReply(Base):
    __tablename__ = "review_replies"

    id = Column(String, primary_key=True, index=True)
    review_id = Column(String, ForeignKey("reviews.id"), nullable=False, index=True)
    provider_id = Column(String, nullable=False, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    review = relationship("Review", back_populates="replies")


class ReviewFlag(Base):
    __tablename__ = "review_flags"

    id = Column(String, primary_key=True, index=True)
    review_id = Column(String, ForeignKey("reviews.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)  # "spam", "offensive", "invalid", etc.
    reporter_id = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, dismissed
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("Review", back_populates="flags")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    provider_id = Column(String, nullable=True, index=True)
    type = Column(Enum(NotificationTypeEnum), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String, default="unread")  # unread, read
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ReviewStatistics(Base):
    __tablename__ = "review_statistics"

    id = Column(String, primary_key=True, index=True)
    provider_id = Column(String, unique=True, index=True)
    total_reviews = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    rating_1_count = Column(Integer, default=0)
    rating_2_count = Column(Integer, default=0)
    rating_3_count = Column(Integer, default=0)
    rating_4_count = Column(Integer, default=0)
    rating_5_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewInvitation(Base):
    __tablename__ = "review_invitations"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    provider_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, default="pending")  # pending, completed, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    reminder_count = Column(Integer, default=0)
