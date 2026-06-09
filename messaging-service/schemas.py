from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    participants: List[str] = Field(..., min_items=1)


class ConversationOut(BaseModel):
    id: int
    title: Optional[str]
    type: str
    created_at: datetime
    updated_at: Optional[datetime]
    participants: List[str] = []

    class Config:
        orm_mode = True


class MessageCreate(BaseModel):
    body: Optional[str] = None
    message_type: Optional[str] = "text"
    location: Optional[dict] = None


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_external_id: str
    body: Optional[str]
    message_type: str
    created_at: datetime

    class Config:
        orm_mode = True


class LocationIn(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: Optional[float]
    address: Optional[str]
