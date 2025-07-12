from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class CommunicationBase(BaseModel):
    message_type: str
    recipient_group: str
    subject: Optional[str] = None
    message: str
    scheduled_at: Optional[datetime] = None
    metadata_: Optional[str] = None # JSON string for flexible data

class CommunicationCreate(CommunicationBase):
    pass

class CommunicationUpdate(CommunicationBase):
    message_type: Optional[str] = None
    recipient_group: Optional[str] = None
    message: Optional[str] = None

class Communication(CommunicationBase):
    id: int
    status: str
    sent_count: int
    failed_count: int
    sent_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True
