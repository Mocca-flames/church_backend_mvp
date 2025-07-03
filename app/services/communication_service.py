from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Communication, Contact
from app.schemas import CommunicationCreate
from app.services.sms_service import sms_service
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_communication(self, communication: CommunicationCreate, user_id: int) -> Communication:
        """Create a new communication record"""
        db_communication = Communication(
            **communication.dict(),
            created_by=user_id
        )
        self.db.add(db_communication)
        self.db.commit()
        self.db.refresh(db_communication)
        return db_communication
    
    def get_recipients(self, recipient_group: str, tags: Optional[List[str]] = None) -> List[Contact]:
        """Get recipient contacts based on group type"""
        query = self.db.query(Contact)
        
        if recipient_group == "all_contacts":
            query = query.filter(Contact.opt_out_sms == False)
        elif recipient_group == "tagged" and tags:
            query = query.filter(
                and_(
                    Contact.tags.overlap(tags),
                    Contact.opt_out_sms == False
                )
            )
        
        return query.all()
    
    def send_communication(self, communication_id: int, tags: Optional[List[str]] = None, exclude_tags: Optional[List[str]] = None) -> Communication:
        """
        Send a communication via SMS.
        Enhanced to allow exclusion of contacts based on tags.
        """
        communication = self.db.query(Communication).filter(
            Communication.id == communication_id
        ).first()
        
        if not communication:
            raise ValueError("Communication not found")
        
        if communication.status != 'draft':
            raise ValueError("Communication has already been sent")
        
        # Get recipients
        recipients = self.get_recipients(communication.recipient_group, tags)
        phone_numbers = [contact.phone for contact in recipients]
        
        if not phone_numbers:
            raise ValueError("No recipients found")
        
        # Send SMS
        if communication.message_type == 'sms':
            result = sms_service.send_bulk_sms(phone_numbers, communication.message)
            
            # Update communication record
            communication.sent_count = result['total_sent']
            communication.failed_count = result['total_failed']
            communication.status = 'sent'
            communication.sent_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(communication)
            
            return communication
        else:
            raise ValueError("WhatsApp messaging not implemented yet")

    def send_bulk_sms(self, communication_id: int, phone_numbers: List[str]) -> Communication:
        """Send a communication to a specified list of phone numbers."""
        communication = self.db.query(Communication).filter(
            Communication.id == communication_id
        ).first()

        if not communication:
            raise ValueError("Communication not found")

        if communication.status != 'draft':
            raise ValueError("Communication has already been sent")

        if not phone_numbers:
            raise ValueError("No recipients found")

        # Send SMS
        if communication.message_type == 'sms':
            result = sms_service.send_bulk_sms(phone_numbers, communication.message)

            # Update communication record
            communication.sent_count = result['total_sent']
            communication.failed_count = result['total_failed']
            communication.status = 'sent'
            communication.sent_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(communication)

            return communication
        else:
            raise ValueError("WhatsApp messaging not implemented yet")
    
    def get_communications(self, user_id: Optional[int] = None) -> List[Communication]:
        """Get all communications, optionally filtered by user"""
        query = self.db.query(Communication)
        if user_id:
            query = query.filter(Communication.created_by == user_id)
        return query.order_by(Communication.created_at.desc()).all()
