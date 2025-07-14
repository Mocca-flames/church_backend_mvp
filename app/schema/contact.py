from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class ContactBase(BaseModel):
    name: Optional[str] = None
    phone: str
    status: Optional[str] = 'active'
    opt_out_sms: bool = False
    opt_out_whatsapp: bool = False
    metadata_: Optional[str] = None # JSON string for flexible data

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    name: Optional[str] = None
    phone: Optional[str] = None

class ContactImport(BaseModel):
    contacts: List[ContactCreate]

class Contact(ContactBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
