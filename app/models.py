from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'super_admin', 'secretary', 'it_admin', 'servant'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    communications = relationship("Communication", back_populates="creator")
    attendance_records = relationship("Attendance", back_populates="recorder")
    created_scenarios = relationship("Scenario", back_populates="creator")
    completed_tasks = relationship("ScenarioTask", back_populates="completer")

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True) # Changed to nullable=True
    phone = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(String(50), default='active') # e.g., 'active', 'inactive', 'lead', 'customer'
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

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'Sunday', 'Tuesday', 'Special Event'
    service_date = Column(DateTime(timezone=True), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    contact = relationship("Contact")
    recorder = relationship("User", back_populates="attendance_records")

class Scenario(Base):
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    filter_tags = Column(ARRAY(String))  # ['kanana'] or ['member', 'kanana']
    status = Column(String(20), default='active')  # 'active', 'completed'
    is_deleted = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    tasks = relationship("ScenarioTask", back_populates="scenario")
    creator = relationship("User", back_populates="created_scenarios")

class ScenarioTask(Base):
    __tablename__ = "scenario_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    name = Column(String(200))
    is_completed = Column(Boolean, default=False)
    completed_by = Column(Integer, ForeignKey("users.id"))
    completed_at = Column(DateTime(timezone=True))
    
    scenario = relationship("Scenario", back_populates="tasks")
    contact = relationship("Contact")
    completer = relationship("User", back_populates="completed_tasks")
