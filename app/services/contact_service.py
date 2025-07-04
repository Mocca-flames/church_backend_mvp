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
        # Clean and validate phone number
        phone = str(contact.phone).strip()
        if not phone.startswith('+'):
            phone = '+27' + phone.lstrip('0')  # Assume South African format for numbers without country code

        # Validate phone number length for South African numbers
        if phone.startswith('+27') and len(phone) != 12:
            raise ValueError(f"Invalid phone number: '{phone}'. South African numbers must have 12 characters (e.g., +27123456789).")

        contact.phone = phone
        
        db_contact = Contact(**contact.model_dump())
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
            required_columns = ['name', 'phone']
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
                    contact_data = ContactCreate(
                        name=str(row['name']).strip(),
                        phone=str(row['phone']).strip()
                    )
                    
                    self.create_contact(contact_data)
                    imported_count += 1
                    
                except IntegrityError:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: Phone number already exists")
                    self.db.rollback()
                except ValueError as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
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
                    # Phone number is essential, check for it first.
                    if not hasattr(vcard, 'tel_list') or not vcard.tel_list:
                        try:
                            name_for_error = vcard.fn.value
                        except Exception:
                            name_for_error = "an unknown contact"
                        failed_count += 1
                        errors.append(f"Card for {name_for_error} is missing a phone number.")
                        continue

                    # Try to get the name, but don't fail the whole card if it's missing/malformed.
                    try:
                        name = vcard.fn.value
                    except Exception:
                        name = None

                    for tel in vcard.tel_list:
                        phone = None
                        try:
                            phone = tel.value
                            
                            # If name was not found, use the phone number as the name.
                            contact_name = name if name else str(phone)

                            contact_data = ContactCreate(
                                name=contact_name,
                                phone=str(phone).strip()
                            )
                            
                            self.create_contact(contact_data)
                            imported_count += 1
                        
                        except IntegrityError:
                            failed_count += 1
                            errors.append(f"Contact with phone number {phone} already exists.")
                            self.db.rollback()
                        except ValueError as e:
                            failed_count += 1
                            errors.append(f"Error processing phone number {phone} for '{name or 'Unknown'}': {str(e)}")
                            self.db.rollback()
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"Error processing phone number {phone} for '{name or 'Unknown'}': {str(e)}")
                            self.db.rollback()

                except Exception as e:
                    failed_count += 1
                    # Try to get a name for the error message
                    try:
                        name_for_error = vcard.fn.value
                    except Exception:
                        name_for_error = "Unknown"
                    errors.append(f"Error processing VCard for {name_for_error}: {str(e)}")
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
