from sqlalchemy.orm import Session # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore
from sqlalchemy import or_ # pyright: ignore[reportMissingImports]
from app.models import Contact
from app.schema.contact import ContactCreate, ContactUpdate
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd # type: ignore
import io
import logging
import vobject # pyright: ignore[reportMissingModuleSource]
import json
import re

logger = logging.getLogger(__name__)

class ContactService:
    def __init__(self, db: Session):
        self.db = db

    def _clean_and_validate_phone(self, phone: str) -> str:
        """
        Cleans and validates a phone number.
        
        Supports:
        - South African: 0XXXXXXXXX (10 digits), 27XXXXXXXXX (11 digits), +27XXXXXXXXX (12 chars)
        - International: +1XXXXXXXXXX (US/Canada), +44XXXXXXXXXX (UK), etc.
        - Various formats with spaces/dashes: +27 71 234 5678, 071-234-5678, etc.
        
        Raises ValueError for invalid formats or empty numbers.
        """
        if not phone:
            raise ValueError("Phone number is required.")
            
        original_phone = phone
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)

        if not digits_only:
            raise ValueError("Phone number cannot be empty.")

        # Handle South African numbers
        if original_phone.startswith('0') or original_phone.startswith('+27') or original_phone.startswith('27'):
            if original_phone.startswith('0'):
                if len(digits_only) == 10 and digits_only.startswith('0'):
                    formatted_phone = '+27' + digits_only[1:]
                else:
                    raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '0' must be 10 digits long (e.g., 0712345678).")
            elif original_phone.startswith('27'):
                if len(digits_only) == 11 and digits_only.startswith('27'):
                    formatted_phone = '+' + digits_only
                else:
                    raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '27' must be 11 digits long (e.g., 271234567890).")
            elif original_phone.startswith('+27'):
                if len(digits_only) == 11 and digits_only.startswith('27'):
                    formatted_phone = '+' + digits_only
                else:
                    raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Must be +27 followed by 9 digits (e.g., +27123456789).")
            
            # Final check for South African format
            if len(formatted_phone) != 12:
                raise ValueError(f"Internal error: Formatted phone number '{formatted_phone}' has incorrect length. Expected 12 characters (+27XXXXXXXXX).")
            
            return formatted_phone
        
        # Handle international numbers (with + prefix)
        if original_phone.startswith('+'):
            # Keep the + and validate the rest
            country_code = digits_only[:1]  # First digit is country code
            if len(digits_only) < 10:
                raise ValueError(f"Invalid international phone number: '{original_phone}'. Must have at least 10 digits.")
            # Return as-is for international numbers, just ensure it starts with +
            return '+' + digits_only
        
        # If it doesn't start with 0, +27, 27, or +, it's likely a local number without country code
        # Try to interpret as South African local number (9 digits)
        if len(digits_only) == 9:
            # Assume it's a local SA number without the 0 prefix
            return '+27' + digits_only
        
        # If we get here, the format is not recognized
        raise ValueError(
            f"Unrecognized phone number format: '{original_phone}'. "
            f"Supported formats: 0712345678 (local SA), +27123456789 (international SA), +1234567890 (international)."
        )

    def _get_contact_metadata(self, contact: Contact) -> Dict[str, Any]:
        """Get contact metadata as a dictionary"""
        if not contact.metadata_:
            return {}
        try:
            return json.loads(contact.metadata_)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _set_contact_metadata(self, contact: Contact, metadata: Dict[str, Any]) -> None:
        """Set contact metadata from dictionary"""
        contact.metadata_ = json.dumps(metadata) if metadata else None

    def _get_contact_tags(self, contact: Contact) -> List[str]:
        """Get tags for a contact"""
        metadata = self._get_contact_metadata(contact)
        return metadata.get('tags', [])

    def _set_contact_tags(self, contact: Contact, tags: List[str]) -> None:
        """Set tags for a contact"""
        metadata = self._get_contact_metadata(contact)
        # Clean and deduplicate tags
        cleaned_tags = list(set([tag.strip() for tag in tags if tag.strip()]))
        metadata['tags'] = cleaned_tags
        self._set_contact_metadata(contact, metadata)

    def create_contact(self, contact: ContactCreate, created_by: int = None) -> Contact:
        """Create a new contact"""
        # Clean and validate phone number
        contact.phone = self._clean_and_validate_phone(contact.phone)
        
        db_contact = Contact(
            name=contact.name if contact.name else contact.phone,
            phone=contact.phone,
            status=contact.status,
            opt_out_sms=contact.opt_out_sms,
            opt_out_whatsapp=contact.opt_out_whatsapp,
            metadata_=contact.metadata_,
            created_by=created_by
        )
        try:
            self.db.add(db_contact)
            self.db.commit()
            self.db.refresh(db_contact)
            return db_contact
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Contact with phone number {contact.phone} already exists.")
        except Exception as e:
            self.db.rollback()
            raise e

    def upsert_contact(self, contact: ContactCreate, created_by: int = None, updated_by: int = None) -> Contact:
        """
        Create or update a contact.
        
        If contact exists by phone:
        - Update name if provided
        - Merge tags (add new tags, keep existing)
        - Update status if provided
        - Update opt_out settings if provided
        
        If contact doesn't exist:
        - Create new contact
        
        This is ideal for device sync scenarios where offline contacts are synced.
        """
        # Clean and validate phone number
        contact.phone = self._clean_and_validate_phone(contact.phone)
        
        # Check if contact already exists
        existing_contact = self.db.query(Contact).filter(Contact.phone == contact.phone).first()
        
        if existing_contact:
            # Update existing contact
            existing_contact.updated_at = datetime.utcnow()
            existing_contact.updated_by = updated_by
            
            # Update name if provided (prefer non-empty names)
            if contact.name:
                existing_contact.name = contact.name
            elif not existing_contact.name:
                # If no name on server and new contact has no name, use phone
                existing_contact.name = contact.phone
            
            # Update status if provided
            if contact.status:
                existing_contact.status = contact.status
            
            # Update opt_out settings if provided
            if hasattr(contact, 'opt_out_sms'):
                existing_contact.opt_out_sms = contact.opt_out_sms
            if hasattr(contact, 'opt_out_whatsapp'):
                existing_contact.opt_out_whatsapp = contact.opt_out_whatsapp
            
            # Merge tags from incoming contact with existing tags
            existing_tags = self._get_contact_tags(existing_contact)
            new_tags = contact.tags if contact.tags else []
            # Add new tags that don't already exist
            merged_tags = list(set(existing_tags + new_tags))
            self._set_contact_tags(existing_contact, merged_tags)
            
            # Update metadata if provided
            if contact.metadata_:
                existing_metadata = self._get_contact_metadata(existing_contact)
                try:
                    incoming_metadata = json.loads(contact.metadata_)
                except (json.JSONDecodeError, TypeError):
                    incoming_metadata = {}
                
                # Merge metadata (incoming overwrites existing)
                merged_metadata = {**existing_metadata, **incoming_metadata}
                self._set_contact_metadata(existing_contact, merged_metadata)
            
            try:
                self.db.add(existing_contact)
                self.db.commit()
                self.db.refresh(existing_contact)
                return existing_contact
            except Exception as e:
                self.db.rollback()
                raise e
        else:
            # Create new contact
            db_contact = Contact(
                name=contact.name if contact.name else contact.phone,
                phone=contact.phone,
                status=contact.status,
                opt_out_sms=contact.opt_out_sms,
                opt_out_whatsapp=contact.opt_out_whatsapp,
                metadata_=contact.metadata_,
                created_by=created_by
            )
            try:
                self.db.add(db_contact)
                self.db.commit()
                self.db.refresh(db_contact)
                return db_contact
            except Exception as e:
                self.db.rollback()
                raise e

    def sync_contacts(self, contacts: List[ContactCreate], user_id: int = None) -> Dict[str, Any]:
        """
        Bulk sync contacts - creates new or updates existing.
        
        This endpoint is designed for device sync scenarios where:
        - Device was offline with local database
        - Now syncing all contacts to server
        - Some contacts are new, some existing (by phone)
        
        Returns summary with created/updated/failed counts.
        """
        created_count = 0
        updated_count = 0
        failed_count = 0
        errors = []
        
        for contact_data in contacts:
            try:
                result = self.upsert_contact(contact_data, created_by=user_id, updated_by=user_id)
                # Check if it was created or updated (we can check if it's a new ID or existing)
                # Since we don't have the original state, we just count as upserted
                created_count += 1
            except Exception as e:
                failed_count += 1
                error_detail = str(e)
                errors.append({
                    'phone': contact_data.phone,
                    'error': error_detail
                })
                # Log validation errors at service level for debugging
                logger.warning(
                    f"Contact sync failed for phone={contact_data.phone}: {error_detail}"
                )
        
        return {
            'success': True,
            'synced_count': created_count,  # Total contacts processed
            'created_count': 'N/A',  # Can't determine without before/after comparison
            'updated_count': 'N/A',
            'failed_count': failed_count,
            'errors': errors[:20]  # Limit error messages
        }
    
    def update_contact(self, contact_id: int, contact_update: ContactUpdate, updated_by: int = None) -> Optional[Contact]:
        """Update an existing contact"""
        db_contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not db_contact:
            return None

        update_data = contact_update.model_dump(exclude_unset=True)

        # Handle phone number cleaning and validation if it's being updated
        if 'phone' in update_data and update_data['phone'] is not None:
            new_phone = self._clean_and_validate_phone(update_data['phone'])
            update_data['phone'] = new_phone

            # Check for duplicate phone number if it's being changed to an existing one
            existing_contact_with_phone = self.db.query(Contact).filter(
                Contact.phone == new_phone,
                Contact.id != contact_id
            ).first()
            if existing_contact_with_phone:
                raise IntegrityError(f"Contact with phone number {new_phone} already exists.", {}, {})

        for key, value in update_data.items():
            setattr(db_contact, key, value)
        
        # Set updated_by if provided
        if updated_by:
            db_contact.updated_by = updated_by

        try:
            self.db.add(db_contact)
            self.db.commit()
            self.db.refresh(db_contact)
            return db_contact
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Update failed: Contact with phone number {update_data['phone']} already exists.")
        except Exception as e:
            self.db.rollback()
            raise e

    def update_contact_by_phone(self, phone: str, contact_update: ContactUpdate, updated_by: int = None) -> Optional[Contact]:
        """Update an existing contact by phone number"""
        db_contact = self.db.query(Contact).filter(Contact.phone == phone).first()
        if not db_contact:
            return None

        update_data = contact_update.model_dump(exclude_unset=True)

        # Handle phone number cleaning and validation if it's being updated
        if 'phone' in update_data and update_data['phone'] is not None:
            new_phone = self._clean_and_validate_phone(update_data['phone'])
            update_data['phone'] = new_phone

            # Check for duplicate phone number if it's being changed to an existing one
            existing_contact_with_phone = self.db.query(Contact).filter(
                Contact.phone == new_phone,
                Contact.id != db_contact.id
            ).first()
            if existing_contact_with_phone:
                raise IntegrityError(f"Contact with phone number {new_phone} already exists.", {}, {})

        for key, value in update_data.items():
            setattr(db_contact, key, value)
        
        # Set updated_by if provided
        if updated_by:
            db_contact.updated_by = updated_by

        try:
            self.db.add(db_contact)
            self.db.commit()
            self.db.refresh(db_contact)
            return db_contact
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Update failed: Contact with phone number {update_data['phone']} already exists.")
        except Exception as e:
            self.db.rollback()
            raise e

    def get_contacts(
            self, skip: int = 0, limit: int = 500, search: Optional[str] = None, 
            status: Optional[str] = None, tags: Optional[List[str]] = None,
            created_after: Optional[datetime] = None, created_before: Optional[datetime] = None,
            updated_after: Optional[datetime] = None, updated_before: Optional[datetime] = None) -> List[Contact]:
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
        
        # Filter by created date range
        if created_after:
            query = query.filter(Contact.created_at >= created_after)
        if created_before:
            query = query.filter(Contact.created_at <= created_before)
        
        # Filter by updated date range
        if updated_after:
            query = query.filter(Contact.updated_at >= updated_after)
        if updated_before:
            query = query.filter(Contact.updated_at <= updated_before)
        
        contacts = query.offset(skip).limit(limit).all()
        
        # Filter by tags if specified
        if tags:
            filtered_contacts = []
            for contact in contacts:
                contact_tags = self._get_contact_tags(contact)
                # Check if contact has any of the specified tags
                if any(tag in contact_tags for tag in tags):
                    filtered_contacts.append(contact)
            return filtered_contacts
            
        return contacts
    
    def get_contacts_in_date_range(
            self, 
            start_date: datetime, 
            end_date: datetime, 
            limit: int = 5000) -> Dict[str, Any]:
        """
        Get contacts that were created or modified within a date range.
        
        Returns:
            Dict with:
            - new_contacts: contacts created within the range
            - modified_contacts: contacts updated within range (excluding those created in range)
            - statistics: counts and percentages
        """
        # Get contacts created within range
        new_query = self.db.query(Contact).filter(
            Contact.created_at >= start_date,
            Contact.created_at <= end_date
        ).limit(limit)
        new_contacts = new_query.all()
        
        # Get contacts updated within range
        modified_query = self.db.query(Contact).filter(
            Contact.updated_at >= start_date,
            Contact.updated_at <= end_date
        ).limit(limit)
        modified_contacts = modified_query.all()
        
        # Get IDs of new contacts to exclude from modified
        new_contact_ids = {c.id for c in new_contacts}
        
        # Filter out new contacts from modified list
        truly_modified_contacts = [c for c in modified_contacts if c.id not in new_contact_ids]
        
        # Build statistics
        total_new = len(new_contacts)
        total_modified = len(truly_modified_contacts)
        total = total_new + total_modified
        
        return {
            'new_contacts': new_contacts,
            'modified_contacts': truly_modified_contacts,
            'statistics': {
                'new_count': total_new,
                'modified_count': total_modified,
                'total': total,
                'new_percentage': round((total_new / total * 100), 1) if total > 0 else 0,
                'modified_percentage': round((total_modified / total * 100), 1) if total > 0 else 0,
            }
        }
    
    def get_contact_by_phone(self, phone: str) -> Contact:
        """Get contact by phone number"""
        return self.db.query(Contact).filter(Contact.phone == phone).first()
    
    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact and all related records"""
        from app.models import Attendance, ScenarioTask
        
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return False
        
        # Check for related records before deletion
        attendance_count = self.db.query(Attendance).filter(Attendance.contact_id == contact_id).count()
        task_count = self.db.query(ScenarioTask).filter(ScenarioTask.contact_id == contact_id).count()
        
        logger.info(f"Deleting contact {contact_id}: Found {attendance_count} attendance records, {task_count} scenario tasks")
        
        # Delete related attendance records
        if attendance_count > 0:
            self.db.query(Attendance).filter(Attendance.contact_id == contact_id).delete(synchronize_session=False)
            logger.info(f"Deleted {attendance_count} attendance records for contact {contact_id}")
        
        # Delete related scenario tasks
        if task_count > 0:
            self.db.query(ScenarioTask).filter(ScenarioTask.contact_id == contact_id).delete(synchronize_session=False)
            logger.info(f"Deleted {task_count} scenario tasks for contact {contact_id}")
        
        # Now delete the contact
        self.db.delete(contact)
        self.db.commit()
        logger.info(f"Successfully deleted contact {contact_id}")
        return True

    def add_tags_to_contact(self, contact_id: int, tags: List[str]) -> Optional[Contact]:
        """Add tags to a contact"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return None
        
        current_tags = self._get_contact_tags(contact)
        # Add new tags to existing ones
        all_tags = list(set(current_tags + [tag.strip() for tag in tags if tag.strip()]))
        self._set_contact_tags(contact, all_tags)
        
        try:
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
            return contact
        except Exception as e:
            self.db.rollback()
            raise e

    def remove_tags_from_contact(self, contact_id: int, tags: List[str]) -> Optional[Contact]:
        """Remove tags from a contact"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return None
        
        current_tags = self._get_contact_tags(contact)
        # Remove specified tags
        updated_tags = [tag for tag in current_tags if tag not in tags]
        self._set_contact_tags(contact, updated_tags)
        
        try:
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
            return contact
        except Exception as e:
            self.db.rollback()
            raise e

    def set_contact_tags(self, contact_id: int, tags: List[str]) -> Optional[Contact]:
        """Set tags for a contact (replaces all existing tags)"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return None
        
        # Clean and set tags
        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        self._set_contact_tags(contact, cleaned_tags)
        
        try:
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
            return contact
        except Exception as e:
            self.db.rollback()
            raise e

    def get_contact_tags(self, contact_id: int) -> Optional[List[str]]:
        """Get tags for a specific contact"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return None
        return self._get_contact_tags(contact)

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all contacts"""
        contacts = self.db.query(Contact).all()
        all_tags = set()
        
        for contact in contacts:
            contact_tags = self._get_contact_tags(contact)
            all_tags.update(contact_tags)
        
        return sorted(list(all_tags))

    def get_tag_statistics(self) -> Dict[str, int]:
        """Get statistics of tag usage (tag name -> count)"""
        contacts = self.db.query(Contact).all()
        tag_counts = {}
        
        for contact in contacts:
            contact_tags = self._get_contact_tags(contact)
            for tag in contact_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return dict(sorted(tag_counts.items()))

    def bulk_add_tags(self, contact_ids: List[int], tags: List[str]) -> Dict[str, Any]:
        """Add tags to multiple contacts"""
        success_count = 0
        failed_ids = []
        
        for contact_id in contact_ids:
            try:
                result = self.add_tags_to_contact(contact_id, tags)
                if result:
                    success_count += 1
                else:
                    failed_ids.append(contact_id)
            except Exception:
                failed_ids.append(contact_id)
        
        return {
            'success_count': success_count,
            'failed_count': len(failed_ids),
            'failed_ids': failed_ids,
            'tags_added': tags
        }

    def bulk_remove_tags(self, contact_ids: List[int], tags: List[str]) -> Dict[str, Any]:
        """Remove tags from multiple contacts"""
        success_count = 0
        failed_ids = []
        
        for contact_id in contact_ids:
            try:
                result = self.remove_tags_from_contact(contact_id, tags)
                if result:
                    success_count += 1
                else:
                    failed_ids.append(contact_id)
            except Exception:
                failed_ids.append(contact_id)
        
        return {
            'success_count': success_count,
            'failed_count': len(failed_ids),
            'failed_ids': failed_ids,
            'tags_removed': tags
        }
    
    def import_contacts_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import contacts from CSV content"""
        try:
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
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
                    
                    # Handle metadata and tags
                    metadata_str = str(row.get('metadata_', '')).strip() if row.get('metadata_') else None
                    metadata = {}
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    # Add tags to metadata
                    if tags:
                        metadata['tags'] = tags
                    
                    final_metadata = json.dumps(metadata) if metadata else None

                    contact_data = ContactCreate(
                        name=name if name else phone, # Use phone as name if name is empty
                        phone=phone,
                        status=status,
                        opt_out_sms=opt_out_sms,
                        opt_out_whatsapp=opt_out_whatsapp,
                        metadata_=final_metadata
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
            skipped_count = 0  # Count of contacts that already exist (by phone)
            failed_count = 0  # Count of contacts that failed (invalid phone, etc.)
            errors = []

            # Split VCF content into individual vCard strings and parse each one
            # This allows us to skip malformed vCards gracefully
            vcard_strings = vcf_content.split('BEGIN:VCARD')
            
            for vcard_str in vcard_strings:
                if not vcard_str.strip():
                    continue
                
                # Re-add the BEGIN:VCARD header that was removed by split
                vcard_str = 'BEGIN:VCARD' + vcard_str
                
                try:
                    # Try to parse this single vCard
                    vcard_list = list(vobject.readComponents(vcard_str))
                    if not vcard_list:
                        continue
                        
                    vcard = vcard_list[0]
                except Exception as e:
                    # Skip malformed vCard and continue
                    logger.warning(f"Skipping malformed vCard: {str(e)}")
                    failed_count += 1
                    continue

                try:
                    # Phone number is essential, check for it first.
                    if not hasattr(vcard, 'tel_list') or not vcard.tel_list:
                        failed_count += 1
                        errors.append(f"Card is missing a phone number.")
                        continue

                    # IGNORE names from VCF - only use phone numbers
                    # This prevents unprofessional names like "Wifey" from Samsung/Google contacts
                    # from overwriting existing contact names

                    for tel in vcard.tel_list:
                        phone = None
                        try:
                            phone = tel.value
                            
                            # Always use phone number as name - never use VCF name
                            # This ensures professional and consistent naming
                            contact_name = str(phone)

                            # Extract other fields from VCard if available, or set defaults
                            # VCF standard doesn't have direct equivalents for 'status', 'tags', 'metadata_'
                            # We'll set sensible defaults or empty values
                            status = 'active' # Default status for VCF imports
                            opt_out_sms = False # No direct VCF field
                            opt_out_whatsapp = False # No direct VCF field
                            metadata_ = None # No direct VCF field

                            contact_data = ContactCreate(
                                name=contact_name,
                                phone=str(phone).strip(),
                                status=status,
                                opt_out_sms=opt_out_sms,
                                opt_out_whatsapp=opt_out_whatsapp,
                                metadata_=metadata_
                            )
                            
                            self.create_contact(contact_data)
                            imported_count += 1
                        
                        except IntegrityError:
                            # Contact already exists - skip gracefully, do NOT update
                            # This prevents overwriting existing contact names with unprofessional VCF names
                            self.db.rollback()
                            skipped_count += 1
                            # No error added - skipping existing contacts is expected behavior
                        except ValueError as e:
                            failed_count += 1
                            errors.append(f"Error processing phone number {phone}: {str(e)}")
                            self.db.rollback()
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"Error processing phone number {phone}: {str(e)}")
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
                'skipped_count': skipped_count,  # Contacts that already exist (by phone)
                'failed_count': failed_count,      # Contacts with invalid phone numbers
                'errors': errors[:10]
            }

        except Exception as e:
            logger.error(f"VCF import error: {str(e)}")
            return {
                'success': False,
                'error': f"VCF parsing error: {str(e)}"
            }

    def get_dashboard_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics including tag categories and new/modified contact counts.
        
        Args:
            date_from: Start date for filtering new/modified contacts (optional)
            date_to: End date for filtering new/modified contacts (optional)
            
        Returns:
            Dict containing total_contacts, locations, roles, membership, new_contacts, modified_contacts
            
        Note: If no date parameters provided, new_contacts and modified_contacts return all-time counts.
        """
        from datetime import timedelta
        
        # Determine if date filtering is requested
        has_date_filter = date_from is not None or date_to is not None
        
        # If no dates provided, use all-time (no filter on new/modified counts)
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = datetime(1970, 1, 1)  # Beginning of time for all-time counts
        
        # Get all contacts for tag analysis
        all_contacts = self.db.query(Contact).all()
        total_contacts = len(all_contacts)
        
        # Fixed role tags
        ROLE_TAGS = {'pastor', 'protocol', 'worshiper', 'usher', 'financier', 'servant'}
        
        # Fixed location tags (hardcoded)
        LOCATION_TAGS = {'kanana', 'majaneng', 'mashemong', 'soshanguve', 'kekana'}
        
        # Initialize counters
        location_counts = {}
        role_counts = {}
        member_count = 0
        non_member_count = 0
        
        # Process each contact
        for contact in all_contacts:
            contact_tags = self._get_contact_tags(contact)
            
            # Check membership
            if 'member' in contact_tags:
                member_count += 1
            else:
                non_member_count += 1
            
            # Categorize other tags
            for tag in contact_tags:
                # Skip 'member' tag - it's handled above
                if tag == 'member':
                    continue
                    
                # Check if it's a fixed role tag
                if tag in ROLE_TAGS:
                    role_counts[tag] = role_counts.get(tag, 0) + 1
                # Check if it's a hardcoded location tag
                elif tag in LOCATION_TAGS:
                    location_counts[tag] = location_counts.get(tag, 0) + 1
                else:
                    # Dynamic location tag (anything else that's not a role)
                    location_counts[tag] = location_counts.get(tag, 0) + 1
        
        # Count new contacts (created within date range)
        new_contacts_count = self.db.query(Contact).filter(
            Contact.created_at >= date_from,
            Contact.created_at <= date_to
        ).count()
        
        # Count modified contacts (updated within date range, but NOT created within range)
        modified_contacts_count = self.db.query(Contact).filter(
            Contact.updated_at >= date_from,
            Contact.updated_at <= date_to,
            Contact.created_at < date_from  # Exclude contacts created in the same period
        ).count()
        
        # Format response based on whether date filtering was requested
        if has_date_filter:
            # Specific date range requested
            new_contacts_response = {
                'count': new_contacts_count,
                'date_from': date_from.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d')
            }
            modified_contacts_response = {
                'count': modified_contacts_count,
                'date_from': date_from.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d')
            }
        else:
            # No date filtering - return all-time counts
            new_contacts_response = {
                'count': new_contacts_count,
                'date_from': None,
                'date_to': None
            }
            modified_contacts_response = {
                'count': modified_contacts_count,
                'date_from': None,
                'date_to': None
            }
        
        return {
            'total_contacts': total_contacts,
            'new_contacts': new_contacts_response,
            'modified_contacts': modified_contacts_response,
            'locations': dict(sorted(location_counts.items())),
            'roles': dict(sorted(role_counts.items())),
            'membership': {
                'member': member_count,
                'non_member': non_member_count
            }
        }

    def delete_location_tag(self, location_tag: str) -> Dict[str, Any]:
        """
        Delete a dynamic location tag from all contacts.
        
        Args:
            location_tag: The location tag to remove from all contacts
            
        Returns:
            Dict containing success status, contacts updated, and updated statistics
            
        Note: Cannot delete hardcoded location tags (kanana, majaneng, mashemong, soshanguve, kekana)
        """
        # Hardcoded location tags that cannot be deleted
        HARDCODE_LOCATIONS = {'kanana', 'majaneng', 'mashemong', 'soshanguve', 'kekana'}
        
        # Check if trying to delete a hardcoded location
        if location_tag.lower() in HARDCODE_LOCATIONS:
            raise ValueError(
                f"Cannot delete hardcoded location '{location_tag}'. "
                f"Allowed hardcoded locations: {', '.join(sorted(HARDCODE_LOCATIONS))}"
            )
        
        # Find all contacts that have this location tag
        all_contacts = self.db.query(Contact).all()
        contacts_to_update = []
        
        for contact in all_contacts:
            contact_tags = self._get_contact_tags(contact)
            if location_tag in contact_tags:
                contacts_to_update.append(contact)
        
        # Remove the tag from each contact
        updated_count = 0
        for contact in contacts_to_update:
            try:
                current_tags = self._get_contact_tags(contact)
                updated_tags = [tag for tag in current_tags if tag != location_tag]
                self._set_contact_tags(contact, updated_tags)
                self.db.add(contact)
                updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update contact {contact.id}: {str(e)}")
        
        # Commit all changes
        if updated_count > 0:
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise ValueError(f"Failed to commit changes: {str(e)}")
        
        # Return success response with updated statistics
        return {
            'success': True,
            'deleted_location': location_tag,
            'contacts_updated': updated_count,
            'message': f"Successfully removed location '{location_tag}' from {updated_count} contacts"
        }