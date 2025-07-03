from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Contact
from app.schemas import ContactCreate
from typing import List, Dict, Any
import pandas as pd
import io
import logging
import vobject

logger = logging.getLogger(__name__)

class ContactService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_contact(self, contact: ContactCreate) -> Contact:
        """Create a new contact"""
        db_contact = Contact(**contact.dict())
        self.db.add(db_contact)
        self.db.commit()
        self.db.refresh(db_contact)
        return db_contact
    
    def get_contacts(self, skip: int = 0, limit: int = 100) -> List[Contact]:
        """Get all contacts with pagination"""
        return self.db.query(Contact).offset(skip).limit(limit).all()
    
    def get_contact_by_phone(self, phone: str) -> Contact:
        """Get contact by phone number"""
        return self.db.query(Contact).filter(Contact.phone == phone).first()
    
    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            self.db.delete(contact)
            self.db.commit()
            return True
        return False
    
    def import_contacts_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import contacts from CSV content"""
        try:
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Validate required columns
            required_columns = ['full_name', 'phone']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f"Missing required columns: {missing_columns}"
                }
            
            # Process contacts
            imported_count = 0
            failed_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Clean phone number
                    phone = str(row['phone']).strip()
                    if not phone.startswith('+'):
                        phone = '+27' + phone.lstrip('0')  # South African format
                    
                    # Parse tags if present
                    tags = []
                    if 'tags' in row and pd.notna(row['tags']):
                        tags = [tag.strip() for tag in str(row['tags']).split(',')]
                    
                    contact_data = ContactCreate(
                        full_name=str(row['full_name']).strip(),
                        phone=phone,
                        tags=tags,
                        opt_out_sms=bool(row.get('opt_out_sms', False)),
                        opt_out_whatsapp=bool(row.get('opt_out_whatsapp', False))
                    )
                    
                    self.create_contact(contact_data)
                    imported_count += 1
                    
                except IntegrityError:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: Phone number already exists")
                    self.db.rollback()
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
                    self.db.rollback()
            
            return {
                'success': True,
                'imported_count': imported_count,
                'failed_count': failed_count,
                'errors': errors[:10]  # Limit error messages
            }
            
        except Exception as e:
            logger.error(f"CSV import error: {str(e)}")
            return {
                'success': False,
                'error': f"CSV parsing error: {str(e)}"
            }

    def import_contacts_from_vcf(self, vcf_content: str) -> Dict[str, Any]:
        """Import contacts from VCF content"""
        try:
            imported_count = 0
            failed_count = 0
            errors = []

            for vcard in vobject.readComponents(vcf_content):
                try:
                    full_name = vcard.fn.value
                    phone = None
                    if hasattr(vcard, 'tel'):
                        phone = vcard.tel.value
                    
                    if not phone:
                        failed_count += 1
                        errors.append(f"Card for {full_name} is missing a phone number.")
                        continue

                    # Clean phone number
                    phone = str(phone).strip()
                    if not phone.startswith('+'):
                        phone = '+27' + phone.lstrip('0')  # South African format

                    contact_data = ContactCreate(
                        full_name=full_name,
                        phone=phone,
                    )
                    
                    self.create_contact(contact_data)
                    imported_count += 1

                except IntegrityError:
                    failed_count += 1
                    errors.append(f"Contact with phone number {phone} already exists.")
                    self.db.rollback()
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error processing VCard: {str(e)}")
                    self.db.rollback()

            return {
                'success': True,
                'imported_count': imported_count,
                'failed_count': failed_count,
                'errors': errors[:10]
            }

        except Exception as e:
            logger.error(f"VCF import error: {str(e)}")
            return {
                'success': False,
                'error': f"VCF parsing error: {str(e)}"
            }
