from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
import re
from app.database import get_db
from app.models import User
from app.schema.contact import Contact, ContactCreate, ContactUpdate, ContactImport
from app.services.contact_service import ContactService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("", response_model=List[Contact])
async def get_contacts(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    return service.get_contacts(skip=skip, limit=limit)

@router.post("", response_model=Contact)
async def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    try:
        return service.create_contact(contact)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    updated_contact = service.update_contact(contact_id, contact)
    if not updated_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated_contact

def parse_csv_contacts(csv_content: str) -> List[dict]:
    """Parse CSV content and extract contact information"""
    contacts = []
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    for row in csv_reader:
        # Extract display name (prioritize Display Name, then First Name + Last Name)
        display_name = row.get('Display Name', '').strip()
        if not display_name:
            first_name = row.get('First Name', '').strip()
            last_name = row.get('Last Name', '').strip()
            display_name = f"{first_name} {last_name}".strip()
        
        # Extract mobile phone number
        mobile_phone = row.get('Mobile Phone', '').strip()
        
        # Skip empty contacts
        if not display_name and not mobile_phone:
            continue
            
        contact_data = {
            'name': display_name,
            'phone': mobile_phone,
            'status': row.get('Status', 'active').strip(),
            'tags': [tag.strip() for tag in row.get('Tags', '').split(',') if tag.strip()],
            'metadata_': row.get('Metadata', '').strip()
        }
        
        contacts.append(contact_data)
    
    return contacts

def parse_vcf_contacts(vcf_content: str) -> List[dict]:
    """Parse VCF content and extract contact information"""
    contacts = []
    current_contact = {}
    
    for line in vcf_content.split('\n'):
        line = line.strip()
        
        if line.startswith('BEGIN:VCARD'):
            current_contact = {}
        elif line.startswith('END:VCARD'):
            if current_contact:
                contacts.append(current_contact)
                current_contact = {}
        elif ':' in line:
            key, value = line.split(':', 1)
            key = key.split(';')[0]  # Remove parameters
            
            if key == 'FN':  # Full Name (Display Name)
                current_contact['name'] = value
            elif key == 'TEL':
                # Determine phone type based on parameters
                if 'CELL' in line or 'MOBILE' in line:
                    current_contact['phone'] = value
            # Add more VCF fields as needed for status, tags, metadata
            # VCF does not have direct equivalents for 'status', 'tags', 'metadata_'
            # These would typically be handled by custom X-properties or by post-processing
            # For now, we'll leave them as default or empty for VCF imports
            current_contact.setdefault('status', 'active')
            current_contact.setdefault('tags', [])
            current_contact.setdefault('metadata_', None)
    
    return contacts

@router.post("/import")
async def import_contacts(
    contact_import: ContactImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    
    imported_count = 0
    skipped_count = 0
    errors = []
    
    for contact_data in contact_import.contacts:
        phone = str(contact_data.phone).strip()
        
        # Clean phone number for checking duplicates
        cleaned_phone = phone
        if not cleaned_phone.startswith('+'):
            cleaned_phone = '+27' + cleaned_phone.lstrip('0')

        # Check if contact already exists with the cleaned phone number
        if service.get_contact_by_phone(cleaned_phone):
            skipped_count += 1
            continue
            
        try:
            # The service will handle its own cleaning and validation
            service.create_contact(contact_data)
            imported_count += 1
            
        except Exception as e:
            errors.append({
                'contact': contact_data.name or 'Unnamed',
                'error': str(e)
            })
            skipped_count += 1
            
    result = {
        'success': True,
        'imported_count': imported_count,
        'skipped_count': skipped_count,
        'total_contacts': len(contact_import.contacts),
        'errors': errors
    }
    
    if errors:
        result['message'] = f"Imported {imported_count} contacts, skipped {skipped_count} due to errors or duplicates."
    else:
        result['message'] = f"Successfully imported {imported_count} contacts. Skipped {skipped_count} duplicates."
        
    return result

@router.delete("/mass-delete")
async def mass_delete_contacts(
    contact_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    deleted_count = 0
    failed_deletions = []

    for contact_id in contact_ids:
        if service.delete_contact(contact_id):
            deleted_count += 1
        else:
            failed_deletions.append(contact_id)
    
    if failed_deletions:
        raise HTTPException(
            status_code=400,
            detail=f"Successfully deleted {deleted_count} contacts. Failed to delete contacts with IDs: {failed_deletions}"
        )
    else:
        return {"message": f"Successfully deleted {deleted_count} contacts."}

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    if service.delete_contact(contact_id):
        return {"message": "Contact deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Contact not found")

@router.get("/export/csv")
async def export_contacts_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export contacts to CSV format"""
    service = ContactService(db)
    contacts = service.get_contacts()
    
    # Create CSV content
    output = io.StringIO()
    fieldnames = ['name', 'phone', 'status', 'tags', 'opt_out_sms', 'opt_out_whatsapp', 'metadata_']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for contact in contacts:
        writer.writerow({
            'name': contact.name or '',
            'phone': contact.phone or '',
            'status': contact.status or 'active',
            'tags': ','.join(contact.tags) if contact.tags else '',
            'opt_out_sms': contact.opt_out_sms,
            'opt_out_whatsapp': contact.opt_out_whatsapp,
            'metadata_': contact.metadata_ or ''
        })
    
    return {
        'success': True,
        'csv_content': output.getvalue(),
        'filename': 'contacts_export.csv'
    }

@router.get("/export/vcf")
async def export_contacts_vcf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export contacts to VCF format"""
    service = ContactService(db)
    contacts = service.get_contacts()
    
    vcf_content = []
    
    for contact in contacts:
        vcf_entry = ['BEGIN:VCARD', 'VERSION:3.0']
        
        if contact.name:
            vcf_entry.append(f'FN:{contact.name}')
        
        if contact.phone:
            vcf_entry.append(f'TEL;TYPE=CELL:{contact.phone}')
        
        vcf_entry.append('END:VCARD')
        vcf_content.extend(vcf_entry)
        vcf_content.append('')  # Empty line between contacts
    
    return {
        'success': True,
        'vcf_content': '\n'.join(vcf_content),
        'filename': 'contacts_export.vcf'
    }
