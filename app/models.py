from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'super_admin', 'secretary', 'it_admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    communications = relationship("Communication", back_populates="creator")

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(String(50), default='active') # e.g., 'active', 'inactive', 'lead', 'customer'
    tags = Column(ARRAY(String), default=[]) # For flexible grouping
    opt_out_sms = Column(Boolean, default=False)
    opt_out_whatsapp = Column(Boolean, default=False)
    metadata_ = Column(Text) # Store JSON string for flexible data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(Integer, primary_key=True, index=True)
    message_type = Column(String(20), nullable=False)  # 'sms', 'whatsapp'
    recipient_group = Column(String(50), nullable=False)  # 'all_contacts', 'tagged', 'custom'
    subject = Column(String(200))
    message = Column(Text, nullable=False)
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    status = Column(String(20), default='draft')  # 'draft', 'scheduled', 'sent', 'failed'
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    metadata_ = Column(Text) # Store JSON string for flexible data
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    creator = relationship("User", back_populates="communications")
