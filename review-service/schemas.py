from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ReviewStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class ReviewCreate(BaseModel):
    order_id: str
    provider_id: str
    user_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewReplyCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


class ReviewReplyOut(BaseModel):
    id: str
    review_id: str
    provider_id: str
    text: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewOut(BaseModel):
    id: str
    order_id: str
    provider_id: str
    user_id: str
    rating: int
    comment: Optional[str]
    status: ReviewStatusEnum
    created_at: datetime
    updated_at: datetime
    edited_until: Optional[datetime]
    replies: List[ReviewReplyOut] = []

    class Config:
        from_attributes = True


class ReviewListOut(BaseModel):
    id: str
    provider_id: str
    user: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    status: ReviewStatusEnum

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: str
    user_id: str
    provider_id: Optional[str]
    type: str
    title: str
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewStatisticsOut(BaseModel):
    provider_id: str
    count: int
    average_rating: float
    rating_distribution: dict

    class Config:
        from_attributes = True


class ReviewFlagCreate(BaseModel):
    reason: str
    reporter_id: Optional[str] = None


class ReviewInvitationCreate(BaseModel):
    order_id: str
    provider_id: str
    user_id: str


class ReviewInvitationOut(BaseModel):
    id: str
    order_id: str
    provider_id: str
    user_id: str
    status: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True
