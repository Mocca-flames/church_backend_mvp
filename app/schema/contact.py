from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
import json


class ContactBase(BaseModel):
    name: Optional[str] = None
    phone: str
    status: Optional[str] = 'active'
    opt_out_sms: bool = False
    opt_out_whatsapp: bool = False
    metadata_: Optional[str] = None # JSON string for flexible data

class ContactCreate(ContactBase):
    tags: Optional[List[str]] = None
    
    def model_dump(self, **kwargs):
        """Override to handle tags in metadata_"""
        data = super().model_dump(**kwargs)
        
        # If tags are provided, merge them into metadata_
        if data.get('tags'):
            metadata = {}
            if data.get('metadata_'):
                try:
                    metadata = json.loads(data['metadata_'])
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            metadata['tags'] = data['tags']
            data['metadata_'] = json.dumps(metadata)
            
        # Remove tags from the main data as it's stored in metadata_
        data.pop('tags', None)
        return data

class ContactUpdate(ContactBase):
    name: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def model_dump(self, **kwargs):
        """Override to handle tags in metadata_"""
        data = super().model_dump(**kwargs)
        
        # If tags are provided, merge them into metadata_
        if data.get('tags') is not None:  # Check for None specifically to allow empty lists
            metadata = {}
            if data.get('metadata_'):
                try:
                    metadata = json.loads(data['metadata_'])
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            metadata['tags'] = data['tags']
            data['metadata_'] = json.dumps(metadata)
            
        # Remove tags from the main data as it's stored in metadata_
        data.pop('tags', None)
        return data

class ContactImport(BaseModel):
    contacts: List[ContactCreate]

class Contact(ContactBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: Optional[List[str]] = []
    
    class Config:
        from_attributes = True
    
    @validator('tags', pre=True, always=True)
    def extract_tags_from_metadata(cls, v, values):
        """Extract tags from metadata_ field"""
        if v is not None:
            return v
            
        metadata_str = values.get('metadata_')
        if not metadata_str:
            return []
            
        try:
            metadata = json.loads(metadata_str)
            return metadata.get('tags', [])
        except (json.JSONDecodeError, TypeError):
            return []
        
class TagRequest(BaseModel):
    tags: List[str]

class BulkTagRequest(BaseModel):
    contact_ids: List[int]
    tags: List[str]