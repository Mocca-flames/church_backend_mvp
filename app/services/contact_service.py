from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from app.models import Contact
from app.schemas import ContactCreate, ContactUpdate
from typing import List, Dict, Any, Optional
import pandas as pd
import io
import logging
import vobject
import json

logger = logging.getLogger(__name__)

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
        
        db_contact = Contact(
            name=contact.name,
            phone=contact.phone,
            status=contact.status,
            tags=contact.tags,
            opt_out_sms=contact.opt_out_sms,
            opt_out_whatsapp=contact.opt_out_whatsapp,
            metadata_=contact.metadata_
        )
        self.db.add(db_contact)
        self.db.commit()
        self.db.refresh(db_contact)
        return db_contact
    
    def update_contact(self, contact_id: int, contact_update: ContactUpdate) -> Optional[Contact]:
        """Update an existing contact"""
        db_contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not db_contact:
            return None
        
        update_data = contact_update.model_dump(exclude_unset=True)
        
        # Handle phone number cleaning if it's being updated
        if 'phone' in update_data and update_data['phone'] is not None:
            phone = str(update_data['phone']).strip()
            if not phone.startswith('+'):
                phone = '+27' + phone.lstrip('0')
            if phone.startswith('+27') and len(phone) != 12:
                raise ValueError(f"Invalid phone number: '{phone}'. South African numbers must have 12 characters (e.g., +27123456789).")
            update_data['phone'] = phone
            
            # Check for duplicate phone number if it's being changed
            existing_contact_with_phone = self.db.query(Contact).filter(
                Contact.phone == phone,
                Contact.id != contact_id
            ).first()
            if existing_contact_with_phone:
                raise IntegrityError(f"Contact with phone number {phone} already exists.", {}, {})

        for key, value in update_data.items():
            setattr(db_contact, key, value)
        
        self.db.add(db_contact)
        self.db.commit()
        self.db.refresh(db_contact)
        return db_contact

    def get_contacts(self, skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None, tag: Optional[str] = None) -> List[Contact]:
        """Get all contacts with pagination and optional filtering/searching"""
        query = self.db.query(Contact)
        
        if search:
            query = query.filter(
                or_(
                    Contact.name.ilike(f"%{search}%"),
                    Contact.phone.ilike(f"%{search}%")
                )
            )
        if status:
            query = query.filter(Contact.status == status)
        if tag:
            query = query.filter(Contact.tags.contains([tag]))
            
        return query.offset(skip).limit(limit).all()
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
                    # Prepare data for ContactCreate, handling optional fields
                    name = str(row.get('name', '')).strip()
                    phone = str(row.get('phone', '')).strip()
                    status = str(row.get('status', 'active')).strip()
                    tags_str = str(row.get('tags', '')).strip()
                    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
                    opt_out_sms = str(row.get('opt_out_sms', 'False')).strip().lower() == 'true'
                    opt_out_whatsapp = str(row.get('opt_out_whatsapp', 'False')).strip().lower() == 'true'
                    metadata_ = str(row.get('metadata_', '')).strip() if row.get('metadata_') else None

                    contact_data = ContactCreate(
                        name=name,
                        phone=phone,
                        status=status,
                        tags=tags,
                        opt_out_sms=opt_out_sms,
                        opt_out_whatsapp=opt_out_whatsapp,
                        metadata_=metadata_
                    )
                    
                    self.create_contact(contact_data)
                    imported_count += 1
                    
                except IntegrityError:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: Phone number already exists or other integrity error.")
                    self.db.rollback()
                except ValueError as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
                    self.db.rollback()
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: Unexpected error: {str(e)}")
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

                            # Extract other fields from VCard if available, or set defaults
                            # VCF standard doesn't have direct equivalents for 'status', 'tags', 'metadata_'
                            # We'll set sensible defaults or empty values
                            status = 'active' # Default status for VCF imports
                            tags = [] # No direct VCF field for tags
                            opt_out_sms = False # No direct VCF field
                            opt_out_whatsapp = False # No direct VCF field
                            metadata_ = None # No direct VCF field

                            contact_data = ContactCreate(
                                name=contact_name,
                                phone=str(phone).strip(),
                                status=status,
                                tags=tags,
                                opt_out_sms=opt_out_sms,
                                opt_out_whatsapp=opt_out_whatsapp,
                                metadata_=metadata_
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
