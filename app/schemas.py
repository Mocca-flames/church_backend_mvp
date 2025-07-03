from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    role: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Contact Schemas
class ContactBase(BaseModel):
    full_name: str
    phone: str
    tags: Optional[List[str]] = []
    opt_out_sms: bool = False
    opt_out_whatsapp: bool = False

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContactImport(BaseModel):
    contacts: List[ContactCreate]

# Communication Schemas
class CommunicationBase(BaseModel):
    message_type: str
    recipient_group: str
    subject: Optional[str] = None
    message: str
    scheduled_at: Optional[datetime] = None

class CommunicationCreate(CommunicationBase):
    pass

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

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
