from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models import Communication, Contact
from app.schema.communication import CommunicationCreate, CommunicationUpdate
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from app.services.sms import SMS_PROVIDERS

logger = logging.getLogger(__name__)

class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
        self.providers = {}
        for provider_name, ProviderClass in SMS_PROVIDERS.items():
            try:
                self.providers[provider_name] = ProviderClass()
            except ValueError as e:
                logger.warning(f"{provider_name.capitalize()} SMS provider not initialized in CommunicationService: {e}")

        if not self.providers:
            raise ValueError("No SMS providers could be initialized in CommunicationService. Check environment variables.")

    def create_communication(self, communication: CommunicationCreate, user_id: int) -> Communication:
        db_communication = Communication(
            message_type=communication.message_type,
            recipient_group=communication.recipient_group,
            subject=communication.subject,
            message=communication.message,
            scheduled_at=communication.scheduled_at,
            metadata_=communication.metadata_,
            created_by=user_id
        )
        self.db.add(db_communication)
        self.db.commit()
        self.db.refresh(db_communication)
        return db_communication

    def update_communication(self, communication_id: int, communication_update: CommunicationUpdate) -> Optional[Communication]:
        db_communication = self.db.query(Communication).filter(Communication.id == communication_id).first()
        if not db_communication:
            return None

        update_data = communication_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_communication, key, value)

        self.db.add(db_communication)
        self.db.commit()
        self.db.refresh(db_communication)
        return db_communication

    def get_recipients(self, recipient_group: str) -> List[Contact]:
        query = self.db.query(Contact)

        if recipient_group == "all_contacts":
            query = query.filter(Contact.opt_out_sms == False)
        else:
            raise ValueError("Invalid recipient_group. Must be 'all_contacts'.")

        return query.all()

    def send_communication(self, communication_id: int, provider: Optional[str] = None) -> Communication:
        communication = self.db.query(Communication).filter(
            Communication.id == communication_id
        ).first()

        if not communication:
            raise ValueError("Communication not found")


        recipients = self.get_recipients(communication.recipient_group)
        phone_numbers = [contact.phone for contact in recipients]

        if not phone_numbers:
            raise ValueError("No recipients found")

        if communication.message_type == 'sms':
            if provider is None:
                # Select the first available provider if none is specified
                for p_name in self.providers.keys():
                    provider = p_name
                    break
                if provider is None:
                    raise ValueError("No active SMS provider available.")

            provider_instance = self.providers.get(provider)
            if not provider_instance:
                raise ValueError(f"SMS provider '{provider}' not found or not initialized.")

            # Bulk optimization for providers that support it
            if hasattr(provider_instance, 'send_bulk_sms') and len(phone_numbers) > 1:
                results = provider_instance.send_bulk_sms(phone_numbers, communication.message)
            else:
                results = []
                for phone in phone_numbers:
                    single_result = provider_instance.send_sms(phone, communication.message)
                    results.append(single_result)

            # Aggregate results from potentially different provider return formats
            sent_count = 0
            failed_count = 0
            for r in results:
                if isinstance(r, dict) and r.get("success"):
                    sent_count += 1
                elif isinstance(r, dict) and r.get("sent_count") is not None: # For bulk results
                    sent_count += r.get("sent_count", 0)
                    failed_count += r.get("failed_count", 0)
                else:
                    failed_count += 1 # Treat as failed if not explicitly successful or bulk result

            communication.sent_count = sent_count
            communication.failed_count = failed_count
            communication.status = 'sent'
            communication.sent_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(communication)
            return communication
        else:
            raise ValueError("WhatsApp messaging not implemented yet")

    def send_bulk_sms(self, communication_id: int, phone_numbers: List[str], provider: Optional[str] = None) -> Communication:
        communication = self.db.query(Communication).filter(
            Communication.id == communication_id
        ).first()

        if not communication:
            raise ValueError("Communication not found")


        if not phone_numbers:
            raise ValueError("No recipients found")

        if communication.message_type == 'sms':
            if provider is None:
                # Select the first available provider if none is specified
                for p_name in self.providers.keys():
                    provider = p_name
                    break
                if provider is None:
                    raise ValueError("No active SMS provider available.")

            provider_instance = self.providers.get(provider)
            if not provider_instance:
                raise ValueError(f"SMS provider '{provider}' not found or not initialized.")

            # Always use send_bulk_sms if available for bulk sending
            if hasattr(provider_instance, 'send_bulk_sms'):
                results = provider_instance.send_bulk_sms(phone_numbers, communication.message)
            else:
                # Fallback to individual sends if bulk is not supported
                results = []
                for phone in phone_numbers:
                    single_result = provider_instance.send_sms(phone, communication.message)
                    results.append(single_result)

            # Aggregate results from potentially different provider return formats
            sent_count = 0
            failed_count = 0
            for r in results:
                if isinstance(r, dict) and r.get("success"):
                    sent_count += 1
                elif isinstance(r, dict) and r.get("sent_count") is not None: # For bulk results
                    sent_count += r.get("sent_count", 0)
                    failed_count += r.get("failed_count", 0)
                else:
                    failed_count += 1 # Treat as failed if not explicitly successful or bulk result

            communication.sent_count = sent_count
            communication.failed_count = failed_count
            communication.status = 'sent'
            communication.sent_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(communication)
            return communication
        else:
            raise ValueError("WhatsApp messaging not implemented yet")

    def get_communications(self, user_id: Optional[int] = None) -> List[Communication]:
        query = self.db.query(Communication)
        if user_id:
            query = query.filter(Communication.created_by == user_id)
        return query.order_by(Communication.created_at.desc()).all()

    def get_sent_count_stats(self) -> Dict[str, int]:
        """
        Retrieves the total count of sent and failed communications.
        """
        total_sent = self.db.query(func.sum(Communication.sent_count)).scalar()
        total_failed = self.db.query(func.sum(Communication.failed_count)).scalar()

        # Combine sent and failed counts as requested
        combined_count = (total_sent if total_sent is not None else 0) + \
                         (total_failed if total_failed is not None else 0)

        return {
            "sent_count": combined_count
        }
